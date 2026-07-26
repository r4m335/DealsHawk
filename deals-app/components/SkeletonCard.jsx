import styles from './SkeletonCard.module.css';

/** Animated placeholder card shown while deals are loading from Supabase */
export default function SkeletonCard() {
  return (
    <div className={styles.card} aria-hidden="true">
      <div className={styles.image} />
      <div className={styles.body}>
        <div className={styles.pill} />
        <div className={styles.titleLine} />
        <div className={styles.titleLineShort} />
        <div className={styles.pricingRow}>
          <div className={styles.price} />
          <div className={styles.oldPrice} />
        </div>
        <div className={styles.btn} />
      </div>
    </div>
  );
}
