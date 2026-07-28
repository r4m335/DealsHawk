"""
cuelinks_feed.py — Cuelinks Deals Feed Integration (Source 2)
═══════════════════════════════════════════════════════════════
Periodically fetches live offers from Cuelinks API v2 and saves them
into Supabase so your deal app is automatically populated with top offers!
"""

import os
import logging
import asyncio
import httpx
from dotenv import load_dotenv
from parser import parse_deal_from_text, detect_store
from db import save_deal, deal_exists

load_dotenv()

log = logging.getLogger("dealhawk.cuelinks_feed")

API_KEY = os.getenv("CUELINKS_API_KEY", "").strip()
CUELINKS_FEED_URL = "https://www.cuelinks.com/api/v2/offers.json"


async def fetch_and_sync_cuelinks_deals(limit: int = 50) -> int:
    """
    Fetch live deals from Cuelinks v2 Offers API and sync them into Supabase.
    Returns the number of new deals saved.
    """
    if not API_KEY:
        log.warning("CUELINKS_API_KEY not configured — skipping Cuelinks feed sync")
        return 0

    log.info("📡 Fetching live deals from Cuelinks Deals Feed API...")

    headers = {
        "Authorization": f"Token token={API_KEY}",
        "Accept": "application/json",
    }

    params = {
        "page": 1,
        "per_page": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(CUELINKS_FEED_URL, params=params, headers=headers)

        if resp.status_code != 200:
            log.warning(f"Cuelinks Feed API returned HTTP {resp.status_code}: {resp.text[:100]}")
            return 0

        data = resp.json()
        offers = data.get("offers", [])
        log.info(f"   Received {len(offers)} offers from Cuelinks Feed")

        saved_count = 0

        for offer in offers:
            try:
                title = (offer.get("title") or "").strip()
                affiliate_url = offer.get("affiliate_url") or offer.get("url")
                raw_url = offer.get("url") or affiliate_url
                campaign = (offer.get("campaign") or "").strip()

                if not title or not affiliate_url:
                    continue

                # 1. Detect store (ONLY Amazon, Flipkart, Myntra, Ajio)
                store = detect_store(raw_url)
                if store == "other" and campaign:
                    camp_lower = campaign.lower()
                    if "amazon" in camp_lower:
                        store = "amazon"
                    elif "flipkart" in camp_lower:
                        store = "flipkart"
                    elif "myntra" in camp_lower:
                        store = "myntra"
                    elif "ajio" in camp_lower:
                        store = "ajio"

                if store not in ("amazon", "flipkart", "myntra", "ajio"):
                    continue

                # 2. Check if deal already in DB
                if await deal_exists(affiliate_url):
                    continue

                # 3. Parse price & discount from title / description
                combined_text = f"{title}\n{offer.get('description', '')}"
                deal = parse_deal_from_text(combined_text, affiliate_url, store)

                if deal is None:
                    deal = {
                        "title": title[:220],
                        "image_url": None,
                        "original_price": None,
                        "discounted_price": 999,  # Default fallback if price unlisted
                        "discount_pct": 20,
                        "store": store,
                        "affiliate_url": affiliate_url,
                        "category": "cuelinks",
                        "is_hot": False,
                    }
                else:
                    deal["affiliate_url"] = affiliate_url
                    deal["store"] = store
                    deal["category"] = "cuelinks"

                # Image URL handling from Cuelinks
                img = offer.get("image_url")
                if img and not img.endswith("missing.png") and not deal.get("image_url"):
                    if img.startswith("//"):
                        img = "https:" + img
                    elif img.startswith("/"):
                        img = "https://www.cuelinks.com" + img
                    deal["image_url"] = img

                # Save deal
                ok = await save_deal(deal)
                if ok:
                    saved_count += 1
                    log.info(f"   ✅ Saved Cuelinks Feed Deal: {title[:50]} ({store.upper()})")

            except Exception as item_exc:
                log.debug(f"Failed to process offer {offer.get('id')}: {item_exc}")

        log.info(f"🎉 Cuelinks Feed sync complete! Saved {saved_count} new deal(s).")
        return saved_count

    except Exception as exc:
        log.error(f"Cuelinks Feed sync failed: {exc}")
        return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(fetch_and_sync_cuelinks_deals(30))
