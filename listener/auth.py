#!/usr/bin/env python3
"""
auth.py — Run this ONCE locally to authenticate with Telegram and generate a
StringSession string. Store the output in TELEGRAM_STRING_SESSION in your .env
(and on Railway/VPS) so the listener can run on cloud without interactive login.

Usage:
    python auth.py
"""

import asyncio
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional here

try:
    from telethon import TelegramClient
    from telethon.sessions import StringSession
except ImportError:
    print("❌ telethon not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


async def main():
    api_id   = os.getenv("TELEGRAM_API_ID")
    api_hash = os.getenv("TELEGRAM_API_HASH")

    if not api_id or not api_hash:
        print("❌ TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env")
        sys.exit(1)

    print("=" * 60)
    print("  DealHawk — Telegram StringSession Generator")
    print("=" * 60)
    print()
    print("You'll be asked for your phone number (+91XXXXXXXXXX)")
    print("and the verification code Telegram sends you.")
    print("This is safe — credentials are never stored or sent anywhere.")
    print()

    async with TelegramClient(StringSession(), int(api_id), api_hash) as client:
        session_string = client.session.save()

    print()
    print("✅ Done! Your StringSession string:")
    print()
    print("─" * 60)
    print(session_string)
    print("─" * 60)
    print()
    print("➡  Copy the string above into:")
    print("   1. listener/.env  →  TELEGRAM_STRING_SESSION=<paste here>")
    print("   2. Railway env vars (Phase 5) →  TELEGRAM_STRING_SESSION=<paste here>")
    print()
    print("⚠️  WARNING: This string grants full access to your Telegram account.")
    print("   Keep it secret. Never commit it to Git.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
