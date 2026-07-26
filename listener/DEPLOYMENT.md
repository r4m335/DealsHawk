# 🚀 Phase 5 Deployment Guide — 24/7 Production Setup

This guide covers deploying the **DealHawk** stack so it runs 24/7 without your laptop:
1. **Frontend Web App** → Deployed on **Vercel** (Free Tier)
2. **Telegram Listener** → Deployed on **Railway** / **Render** / **VPS** (24/7 Worker)

---

## 🌐 PART 1 — Deploy Web App to Vercel

### Step 1: Push Code to GitHub
1. Create a new GitHub repository named `deals-app`.
2. Initialize git and push:
   ```bash
   cd "C:\mini project\Deals App\deals-app"
   git init
   git add .
   git commit -m "Initial commit - DealHawk Web App"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/deals-app.git
   git push -u origin main
   ```

### Step 2: Deploy on Vercel
1. Go to [vercel.com](https://vercel.com) and log in with GitHub.
2. Click **"Add New..."** → **"Project"**.
3. Import your `deals-app` repository.
4. Expand **Environment Variables** and add:
   - `NEXT_PUBLIC_SUPABASE_URL` = `https://your-project-ref.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` = `your-anon-public-key`
5. Click **Deploy**.

🎉 Your web app is now live at `https://deals-app-xxx.vercel.app`!

---

## 🎧 PART 2 — Deploy 24/7 Telegram Listener to Railway

Because cloud servers cannot accept interactive phone logins, we generate a `TELEGRAM_STRING_SESSION` token once on local machine.

### Step 1: Generate StringSession (One-Time Setup)
1. In your local terminal:
   ```bash
   cd "C:\mini project\Deals App\listener"
   python auth.py
   ```
2. Enter your phone number (`+91...`) and the verification code sent to your Telegram app.
3. Copy the long session string printed on screen.

### Step 2: Push Listener to GitHub
1. Create a separate GitHub repository named `dealhawk-listener`.
2. Push the listener code:
   ```bash
   cd "C:\mini project\Deals App\listener"
   git init
   git add .
   git commit -m "Initial commit - DealHawk Listener"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/dealhawk-listener.git
   git push -u origin main
   ```

### Step 3: Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub repo"**.
3. Select `dealhawk-listener`.
4. Go to **Variables** tab in Railway and add the following:
   - `TELEGRAM_API_ID` = `30031800`
   - `TELEGRAM_API_HASH` = `5ff1e9abeef84f9a52fc0e4f55021fe8`
   - `TELEGRAM_STRING_SESSION` = `<paste your generated StringSession here>`
   - `TELEGRAM_CHANNELS` = `@grabdeals16,@nonstopdeals,-1001191090845`
   - `SUPABASE_URL` = `https://iuowoeasksnlywlriozf.supabase.co`
   - `SUPABASE_SERVICE_KEY` = `<your Supabase service_role secret key>`
   - `CUELINKS_API_KEY` = `<optional Cuelinks API key>`
5. Railway will automatically build the Dockerfile and start your listener 24/7!

---

## 📊 Deployment Checklist

- [ ] Vercel deployment live with `NEXT_PUBLIC_SUPABASE_*` env vars
- [ ] `python auth.py` executed locally to produce `TELEGRAM_STRING_SESSION`
- [ ] Listener repository pushed to GitHub
- [ ] Railway project deployed with all 6 environment variables
- [ ] Test: Post a deal link in a channel → verify deal appears live on Vercel site ⚡
