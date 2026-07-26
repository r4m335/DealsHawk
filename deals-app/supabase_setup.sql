-- ══════════════════════════════════════════════════════════
--  DealHawk — Supabase Setup SQL
--  Run this in your Supabase SQL Editor (one time)
--  Dashboard → SQL Editor → New query → paste → Run
-- ══════════════════════════════════════════════════════════

-- 1. Create the deals table
create table if not exists public.deals (
  id               uuid        primary key default gen_random_uuid(),
  title            text        not null,
  image_url        text,
  original_price   integer,
  discounted_price integer     not null,
  discount_pct     integer,
  store            text        check (store in ('amazon','flipkart','myntra','ajio','other')),
  affiliate_url    text        not null,
  category         text        default 'general',
  is_hot           boolean     default false,
  created_at       timestamptz default now(),
  expires_at       timestamptz
);

-- 2. Row-Level Security — allow public read (no auth needed to view deals)
alter table public.deals enable row level security;

create policy "Public read access"
  on public.deals for select
  using (true);

-- 3. Enable Realtime on the deals table
--    (Also turn it on in Dashboard → Database → Replication → deals ✓)
alter publication supabase_realtime add table public.deals;

-- ──────────────────────────────────────────────────────────
--  Optional: seed with 3 sample deals to test the pipeline
-- ──────────────────────────────────────────────────────────
insert into public.deals (title, image_url, original_price, discounted_price, discount_pct, store, affiliate_url, category, is_hot)
values
  (
    'Apple AirPods Pro (2nd Gen) — Active Noise Cancellation',
    'https://images.unsplash.com/photo-1608156639585-b3a032ef9689?w=400&q=80',
    24900, 11999, 52, 'amazon', 'https://amazon.in', 'electronics', true
  ),
  (
    'Nike Air Max 270 Running Shoes — Men''s Size 8–11',
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&q=80',
    12995, 4999, 62, 'myntra', 'https://myntra.com', 'fashion', true
  ),
  (
    'Samsung 55" 4K QLED Smart TV with Tizen OS',
    'https://images.unsplash.com/photo-1593784991095-a205069470b6?w=400&q=80',
    89990, 39999, 56, 'flipkart', 'https://flipkart.com', 'electronics', false
  );
