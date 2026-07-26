"""
enricher.py — Product detail enrichment (Phase 4)
══════════════════════════════════════════════════
Fetches real product title, image URL, and prices directly from product pages.

Strategy (in order of reliability):
  1. Open Graph meta tags  — og:title, og:image  (works on all stores)
  2. JSON-LD structured data — schema.org Product  (Amazon, Flipkart, Myntra)
  3. Store-specific HTML patterns — price selectors, regex
  4. Fallback: whatever the Telegram text parser found

The enricher is best-effort: on failure it returns {} and the listener
falls back gracefully to text-parsed data.
"""

import json
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("dealhawk.enricher")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT":             "1",
}

# ─────────────────────────────────────────────────────────────
#  Store-specific price CSS selectors (BeautifulSoup attrs)
# ─────────────────────────────────────────────────────────────
_PRICE_SELECTORS = {
    "amazon": [
        {"class": re.compile(r"a-price-whole")},
        {"id": "priceblock_ourprice"},
        {"id": "priceblock_dealprice"},
        {"class": re.compile(r"priceToPay")},
    ],
    "flipkart": [
        {"class": re.compile(r"_30jeq3")},
        {"class": re.compile(r"_16Jk6d")},
        {"class": re.compile(r"hl05eU")},
    ],
    "myntra": [
        {"class": re.compile(r"pdp-price")},
        {"class": re.compile(r"pdp-mrp")},
    ],
    "ajio": [
        {"class": re.compile(r"prod-sp")},
        {"class": re.compile(r"prod-cp")},
    ],
}

# ─────────────────────────────────────────────────────────────
#  JSON-LD structured data pattern
# ─────────────────────────────────────────────────────────────
_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.DOTALL | re.IGNORECASE,
)

# ─────────────────────────────────────────────────────────────
#  Numeric price extraction
# ─────────────────────────────────────────────────────────────
_PRICE_TEXT_RE = re.compile(r"[\d,]+\.?\d*")


def _clean_price(raw: str) -> Optional[int]:
    try:
        val = int(float(raw.replace(",", "").strip()))
        return val if 10 < val < 10_000_000 else None
    except (ValueError, TypeError):
        return None


def _prices_from_elements(soup: BeautifulSoup, store: str) -> list:
    """Try store-specific CSS selectors to find price elements."""
    prices = []
    for attrs in _PRICE_SELECTORS.get(store, []):
        for el in soup.find_all(True, attrs):
            text = el.get_text(strip=True).replace("₹", "").replace(",", "").strip()
            p = _clean_price(text)
            if p:
                prices.append(p)
    return prices


def _prices_from_jsonld(html: str) -> list:
    """Extract prices from JSON-LD Product schema blocks."""
    prices = []
    for match in _JSONLD_RE.finditer(html):
        try:
            data = json.loads(match.group(1))
            # Handle @graph arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    schema_type = item.get("@type", "")
                    if "Product" in schema_type or "Offer" in schema_type:
                        offers = item.get("offers", item)
                        if isinstance(offers, dict):
                            p = _clean_price(str(offers.get("price", "")))
                            if p:
                                prices.append(p)
                        elif isinstance(offers, list):
                            for offer in offers:
                                p = _clean_price(str(offer.get("price", "")))
                                if p:
                                    prices.append(p)
        except (json.JSONDecodeError, Exception):
            continue
    return prices


# ─────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────

async def fetch_product_details(url: str, store: str) -> dict:
    """
    Fetch product title, image URL, and prices from a product page.

    Returns a dict with any subset of:
      title, image_url, original_price, discounted_price

    Returns {} on any failure — the caller falls back to text-parsed data.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers=_HEADERS,
        ) as http:
            resp = await http.get(url)

        if resp.status_code != 200:
            log.debug(f"    Enricher HTTP {resp.status_code} for {url[:60]}")
            return {}

        html  = resp.text
        soup  = BeautifulSoup(html, "lxml")
        result: dict = {}

        # ── 1. Open Graph title ───────────────────────────────
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            result["title"] = og_title["content"].strip()[:220]

        # Fallback title: <title> tag
        if "title" not in result:
            tag = soup.find("title")
            if tag and tag.string:
                raw = tag.string.strip()
                # Strip store-name suffix common on Amazon/Flipkart
                for suffix in [" - Amazon.in", " | Flipkart.com", " - Myntra", " | AJIO"]:
                    raw = raw.replace(suffix, "")
                if len(raw) > 5:
                    result["title"] = raw[:220]

        # ── 2. Open Graph image ───────────────────────────────
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            img = og_image["content"]
            # Ensure it's a full URL
            if img.startswith("//"):
                img = "https:" + img
            result["image_url"] = img

        # ── 3. Prices ─────────────────────────────────────────
        # Try JSON-LD first (most structured)
        prices = _prices_from_jsonld(html)

        # Fall back to CSS selectors
        if not prices:
            prices = _prices_from_elements(soup, store)

        # Deduplicate and sort
        prices = sorted(set(p for p in prices if p))

        if len(prices) >= 2:
            result["discounted_price"] = prices[0]   # lowest = deal price
            result["original_price"]   = prices[-1]  # highest = MRP
        elif len(prices) == 1:
            result["discounted_price"] = prices[0]

        if result:
            log.info(
                f"    📦 Enriched: title={'yes' if 'title' in result else 'no'} "
                f"image={'yes' if 'image_url' in result else 'no'} "
                f"price={'yes' if 'discounted_price' in result else 'no'}"
            )

        return result

    except Exception as exc:
        log.debug(f"    Enricher failed for {url[:60]}: {exc}")
        return {}
