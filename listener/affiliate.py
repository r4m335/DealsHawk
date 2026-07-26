"""
affiliate.py — Cuelinks affiliate link converter (Phase 4)
══════════════════════════════════════════════════════════
Converts raw product URLs into your Cuelinks affiliate tracking links.
Every "Grab Deal" click through your affiliate link earns you commission.

Requires CUELINKS_API_KEY in .env.
Falls back gracefully to the original URL if Cuelinks is not configured.

Cuelinks API docs: https://cuelinks.com/publishers/api-docs
"""

import logging
import os
import httpx

log = logging.getLogger("dealhawk.affiliate")

_API_KEY = os.getenv("CUELINKS_API_KEY", "").strip()
_API_URL  = "https://api.cuelinks.com/v1/affiliate-url/"


def is_configured() -> bool:
    return bool(_API_KEY)


async def make_affiliate_url(product_url: str) -> str:
    """
    Convert a product URL to a Cuelinks affiliate URL.

    Returns the affiliate URL on success, or the original URL as fallback
    so deals are always saved even if Cuelinks is down or not yet configured.
    """
    if not _API_KEY:
        log.debug("Cuelinks not configured (CUELINKS_API_KEY missing) — using raw URL")
        return product_url

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                _API_URL,
                params={"apiKey": _API_KEY, "url": product_url},
            )

        if resp.status_code != 200:
            log.warning(f"    Cuelinks API returned HTTP {resp.status_code}")
            return product_url

        data = resp.json()

        # Cuelinks v1 response shape: {"data": {"affiliate_url": "..."}, "status": 200}
        affiliate_url = (
            data.get("data", {}).get("affiliate_url")
            or data.get("url")          # some versions use top-level "url"
            or data.get("affiliateUrl") # camelCase variant
        )

        if affiliate_url:
            log.info(f"    💰 Affiliate URL created (Cuelinks)")
            return affiliate_url
        else:
            log.warning(f"    Cuelinks returned no URL — raw response: {data}")
            return product_url

    except Exception as exc:
        log.error(f"    Cuelinks error: {exc}")
        return product_url
