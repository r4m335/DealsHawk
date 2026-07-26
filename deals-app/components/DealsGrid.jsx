'use client';

import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import DealCard from '../components/DealCard';
import SkeletonCard from '../components/SkeletonCard';
import NewDealToast from '../components/NewDealToast';
import { DEALS, STORES } from '../data/deals';
import { supabase, isSupabaseConfigured } from '../lib/supabase';
import styles from './DealsGrid.module.css';

const SKELETONS = Array.from({ length: 6 }, (_, i) => i);
const DISCOUNT_OPTIONS = [0, 40, 50, 60, 70];

export default function DealsGrid() {
  // ── Filter state ──────────────────────────────────────────
  const [activeStore, setActiveStore]   = useState('all');
  const [search, setSearch]             = useState('');
  const [minDiscount, setMinDiscount]   = useState(0);

  // ── Data state ────────────────────────────────────────────
  const [deals, setDeals]               = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState(null);

  // ── Realtime toast state ──────────────────────────────────
  const [newDeal, setNewDeal]           = useState(null);
  const channelRef                      = useRef(null);

  // ── Fetch deals ───────────────────────────────────────────
  const fetchDeals = useCallback(async () => {
    if (!isSupabaseConfigured) {
      // Demo mode — use fake data
      setDeals(DEALS.map(d => ({ ...d, image_url: d.image })));
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const { data, error: err } = await supabase
        .from('deals')
        .select('*')
        .order('created_at', { ascending: false });

      if (err) throw err;

      // If table is empty, fall back to fake data so the UI never looks blank
      setDeals(data && data.length > 0 ? data : DEALS.map(d => ({ ...d, image_url: d.image })));
    } catch (err) {
      console.error('[DealHawk] Supabase fetch error:', err.message);
      setError(err.message);
      setDeals(DEALS.map(d => ({ ...d, image_url: d.image })));
    } finally {
      setLoading(false);
    }
  }, []);

  // ── Set up Realtime subscription ──────────────────────────
  const setupRealtime = useCallback(() => {
    if (!isSupabaseConfigured || !supabase) return;

    // Clean up any existing channel before creating a new one
    if (channelRef.current) {
      supabase.removeChannel(channelRef.current);
    }

    const channel = supabase
      .channel('deals-changes')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'deals' },
        (payload) => {
          const incoming = payload.new;
          setDeals(prev => [incoming, ...prev]);
          setNewDeal(incoming);
        }
      )
      .on(
        'postgres_changes',
        { event: 'DELETE', schema: 'public', table: 'deals' },
        (payload) => {
          setDeals(prev => prev.filter(d => d.id !== payload.old.id));
        }
      )
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'deals' },
        (payload) => {
          setDeals(prev => prev.map(d => d.id === payload.new.id ? payload.new : d));
        }
      )
      .subscribe();

    channelRef.current = channel;
  }, []);

  // ── Mount ─────────────────────────────────────────────────
  useEffect(() => {
    fetchDeals();
    setupRealtime();

    return () => {
      if (channelRef.current && supabase) {
        supabase.removeChannel(channelRef.current);
      }
    };
  }, [fetchDeals, setupRealtime]);

  // ── Filter logic ──────────────────────────────────────────
  const filtered = useMemo(() => {
    return deals.filter(d => {
      const matchStore    = activeStore === 'all' || d.store === activeStore;
      const matchSearch   = d.title.toLowerCase().includes(search.toLowerCase());
      const matchDiscount = (d.discount_pct ?? 0) >= minDiscount;
      return matchStore && matchSearch && matchDiscount;
    });
  }, [deals, activeStore, search, minDiscount]);

  // ── Render ────────────────────────────────────────────────
  return (
    <section className={styles.section} aria-label="Deals grid">

      {/* Error banner */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          ⚠️ Couldn't reach Supabase ({error}). Showing demo data.
        </div>
      )}

      {/* Controls bar */}
      <div className={styles.controls}>
        {/* Search */}
        <div className={styles.searchWrap}>
          <span className={styles.searchIcon} aria-hidden="true">🔍</span>
          <input
            id="deal-search"
            type="search"
            placeholder="Search deals…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className={styles.searchInput}
            aria-label="Search deals"
          />
        </div>

        {/* Discount filter */}
        <div className={styles.discountFilter} role="group" aria-label="Minimum discount filter">
          {DISCOUNT_OPTIONS.map(d => (
            <button
              key={d}
              id={`discount-filter-${d}`}
              className={`${styles.discountBtn} ${minDiscount === d ? styles.activeDiscount : ''}`}
              onClick={() => setMinDiscount(d)}
              aria-pressed={minDiscount === d}
            >
              {d === 0 ? 'All' : `${d}%+ off`}
            </button>
          ))}
        </div>
      </div>

      {/* Store tabs */}
      <div className={styles.tabs} role="tablist" aria-label="Filter by store">
        {STORES.map(store => (
          <button
            key={store}
            id={`store-tab-${store}`}
            role="tab"
            aria-selected={activeStore === store}
            className={`${styles.tab} ${activeStore === store ? styles.activeTab : ''}`}
            onClick={() => setActiveStore(store)}
          >
            {store === 'all' ? '⚡ All Deals' : store.charAt(0).toUpperCase() + store.slice(1)}
          </button>
        ))}
      </div>

      {/* Results count */}
      {!loading && (
        <p className={styles.resultsCount}>
          {isSupabaseConfigured
            ? `${filtered.length} live deal${filtered.length !== 1 ? 's' : ''}`
            : `${filtered.length} demo deal${filtered.length !== 1 ? 's' : ''}`}
        </p>
      )}

      {/* Grid — skeleton → cards */}
      {loading ? (
        <div className={styles.grid} aria-busy="true" aria-label="Loading deals">
          {SKELETONS.map(i => <SkeletonCard key={i} />)}
        </div>
      ) : filtered.length > 0 ? (
        <div className={styles.grid}>
          {filtered.map(deal => (
            <DealCard key={deal.id} deal={{ ...deal, image: deal.image_url ?? deal.image }} />
          ))}
        </div>
      ) : (
        <div className={styles.empty}>
          <span className={styles.emptyIcon}>🔎</span>
          <p>No deals match your filters. Try adjusting them!</p>
        </div>
      )}

      {/* Realtime new-deal toast */}
      <NewDealToast deal={newDeal} onDismiss={() => setNewDeal(null)} />
    </section>
  );
}
