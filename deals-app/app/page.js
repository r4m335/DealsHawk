import Header from '../components/Header';
import DealsGrid from '../components/DealsGrid';
import SetupBanner from '../components/SetupBanner';
import { isSupabaseConfigured } from '../lib/supabase';
import styles from './page.module.css';

export default function HomePage() {
  return (
    <div className={styles.page}>
      <Header />
      {!isSupabaseConfigured && <SetupBanner />}

      {/* Hero banner */}
      <section className={styles.hero} aria-label="Hero banner">
        <div className={styles.heroInner}>
          <div className={styles.heroBadge}>
            <span>⚡</span> Real-time deals engine
          </div>
          <h1 className={styles.heroTitle}>
            Never miss a <span className={styles.heroGradient}>deal again.</span>
          </h1>
          <p className={styles.heroSub}>
            We scan top Telegram deal channels 24/7 and surface the best offers — updated live.
          </p>
          <div className={styles.heroStats}>
            <div className={styles.stat}>
              <span className={styles.statNumber}>1,200+</span>
              <span className={styles.statLabel}>Deals today</span>
            </div>
            <div className={styles.statDivider}></div>
            <div className={styles.stat}>
              <span className={styles.statNumber}>₹4.8Cr</span>
              <span className={styles.statLabel}>Saved this month</span>
            </div>
            <div className={styles.statDivider}></div>
            <div className={styles.stat}>
              <span className={styles.statNumber}>4</span>
              <span className={styles.statLabel}>Stores covered</span>
            </div>
          </div>
        </div>
      </section>

      {/* Main content */}
      <main className={styles.main} id="deals">
        <DealsGrid />
      </main>

      {/* Footer */}
      <footer className={styles.footer}>
        <p>© 2025 DealHawk · Built with ⚡ for Indian shoppers · Affiliate links help us keep the lights on.</p>
      </footer>
    </div>
  );
}
