"""
parser.py — URL extraction, store detection, redirect following, and deal text parsing.
"""

import re
import logging
from typing import Optional
import httpx

log = logging.getLogger("dealhawk.parser")

# ─────────────────────────────────────────────────────────────
#  URL extraction
# ─────────────────────────────────────────────────────────────

URL_RE = re.compile(
    r'https?://[^\s<>"\'\)\]\}]+',
    re.IGNORECASE,
)

def extract_urls(text: str) -> list:
    """Return all HTTP/HTTPS URLs found in the message text."""
    return URL_RE.findall(text)


# ─────────────────────────────────────────────────────────────
#  Store detection
# ─────────────────────────────────────────────────────────────

STORE_MAP = {
    "amazon":   [r"amazon\.in", r"amzn\.in", r"amzn\.to", r"amazon\.com/dp"],
    "flipkart": [r"flipkart\.com", r"fkrt\.it", r"dl\.flipkart\.com"],
    "myntra":   [r"myntra\.com"],
    "ajio":     [r"ajio\.com"],
}

def detect_store(url: str) -> str:
    """
    Return the store name for a URL, or 'other' if not recognised.
    Checked in priority order so amazon.in always wins over generic .in TLD.
    """
    for store, patterns in STORE_MAP.items():
        for pattern in patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return store
    return "other"


# ─────────────────────────────────────────────────────────────
#  Follow redirects
# ─────────────────────────────────────────────────────────────

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

async def follow_redirects(url: str, max_redirects: int = 10) -> str:
    """
    Follow all redirects for a shortlink and return the final destination URL.
    Deal channels commonly use amzn.to, fkrt.it, etc.
    Falls back to the original URL on any error.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            max_redirects=max_redirects,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers=_HTTP_HEADERS,
        ) as client:
            # Try HEAD first (faster, no body download)
            try:
                resp = await client.head(url)
                return str(resp.url)
            except httpx.HTTPStatusError:
                pass

            # Some servers reject HEAD — fall back to GET
            resp = await client.get(url)
            return str(resp.url)

    except Exception as exc:
        log.debug(f"Redirect follow failed for {url}: {exc}")
        return url


# ─────────────────────────────────────────────────────────────
#  Text parsing — extract title, prices, discount
# ─────────────────────────────────────────────────────────────

# Matches ₹999, Rs 999, Rs.999, INR 999  (with optional commas)
PRICE_RE = re.compile(
    r'(?:₹|Rs\.?\s*|INR\s*)(\d[\d,]*)',
    re.IGNORECASE,
)

# Matches "70% off", "70% discount", "save 70%", "70% savings"
DISCOUNT_RE = re.compile(
    r'(\d{1,2})%\s*(?:off|discount|saving|savings)',
    re.IGNORECASE,
)

# Also match "at X% discount" and "upto X% off" patterns
DISCOUNT_RE2 = re.compile(
    r'(?:upto?|up\s+to|save)\s*(\d{1,2})%',
    re.IGNORECASE,
)


def _clean_price(raw: str) -> int:
    """Strip commas and convert to integer."""
    return int(raw.replace(",", "").strip())


def _extract_title(text: str) -> Optional[str]:
    """
    Return the best title line from the message.
    Strategy: first non-URL, non-empty line with >10 chars after stripping emojis.
    """
    # Strip leading emoji / symbol clusters
    emoji_prefix = re.compile(r'^[\U0001F000-\U0001FFFF\u2600-\u26FF\u2700-\u27BF\s📢🔔💥🚨🔥⚡🎯✅❗]+')

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("http"):
            continue
        # Remove leading emoji noise
        cleaned = emoji_prefix.sub("", line).strip()
        # Remove hashtags
        cleaned = re.sub(r"#\w+", "", cleaned).strip()
        if len(cleaned) >= 8:
            return cleaned[:220]

    return None


def parse_deal_from_text(
    text: str,
    affiliate_url: str,
    store: str,
) -> Optional[dict]:
    """
    Parse a Telegram message and return a deal dict ready for Supabase INSERT.
    Returns None if not enough info could be extracted.
    """
    # ── Title ──────────────────────────────────────────────
    title = _extract_title(text)
    if not title:
        title = f"Deal from {store.capitalize()}"

    # ── Prices ─────────────────────────────────────────────
    raw_prices = PRICE_RE.findall(text)
    prices = [_clean_price(p) for p in raw_prices]
    # Remove obviously wrong values (e.g. year-like numbers)
    prices = [p for p in prices if 10 < p < 10_000_000]

    original_price   = None
    discounted_price = None

    if len(prices) >= 2:
        # Assume higher = MRP, lower = deal price
        sorted_p = sorted(prices, reverse=True)
        original_price   = sorted_p[0]
        discounted_price = sorted_p[1]
    elif len(prices) == 1:
        discounted_price = prices[0]

    # ── Discount % ─────────────────────────────────────────
    discount_pct = None
    d_matches = DISCOUNT_RE.findall(text) or DISCOUNT_RE2.findall(text)
    if d_matches:
        discount_pct = int(d_matches[0])

    # Compute from prices if not found in text
    if discount_pct is None and original_price and discounted_price and original_price > discounted_price:
        discount_pct = round((original_price - discounted_price) / original_price * 100)

    # ── Hot deal flag ──────────────────────────────────────
    is_hot = (discount_pct or 0) >= 60

    return {
        "title":            title,
        "image_url":        None,           # enriched in Phase 4
        "original_price":   original_price,
        "discounted_price": discounted_price or 0,
        "discount_pct":     discount_pct or 0,
        "store":            store,
        "affiliate_url":    affiliate_url,  # converted to affiliate link in Phase 4
        "category":         "general",
        "is_hot":           is_hot,
    }
