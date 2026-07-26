import styles from './SetupBanner.module.css';

/**
 * Shown at the top of the page when Supabase env vars aren't configured.
 * The app falls back to fake data in this case so the UI still looks great.
 */
export default function SetupBanner() {
  return (
    <aside className={styles.banner} role="note" aria-label="Setup required">
      <div className={styles.inner}>
        <span className={styles.icon}>🔧</span>
        <div className={styles.text}>
          <strong>Demo Mode</strong> — Showing fake data. To go live:
          <ol className={styles.steps}>
            <li>Create a project on <a href="https://supabase.com" target="_blank" rel="noopener noreferrer" className={styles.link}>supabase.com</a></li>
            <li>Run <code className={styles.code}>supabase_setup.sql</code> in your SQL Editor</li>
            <li>Copy <code className={styles.code}>.env.local.example</code> → <code className={styles.code}>.env.local</code> and fill in your keys</li>
            <li>Restart the dev server</li>
          </ol>
        </div>
        <span className={styles.badge}>Phase 2</span>
      </div>
    </aside>
  );
}
