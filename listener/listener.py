#!/usr/bin/env python3
"""
listener.py — DealHawk Telegram Listener (Phase 3)
═══════════════════════════════════════════════════
Watches configured Telegram deal channels in real-time.
For every new message:
  1. Extracts URLs
  2. Follows redirects to get the real product URL
  3. Detects the store (Amazon / Flipkart / Myntra / Ajio)
  4. Parses title, price, and discount from the message text
  5. Deduplicates (skips if URL already saved)
  6. Saves to Supabase → appears live on DealHawk instantly

Usage:
    python listener.py

First run: you'll be prompted for phone + verification code (one time only).
Subsequent runs reuse the saved session file (dealhawk_session.session).
For cloud: set TELEGRAM_STRING_SESSION (run auth.py to generate it).
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.types import MessageEntityUrl, MessageEntityTextUrl, PeerChannel

from parser import extract_urls, detect_store, follow_redirects, parse_deal_from_text
from db import save_deal, deal_exists, health_check
from affiliate import make_affiliate_url, is_configured as cuelinks_ready
from enricher import fetch_product_details

# ── Load env ─────────────────────────────────────────────────
load_dotenv()

# ── Logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("dealhawk")

# Quieten noisy third-party loggers
logging.getLogger("telethon").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ── Config ───────────────────────────────────────────────────
def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        log.critical(f"Missing required env var: {key}")
        sys.exit(1)
    return val

API_ID         = int(_require("TELEGRAM_API_ID"))
API_HASH       = _require("TELEGRAM_API_HASH")
PHONE          = os.getenv("TELEGRAM_PHONE")        # optional when using StringSession
STRING_SESSION = os.getenv("TELEGRAM_STRING_SESSION", "").strip()

raw_channels   = _require("TELEGRAM_CHANNELS")
CHANNELS       = [c.strip() for c in raw_channels.split(",") if c.strip()]

if not CHANNELS:
    log.critical("TELEGRAM_CHANNELS is empty — add at least one channel.")
    sys.exit(1)

# ── Telegram client ───────────────────────────────────────────
# StringSession is used for cloud (no session file needed).
# Falls back to a local file session for local development.
session = "dealhawk_session"  # default

if STRING_SESSION:
    try:
        session = StringSession(STRING_SESSION)
        log.info("Using StringSession (cloud mode)")
    except ValueError:
        log.warning(
            "TELEGRAM_STRING_SESSION is set but not a valid session string.\n"
            "  → Falling back to local file session (dealhawk_session.session).\n"
            "  → If you want cloud mode, run: python auth.py"
        )
        session = "dealhawk_session"
else:
    log.info("Using file session (local mode) → dealhawk_session.session")

client = TelegramClient(session, API_ID, API_HASH)



# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────

def _extract_entity_urls(message) -> list:
    """
    Pull URLs from Telegram message entities (hyperlinks embedded in text).
    These are often the real product links even if not visible in plain text.
    """
    urls = []
    if not message.entities:
        return urls

    for entity in message.entities:
        if isinstance(entity, MessageEntityTextUrl):
            urls.append(entity.url)
        elif isinstance(entity, MessageEntityUrl):
            start = entity.offset
            end   = entity.offset + entity.length
            urls.append(message.message[start:end])

    return urls


async def _process_url(url: str, channel_name: str) -> bool:
    """
    Full pipeline for a single URL extracted from a message.
    Returns True if a deal was saved, False otherwise.
    """
    # 1. Follow redirects → get final product URL
    final_url = await follow_redirects(url)

    # 2. Detect store
    store = detect_store(final_url)
    if store == "other":
        log.debug(f"    Unknown store: {final_url[:70]}")
        return False

    log.info(f"    🏪 Store: {store.upper()}  →  {final_url[:70]}")

    # 3. Dedup check
    if await deal_exists(final_url):
        log.info(f"    ⏭  Already saved — skipping")
        return False

    return True, final_url, store


# ─────────────────────────────────────────────────────────────
#  Event handler
# ─────────────────────────────────────────────────────────────

async def handle_new_message(event):
    msg          = event.message
    text         = msg.message or ""
    channel_name = getattr(event.chat, "title", str(event.chat_id))

    if not text.strip():
        return  # ignore media-only messages (no text)

    log.info(f"📨 [{channel_name}] {text[:90].replace(chr(10), ' ')!r}")

    # Collect URLs — check entities first (most reliable), then regex
    entity_urls = _extract_entity_urls(msg)
    text_urls   = extract_urls(text)
    # Deduplicate while preserving order (entity URLs take priority)
    seen = set()
    all_urls = []
    for u in entity_urls + text_urls:
        if u not in seen:
            seen.add(u)
            all_urls.append(u)

    if not all_urls:
        log.debug("   No URLs found — ignoring")
        return

    saved_count = 0

    for raw_url in all_urls:
        log.info(f"  🔗 Processing: {raw_url[:70]}")
        try:
            # 1. Follow redirects
            final_url = await follow_redirects(raw_url)

            # 2. Store detection
            store = detect_store(final_url)
            if store == "other":
                log.debug(f"    ⏭  Unknown store — skipping")
                continue

            log.info(f"    🏪 {store.upper()} → {final_url[:70]}")

            # 3. Dedup — check BEFORE enrichment to avoid wasted HTTP requests
            if await deal_exists(final_url):
                log.info(f"    ⏭  Already in DB — skipping")
                continue

            # 4. Parse deal info from message text (fast, always available)
            deal = parse_deal_from_text(text, final_url, store)
            if deal is None:
                log.warning("    ⚠️  Could not parse deal info — skipping")
                continue

            # 5. Enrich with real product data from the page ─────────────
            log.info(f"    🔍 Fetching product page...")
            enriched = await fetch_product_details(final_url, store)

            # Enriched data wins over text-parsed data when available
            if enriched.get("title"):
                deal["title"] = enriched["title"]
            if enriched.get("image_url"):
                deal["image_url"] = enriched["image_url"]
            if enriched.get("discounted_price"):
                deal["discounted_price"] = enriched["discounted_price"]
            if enriched.get("original_price"):
                deal["original_price"] = enriched["original_price"]
                # Recalculate discount % from enriched prices if both available
                if deal["original_price"] and deal["discounted_price"]:
                    pct = round(
                        (deal["original_price"] - deal["discounted_price"])
                        / deal["original_price"] * 100
                    )
                    deal["discount_pct"] = max(pct, deal.get("discount_pct", 0))
                    deal["is_hot"] = deal["discount_pct"] >= 60

            # 6. Convert to affiliate link (Cuelinks) ────────────────────
            affiliate_url = await make_affiliate_url(final_url)
            deal["affiliate_url"] = affiliate_url
            if affiliate_url != final_url:
                log.info(f"    💰 Affiliate link ready")

            log.info(
                f"    📝 Title:    {deal['title'][:60]}\n"
                f"       Price:    ₹{deal['discounted_price']}  "
                f"(was ₹{deal['original_price']})  "
                f"{deal['discount_pct']}% off\n"
                f"       Image:    {'✓' if deal.get('image_url') else '✗ (no image)'}\n"
                f"       Affiliate:{'✓ Cuelinks' if affiliate_url != final_url else '✗ raw URL (Cuelinks not set)'}"
            )

            # 7. Save to Supabase ─────────────────────────────────────────
            ok = await save_deal(deal)
            if ok:
                saved_count += 1
                log.info(f"    ✅ Saved to Supabase!")
            else:
                log.warning(f"    ❌ Failed to save")

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.error(f"    💥 Error processing {raw_url[:60]}: {exc}", exc_info=True)

    if saved_count > 0:
        log.info(f"  🎉 {saved_count} deal(s) saved from this message\n")
    else:
        log.debug("  No new deals saved from this message")


# ─────────────────────────────────────────────────────────────
#  Startup
# ─────────────────────────────────────────────────────────────

async def _resolve_channel(ch: str):
    """
    Resolve a channel string to a Telethon entity.
    Supports:
      - @username           (public channels)
      - numeric IDs         (-1001234567890)
      - invite hash/link    (+AbCdEfGhIjKl or t.me/+AbCdEfGhIjKl)
    Auto-joins private channels via invite link if not already a member.
    Returns the entity on success, None on failure.
    """
    clean = ch.strip()

    # ── Strip t.me/ prefix ───────────────────────────────────
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if clean.startswith(prefix):
            clean = "@" + clean[len(prefix):]  # e.g. @+HASH or @username
            break

    # ── Private invite hash: @+HASH or +HASH ─────────────────
    invite_hash = None
    if clean.startswith("@+"):
        invite_hash = clean[2:]
    elif clean.startswith("+"):
        invite_hash = clean[1:]

    if invite_hash:
        try:
            result = await client(ImportChatInviteRequest(invite_hash))
            entity = result.chats[0] if result.chats else None
            if entity:
                log.info(f"   ✓ Joined and resolved private channel +{invite_hash}")
                return entity
        except Exception as e:
            err = str(e)
            if "INVITE_REQUEST_SENT" in err:
                log.warning(f"   ⏳ Join request sent for +{invite_hash} — waiting for admin approval")
                return None
            elif "USER_ALREADY_PARTICIPANT" in err:
                # Already a member — search our dialog list for a match
                log.info(f"   Already in +{invite_hash}, searching dialogs...")
                async for dialog in client.iter_dialogs():
                    entity = dialog.entity
                    # Match by checking if the invite link is associated
                    if hasattr(entity, 'username') or hasattr(entity, 'id'):
                        title = getattr(entity, 'title', '')
                        log.debug(f"     checking: {title} ({entity.id})")
                        return entity  # Return the first channel dialog that matches
            else:
                log.warning(f"   ✗ Could not join private channel +{invite_hash}: {e}")
                return None

    # ── Numeric ID: -1001234567890 ────────────────────────────
    try:
        as_int = int(clean)
        # Telethon needs the raw channel ID (strip the -100 supergroup prefix)
        raw_id = abs(as_int)
        if str(raw_id).startswith("100"):
            raw_id = int(str(raw_id)[3:])
        try:
            return await client.get_entity(PeerChannel(raw_id))
        except Exception:
            # Not in cache yet — search dialogs
            log.debug(f"   ID {clean} not in cache, scanning dialogs...")
            async for dialog in client.iter_dialogs():
                if dialog.entity.id == raw_id or dialog.entity.id == abs(as_int):
                    return dialog.entity
            log.warning(
                f"   ✗ Could not find channel ID {clean} in your dialogs.\n"
                f"     Make sure your account has JOINED this channel, then restart."
            )
            return None
    except ValueError:
        pass  # not a numeric ID, fall through to username lookup

    # ── Public @username ──────────────────────────────────────
    try:
        return await client.get_entity(clean)
    except Exception as exc:
        log.warning(f"   ✗ Could not resolve '{clean}': {exc}")
        return None


async def main():
    print()
    print("  ⚡ DealHawk — Telegram Listener & Enricher  (Phase 4)")
    print("  ─────────────────────────────────────────────────────")
    print(f"  Channels : {', '.join(CHANNELS)}")
    print(f"  Mode     : {'Cloud (StringSession)' if STRING_SESSION else 'Local (file session)'}")
    print(f"  Cuelinks : {'Configured ✅' if cuelinks_ready() else 'Not configured (using raw URLs)'}")
    print()

    # Supabase connectivity test
    log.info("Testing Supabase connection...")
    ok = await health_check()
    if not ok:
        log.critical("Cannot reach Supabase — check SUPABASE_URL and SUPABASE_SERVICE_KEY in .env")
        sys.exit(1)
    log.info("✅ Supabase connected")

    # Start Telegram client
    if STRING_SESSION:
        # StringSession is already authenticated — just connect, don't call start()
        # (start() demands a phone/bot_token even when the session is valid)
        await client.connect()
        if not await client.is_user_authorized():
            log.critical(
                "StringSession is invalid or expired. "
                "Re-run `python auth.py` to generate a fresh session."
            )
            sys.exit(1)
        log.info("✅ Telegram connected (StringSession)")
    else:
        # Local mode — start() handles interactive phone/code auth
        await client.start(phone=PHONE)
        log.info("✅ Telegram connected (local session)")

    me = await client.get_me()
    log.info(f"✅ Logged in as: {me.first_name} (@{me.username or me.id})")

    # ── Populate entity cache (required for numeric ID resolution) ─
    log.info("Loading dialogs (populating cache)...")
    await client.get_dialogs()
    log.info("   Cache ready")

    # ── Resolve every channel and collect valid entity IDs ────────
    log.info("Resolving channels...")
    valid_entity_ids = []
    for ch in CHANNELS:
        entity = await _resolve_channel(ch)
        if entity is not None:
            title = getattr(entity, "title", ch)
            log.info(f"   ✓ {title} (id: {entity.id})")
            valid_entity_ids.append(entity.id)

    if not valid_entity_ids:
        log.critical(
            "No valid channels could be resolved. "
            "Check your TELEGRAM_CHANNELS in .env and make sure your account has joined them."
        )
        sys.exit(1)

    log.info(f"   → Listening to {len(valid_entity_ids)} channel(s)")

    # ── Register handler only with validated channel IDs ──────────
    # Using IDs avoids Telethon re-resolving strings on every event.
    client.add_event_handler(
        handle_new_message,
        events.NewMessage(chats=valid_entity_ids),
    )

    print()
    log.info("👂 Listening for new deals... Press Ctrl+C to stop.")
    print()

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Listener stopped.")
