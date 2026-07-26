'use client';

import { useState } from 'react';
import styles from './DealCard.module.css';
import { STORE_META } from '../data/deals';

function formatPrice(n) {
  return '₹' + n.toLocaleString('en-IN');
}

export default function DealCard({ deal }) {
  const [clicked, setClicked] = useState(false);
  const store = STORE_META[deal.store] || { label: deal.store, color: '#aaa', bg: 'rgba(170,170,170,0.1)' };

  function handleGrab() {
    setClicked(true);
    setTimeout(() => setClicked(false), 600);
    window.open(deal.affiliate_url, '_blank', 'noopener,noreferrer');
  }

  return (
    <article className={styles.card} aria-label={deal.title}>
      {/* Discount badge */}
      <div className={styles.badge}>−{deal.discount_pct}% OFF</div>

      {/* Hot deal flame */}
      {deal.is_hot && (
        <div className={styles.hotBadge} title="Hot Deal">🔥</div>
      )}

      {/* Product image */}
      <div className={styles.imageWrap}>
        <img
          src={deal.image}
          alt={deal.title}
          className={styles.image}
          loading="lazy"
        />
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
          <span className={styles.discountedPrice}>{formatPrice(deal.discounted_price)}</span>
          <span className={styles.originalPrice}>{formatPrice(deal.original_price)}</span>
          <span className={styles.saving}>
            Save {formatPrice(deal.original_price - deal.discounted_price)}
          </span>
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
