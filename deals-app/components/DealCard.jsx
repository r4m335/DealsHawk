'use client';

import { useState } from 'react';
import styles from './DealCard.module.css';
import { STORE_META } from '../data/deals';

function formatPrice(n) {
  if (n == null || isNaN(n)) return '₹—';
  return '₹' + Number(n).toLocaleString('en-IN');
}

export default function DealCard({ deal }) {
  const [clicked, setClicked] = useState(false);
  const store = STORE_META[deal.store] || { label: deal.store || 'Other', color: '#aaa', bg: 'rgba(170,170,170,0.1)' };

  // Handle both DB (image_url) and demo data (image) field names
  const imageUrl = deal.image_url || deal.image;
  const discountPct = deal.discount_pct || 0;
  const discountedPrice = deal.discounted_price ?? null;
  const originalPrice = deal.original_price ?? null;
  const saving = (originalPrice != null && discountedPrice != null)
    ? originalPrice - discountedPrice
    : null;

  function handleGrab() {
    setClicked(true);
    setTimeout(() => setClicked(false), 600);
    window.open(deal.affiliate_url, '_blank', 'noopener,noreferrer');
  }

  return (
    <article className={styles.card} aria-label={deal.title}>
      {/* Discount badge */}
      {discountPct > 0 && (
        <div className={styles.badge}>−{discountPct}% OFF</div>
      )}

      {/* Hot deal flame */}
      {deal.is_hot && (
        <div className={styles.hotBadge} title="Hot Deal">🔥</div>
      )}

      {/* Product image */}
      <div className={styles.imageWrap}>
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={deal.title}
            className={styles.image}
            loading="lazy"
            onError={(e) => {
              // Hide broken image link and fall back gracefully
              e.currentTarget.style.display = 'none';
            }}
          />
        ) : null}
        {(!imageUrl) && (
          <div
            className={styles.image}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: `radial-gradient(circle at center, ${store.color}15 0%, rgba(15, 23, 42, 0.95) 100%)`,
              borderBottom: `1px solid ${store.color}33`,
              padding: '1rem',
              textAlign: 'center',
              gap: '0.5rem'
            }}
          >
            <span style={{ fontSize: '2rem', filter: 'drop-shadow(0 2px 8px rgba(0,0,0,0.4))' }}>
              {deal.store === 'amazon' ? '📦' : deal.store === 'flipkart' ? '⚡' : deal.store === 'myntra' ? '🛍️' : deal.store === 'ajio' ? '✨' : '🔥'}
            </span>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: store.color, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              {store.label} Deal
            </span>
          </div>
        )}
      </div>

      {/* Card body */}
      <div className={styles.body}>
        {/* Store pill */}
        <span
          className={styles.storePill}
          style={{ color: store.color, background: store.bg, borderColor: store.color + '44' }}
        >
          {store.label}
        </span>

        <h3 className={styles.title}>{deal.title}</h3>

        {/* Pricing */}
        <div className={styles.pricing}>
          <span className={styles.discountedPrice}>{formatPrice(discountedPrice)}</span>
          {originalPrice != null && (
            <span className={styles.originalPrice}>{formatPrice(originalPrice)}</span>
          )}
          {saving != null && saving > 0 && (
            <span className={styles.saving}>
              Save {formatPrice(saving)}
            </span>
          )}
        </div>

        {/* CTA */}
        <button
          id={`grab-deal-${deal.id}`}
          className={`${styles.grabBtn} ${clicked ? styles.grabbed : ''}`}
          onClick={handleGrab}
          aria-label={`Grab deal for ${deal.title}`}
        >
          {clicked ? '✓ Opening…' : 'Grab Deal 🔥'}
        </button>
      </div>
    </article>
  );
}

