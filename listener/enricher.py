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


def _is_generic_title(title: str) -> bool:
    if not title:
        return True
    t = title.strip().lower()
    if len(t) < 5:
        return True
    generics = [
        "amazon.in", "amazon", "flipkart.com", "flipkart", "myntra", "ajio",
        "online shopping site", "buy products online", "shopping india",
        "404", "not found", "robot check", "access denied", "page not found"
    ]
    for g in generics:
        if t == g or t.startswith(g + " :") or t.startswith(g + ":") or t.startswith(g + " -") or t.startswith(g + " —"):
            return True
    return False


def _is_valid_image_url(url: str) -> bool:
    if not url or len(url) < 10:
        return False
    u = url.lower()
    junk = ["1x1", "grey-pixel", "transparent-pixel", "sprite", "favicon", "loader.gif", "blank.gif", "placeholder"]
    return not any(j in u for j in junk)


_AMAZON_ASIN_RE = re.compile(r'/(?:dp|gp/product|product)/([A-Z0-9]{10})', re.IGNORECASE)


def _get_amazon_asin_image(url: str) -> Optional[str]:
    """Extract Amazon ASIN from URL and return direct high-res Amazon CDN image URL."""
    match = _AMAZON_ASIN_RE.search(url)
    if match:
        asin = match.group(1).upper()
        return f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01._SCLZZZZZZZ_.jpg"
    return None


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
    result: dict = {}

    # ── Instant Amazon ASIN CDN image check ─────────────────
    if store == "amazon":
        asin_img = _get_amazon_asin_image(url)
        if asin_img:
            result["image_url"] = asin_img
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers=_HEADERS,
        ) as http:
            resp = await http.get(url)

        if resp.status_code != 200:
            log.debug(f"    Enricher HTTP {resp.status_code} for {url[:60]}")
            return result

        html  = resp.text
        soup  = BeautifulSoup(html, "lxml")

        # ── 1. Open Graph / Page title ──────────────────────────
        candidate_title = None
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            candidate_title = og_title["content"].strip()[:220]
        else:
            tag = soup.find("title")
            if tag and tag.string:
                raw = tag.string.strip()
                for suffix in [" - Amazon.in", " | Flipkart.com", " - Myntra", " | AJIO"]:
                    raw = raw.replace(suffix, "")
                candidate_title = raw[:220]

        if candidate_title and not _is_generic_title(candidate_title):
            result["title"] = candidate_title

        # ── 2. Product Image ──────────────────────────────────
        candidate_img = None
        # Try meta tags first
        for meta_prop in ["og:image", "twitter:image", "og:image:secure_url"]:
            el = soup.find("meta", property=meta_prop) or soup.find("meta", attrs={"name": meta_prop})
            if el and el.get("content") and _is_valid_image_url(el["content"]):
                candidate_img = el["content"].strip()
                break

        # Fallback 1: Amazon product image selectors
        if not candidate_img and store == "amazon":
            for img_el in soup.select("#landingImage, #imgBlkFront, #imgTagWrapperId img, img.s-image"):
                src = img_el.get("src") or img_el.get("data-old-hires")
                if src and _is_valid_image_url(src):
                    candidate_img = src.strip()
                    break

        # Fallback 2: Flipkart product image selectors
        if not candidate_img and store == "flipkart":
            for img_el in soup.select("img._396cs4, img._2r_T1I, img._53v2, img[src*='flixcart.com']"):
                src = img_el.get("src")
                if src and _is_valid_image_url(src):
                    candidate_img = src.strip()
                    break

        if candidate_img and "image_url" not in result:
            if candidate_img.startswith("//"):
                candidate_img = "https:" + candidate_img
            result["image_url"] = candidate_img

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
        return result
