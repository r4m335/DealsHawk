# 🦅 DealHawk — Real-Time Deals Platform

> **Auto-catches deals from Telegram channels ➔ Enriches product info ➔ Converts to affiliate links ➔ Streams live in real-time.**

---

## ⚡ Overview

**DealHawk** is a full-stack, real-time deals aggregation engine designed for Indian shoppers and deal finders. It monitors popular Telegram deal channels 24/7, extracts deal links, enriches them with real product images and pricing via web scraping, converts URLs into commission-earning affiliate links (via Cuelinks), and streams them instantly to a dark-mode Next.js frontend using Supabase Realtime WebSockets.

---

## 🏗️ System Architecture

```
                               ┌───────────────────────────┐
                               │  Telegram Deal Channels   │
                               │  (@grabdeals16, etc.)     │
                               └─────────────┬─────────────┘
                                             │  New Message Event
                                             ▼
                               ┌───────────────────────────┐
                               │  Python Listener Engine   │
                               │  (Telethon + httpx)       │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
         ┌───────────────────────────┐               ┌───────────────────────────┐
         │  Web Scraper & Enricher   │               │  Cuelinks Affiliate Engine│
         │  (OG Tags + JSON-LD)      │               │  (affiliate.py)           │
         └─────────────┬─────────────┘               └─────────────┬─────────────┘
                       └─────────────────────┬─────────────────────┘
                                             │  Inserts Enriched Deal
                                             ▼
                               ┌───────────────────────────┐
                               │  Supabase PostgreSQL      │
                               │  (Realtime Engine Enabled)│
                               └─────────────┬─────────────┘
                                             │  WebSocket Instant Push
                                             ▼
                               ┌───────────────────────────┐
                               │  Next.js Frontend (React) │
                               │  (Live Grid & Toast UI)   │
                               └───────────────────────────┘
```

---

## 📦 Project Structure

```
Deals App/
├── deals-app/               # Frontend (Next.js 16 + React)
│   ├── app/                 # App Router pages & CSS modules
│   ├── components/          # DealCard, DealsGrid, SkeletonCard, Toast
│   ├── lib/                 # Supabase client singleton
│   ├── vercel.json          # Production deployment config for Vercel
│   └── package.json
│
├── listener/                # Backend Engine (Python 3.10+)
│   ├── listener.py          # Telethon listener loop
│   ├── enricher.py          # OpenGraph & JSON-LD product page scraper
│   ├── affiliate.py         # Cuelinks affiliate API integration
│   ├── parser.py            # Regex URL & price parser
│   ├── db.py                # Supabase service role client
│   ├── auth.py              # StringSession generator for cloud worker
│   ├── Dockerfile           # Docker container for 24/7 worker
│   ├── Procfile             # Process manager config (Railway/Heroku)
│   ├── railway.json         # Railway deployment manifest
│   └── requirements.txt     # Python dependencies
│
├── .gitignore
└── README.md
```

---

## ✨ Features

- **⚡ Real-Time Streaming**: New deals appear instantly on screen without page refresh via Supabase Realtime WebSockets.
- **🎨 Glassmorphism UI**: Modern dark theme with neon green & orange accents, hover lift animations, and shimmer loading placeholders.
- **🔍 Multi-Filter Engine**: Filter by store (Amazon, Flipkart, Myntra, Ajio), search by keyword, or filter by discount percentage (40%+, 50%+, 60%+, 70%+).
- **📦 Smart Web Scraping**: Extracts high-res product images, full product titles, and accurate prices using OpenGraph meta tags, JSON-LD structured data, and store CSS selectors.
- **💰 Automatic Monetization**: Converts raw deal links into Cuelinks affiliate links on the fly so clicks earn commission.
- **🛡️ Robust Deduplication**: Prevents duplicate deals from being posted even if shared across multiple Telegram channels.
- **🔔 Live Toast Notifications**: Slide-in notification whenever a new deal drops.

---

## 🚀 Quick Start (Local Setup)

### 1. Prerequisites
- Node.js 18+ and npm
- Python 3.10+
- Free [Supabase](https://supabase.com) account

### 2. Frontend Setup (`deals-app`)
```bash
cd deals-app
npm install
copy .env.example .env.local
```
Fill in your Supabase project URL and Anon key in `.env.local`, then start dev server:
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to view the web app.

### 3. Database Setup (Supabase)
Run the SQL queries in `deals-app/supabase_setup.sql` in your Supabase SQL Editor:
- Creates the `deals` table.
- Enables Row Level Security (RLS) with public read policies.
- Enables Realtime replication on the `deals` table.

### 4. Listener Engine Setup (`listener`)
```bash
cd listener
pip install -r requirements.txt
copy .env.example .env
```
Fill in your Telegram API credentials from [my.telegram.org](https://my.telegram.org) and Supabase Service Role Key in `.env`:
```bash
python listener.py
```

---

## 🌐 Production Deployment

- **Frontend**: Deploy `deals-app/` to **Vercel** with `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
- **Backend Listener**: Run `python auth.py` to generate a `TELEGRAM_STRING_SESSION`, then deploy `listener/` to **Railway** or any Docker VPS using the provided `Dockerfile` and `railway.json`.

Detailed step-by-step deployment guide available at [`listener/DEPLOYMENT.md`](file:///C:/mini%20project/Deals%20App/listener/DEPLOYMENT.md).

---

## 📝 License

MIT License. Built for educational and commercial deal aggregation purposes.
