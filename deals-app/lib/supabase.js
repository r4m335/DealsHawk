// lib/supabase.js
// Supabase client — shared across the app
// Requires NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local

import { createClient } from '@supabase/supabase-js';

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey  = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

/** True when both env vars are present (i.e. Supabase is configured). */
export const isSupabaseConfigured = Boolean(supabaseUrl && supabaseKey);

/**
 * The Supabase client, or null when not yet configured.
 * Always guard usage with `if (supabase)` or `isSupabaseConfigured`.
 */
export const supabase = isSupabaseConfigured
  ? createClient(supabaseUrl, supabaseKey, {
      realtime: { params: { eventsPerSecond: 10 } },
    })
  : null;
