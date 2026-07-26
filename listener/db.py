"""
db.py — Supabase helpers: save deals and deduplication checks.
Uses the SERVICE ROLE key so inserts bypass Row-Level Security.
"""

import asyncio
import logging
import os
from functools import partial
from typing import Optional

from supabase import create_client, Client

log = logging.getLogger("dealhawk.db")

# ── Lazy singleton ───────────────────────────────────────────
_client: Optional[Client] = None

def _get_client() -> Client:
    """Return (and lazily create) the Supabase service-role client."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
        log.info("Supabase client initialised")
    return _client


def _run_in_thread(fn):
    """Run a synchronous callable in a thread pool so we don't block the event loop."""
    return asyncio.to_thread(fn)


# ── Public helpers ───────────────────────────────────────────

async def deal_exists(affiliate_url: str) -> bool:
    """
    Return True if a deal with this affiliate_url is already in the DB.
    Prevents duplicate deals when the same link is reposted across channels.
    """
    def _check():
        result = (
            _get_client()
            .table("deals")
            .select("id")
            .eq("affiliate_url", affiliate_url)
            .limit(1)
            .execute()
        )
        return len(result.data) > 0

    try:
        return await _run_in_thread(_check)
    except Exception as exc:
        log.error(f"Dedup check failed: {exc}")
        return False  # Assume not exists on error (rather than silently drop)


async def save_deal(deal: dict) -> bool:
    """
    Insert a deal dict into the Supabase `deals` table.
    Returns True on success, False on failure.
    """
    def _insert():
        _get_client().table("deals").insert(deal).execute()

    try:
        await _run_in_thread(_insert)
        return True
    except Exception as exc:
        log.error(f"DB insert failed: {exc}")
        log.debug(f"  Deal that failed: {deal}")
        return False


async def health_check() -> bool:
    """Quick connectivity test — called on startup."""
    def _ping():
        _get_client().table("deals").select("id").limit(1).execute()

    try:
        await _run_in_thread(_ping)
        return True
    except Exception as exc:
        log.error(f"Supabase health check failed: {exc}")
        return False
