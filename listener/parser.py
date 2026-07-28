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

# Matches ₹999, Rs 999, Rs.999, INR 999, @149, at 149, price: 149, starts @149
PRICE_RE = re.compile(
    r'(?:₹|Rs\.?\s*|INR\s*|@\s*|(?:price|at|just|only|flat|starts?|start)\s*@?\s*:?\s*)(\d[\d,]*)',
    re.IGNORECASE,
)

# Matches 149/- or 149 rs
PRICE_RE2 = re.compile(
    r'(\d[\d,]*)\s*(?:/-|\s*rs|\s*rupees)',
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
    Strategy: first non-URL, non-empty line with >=6 chars after stripping emojis and links.
    """
    # Strip leading emoji / symbol clusters
    emoji_prefix = re.compile(r'^[\U0001F000-\U0001FFFF\u2600-\u26FF\u2700-\u27BF\s📢🔔💥🚨🔥⚡🎯✅❗]+')

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("http"):
            continue
        # Remove URLs embedded in the line (e.g. "Master Link : https://...")
        cleaned = re.sub(r'https?://\S+', '', line).strip()
        # Remove leading emoji noise
        cleaned = emoji_prefix.sub("", cleaned).strip()
        # Remove trailing "Master Link :" or similar label remnants
        cleaned = re.sub(r'(?:master\s*link|buy\s*here|link|deal\s*link)\s*:?\s*$', '', cleaned, flags=re.IGNORECASE).strip()
        # Remove hashtags
        cleaned = re.sub(r"#\w+", "", cleaned).strip()
        if len(cleaned) >= 6:
            return cleaned[:220]

    return None


def is_generic_title(title: Optional[str]) -> bool:
    if not title:
        return True
    t = title.strip().lower()
    if len(t) < 5:
        return True
    generics = [
        "amazon.in", "amazon", "flipkart.com", "flipkart", "myntra", "ajio",
        "online shopping site", "buy products online", "shopping india",
        "404", "not found", "robot check", "access denied", "page not found",
        "deal from amazon", "deal from flipkart", "deal from myntra", "deal from ajio", "deal from other"
    ]
    for g in generics:
        if t == g or t.startswith(g + " :") or t.startswith(g + ":") or t.startswith(g + " -") or t.startswith(g + " —"):
            return True
    return False


def parse_deal_from_text(
    text: str,
    affiliate_url: str,
    store: str,
) -> Optional[dict]:
    """
    Parse a Telegram message and return a deal dict ready for Supabase INSERT.
    Returns None if not enough info could be extracted.
    """
    # Strip hidden unicode formatting marks (e.g. \u200e LTR, \u200f RTL, \u200b ZWSP, \xa0 NBSP)
    text = re.sub(r'[\u200e\u200f\u200b\u200c\u200d\uFEFF\xa0]', '', text)

    # ── Title ──────────────────────────────────────────────
    title = _extract_title(text)
    if not title or is_generic_title(title):
        title = None

    # ── Prices ─────────────────────────────────────────────
    raw_prices = PRICE_RE.findall(text) or PRICE_RE2.findall(text)
    prices = [_clean_price(p) for p in raw_prices]
    # Remove obviously wrong values (e.g. year-like numbers like 2024, 2025, 2026)
    prices = [p for p in prices if 10 < p < 10_000_000 and p not in (2024, 2025, 2026)]

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
