'use client';

import { useEffect, useState } from 'react';
import styles from './NewDealToast.module.css';

/**
 * Pops up at the bottom-right when a new deal arrives via Supabase Realtime.
 * @param {{ deal: object|null, onDismiss: () => void }} props
 */
export default function NewDealToast({ deal, onDismiss }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!deal) return;
    setVisible(true);
    const t = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 400); // allow fade-out before clearing
    }, 5000);
    return () => clearTimeout(t);
  }, [deal, onDismiss]);

  if (!deal) return null;

  return (
    <div
      className={`${styles.toast} ${visible ? styles.visible : styles.hidden}`}
      role="alert"
      aria-live="assertive"
    >
      <span className={styles.fireIcon}>🔥</span>
      <div className={styles.content}>
        <p className={styles.label}>New deal just dropped!</p>
        <p className={styles.title}>{deal.title}</p>
      </div>
      <button
        className={styles.close}
        onClick={() => { setVisible(false); setTimeout(onDismiss, 400); }}
        aria-label="Dismiss notification"
      >
        ✕
      </button>
    </div>
  );
}
