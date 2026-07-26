# 🦅 DealHawk — Telegram Listener (Phase 3)

A Python service that monitors Telegram deal channels in real-time and
automatically saves deals to Supabase, making them appear live on your site.

---

## 📁 File Structure

```
listener/
├── listener.py      ← Main script (run this)
├── parser.py        ← URL extraction, store detection, text parsing
├── db.py            ← Supabase helpers (save + dedup)
├── auth.py          ← One-time StringSession generator (for cloud)
├── requirements.txt ← Python dependencies
├── .env.example     ← Env var template
└── .gitignore       ← Protects secrets
```

---

## 🚀 Quick Start (Local)

### Step 1 — Prerequisites
- Python 3.10+ installed
- Supabase project set up (Phase 2 complete)
- Joined the Telegram deal channels you want to monitor

### Step 2 — Install dependencies
```bash
cd listener
pip install -r requirements.txt
```

### Step 3 — Get Telegram API credentials
1. Go to **https://my.telegram.org/auth** and log in
2. Click **"API development tools"**
3. Create a new app (any name/platform is fine)
4. Copy your `api_id` and `api_hash`

### Step 4 — Configure .env
```bash
copy .env.example .env
```
Edit `.env` and fill in:
- `TELEGRAM_API_ID` — from my.telegram.org
- `TELEGRAM_API_HASH` — from my.telegram.org
- `TELEGRAM_PHONE` — your number (e.g. `+917XXXXXXXXX`)
- `TELEGRAM_CHANNELS` — comma-separated channel usernames (e.g. `@DealsDhamaka,@LootDeals`)
- `SUPABASE_URL` — your Supabase project URL
- `SUPABASE_SERVICE_KEY` — **service_role key** (Dashboard → Settings → API → service_role)

> ⚠️ Use the **service_role** key, NOT the anon key. The service role bypasses Row-Level Security so the listener can insert deals.

### Step 5 — Run the listener
```bash
python listener.py
```

**First run:** Telegram will send a code to your phone/app.
Enter it when prompted. This is a **one-time** step — the session is saved locally.

**You should see output like:**
```
✅ Supabase connected
✅ Telegram connected
✅ Logged in as: YourName (@yourhandle)
   ✓ Deals Dhamaka (@DealsDhamaka)
   ✓ Loot Deals (@LootDeals)

👂 Listening for new deals... Press Ctrl+C to stop.

📨 [Deals Dhamaka] 'Apple AirPods Pro ₹11,999 (MRP ₹24,900) 52% OFF\nhttps://amzn.to/...'
  🔗 Processing: https://amzn.to/xxxxx
    🏪 AMAZON → https://www.amazon.in/dp/B0BDHWDR12/...
    📝 Title: Apple AirPods Pro
       Price: ₹11999  (was ₹24900)  52% off
    ✅ Saved to Supabase!
  🎉 1 deal(s) saved from this message
```

Now open your site at **http://localhost:3000** — the deal appears **instantly!** 🎉

---

## ☁️ For Cloud Deployment (Phase 5 — Railway)

You can't use an interactive login on a server. Instead, generate a **StringSession**:

### Step 1 — Generate StringSession (run locally, one time)
```bash
python auth.py
```
Follow the prompts. You'll get a long string like `1BVtsOG8B...`

### Step 2 — Save it
Paste it into `.env` → `TELEGRAM_STRING_SESSION=1BVtsOG8B...`  
Also set it as an env var in Railway's dashboard.

### Step 3 — Deploy to Railway
See Phase 5 for full deployment instructions.

---

## 🔍 How It Works

```
New message in channel
    │
    ▼
Extract URLs (from entities + regex)
    │
    ▼
Follow redirects → get real product URL (amzn.to → amazon.in/dp/...)
    │
    ▼
Detect store (amazon / flipkart / myntra / ajio)
    │
    ▼
Dedup check (skip if URL already in Supabase)
    │
    ▼
Parse text → extract title, prices (₹999), discount (52% off)
    │
    ▼
INSERT into Supabase deals table
    │
    ▼
Supabase Realtime fires → site updates live ⚡
```

---

## 🧪 Testing Without Real Channels

You can create a **private Telegram group**, add your account as admin,
and paste a deal message like:

```
🔥 Apple AirPods Pro (2nd Gen) — Active Noise Cancellation
MRP: ₹24,900 | Deal Price: ₹11,999 | 52% OFF
https://amzn.to/3ZxxxYY
```

Then set `TELEGRAM_CHANNELS=` to that group's username or ID.

---

## 📋 Checklist

- [ ] Python 3.10+ installed
- [ ] `pip install -r requirements.txt` done
- [ ] `.env` created from `.env.example`
- [ ] Telegram API credentials added
- [ ] Target channels joined and added to `.env`
- [ ] Supabase URL and SERVICE KEY added
- [ ] `python listener.py` runs without errors
- [ ] Test message posted → deal appears on site live 🎉
