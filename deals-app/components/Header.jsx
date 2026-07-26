import styles from './Header.module.css';

export default function Header() {
  return (
    <header className={styles.header} role="banner">
      <div className={styles.inner}>
        {/* Logo */}
        <div className={styles.logo} aria-label="DealHawk home">
          <span className={styles.logoIcon} aria-hidden="true">⚡</span>
          <span className={styles.logoText}>
            Deal<span className={styles.logoAccent}>Hawk</span>
          </span>
        </div>

        {/* Live indicator */}
        <div className={styles.liveIndicator} aria-live="polite" aria-label="Real-time deals active">
          <span className={styles.liveDot} aria-hidden="true"></span>
          <span className={styles.liveText}>LIVE</span>
        </div>

        {/* Right side tagline */}
        <p className={styles.tagline}>Real-time deals from top Indian stores</p>
      </div>
    </header>
  );
}
