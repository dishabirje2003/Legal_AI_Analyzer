import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { supabase } from '../lib/supabase.js';
import { syncUserProfile } from '../lib/userProfile.js';

/** @typedef {{ session: import('@supabase/supabase-js').Session | null, user: import('@supabase/supabase-js').User | null, loading: boolean, signIn: (email: string, password: string) => Promise<unknown>, signUp: (name: string, email: string, password: string) => Promise<unknown>, signOut: () => Promise<void> }} AuthState */

/** @type {React.Context<AuthState | null>} */
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!supabase) {
      setSession(null);
      setUser(null);
      setLoading(false);
      return;
    }

    let mounted = true;

    supabase.auth.getSession().then(({ data: { session: s } }) => {
      if (!mounted) return;
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
      if (s?.user) {
        syncUserProfile(supabase, s.user).catch(() => {});
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, s) => {
      // Ignore auth state changes if we are currently forcing a manual sign-out during the signup flow
      if (window.__isSigningUp) return;
      
      setSession(s);
      setUser(s?.user ?? null);
      setLoading(false);
      if (s?.user) {
        syncUserProfile(supabase, s.user).catch(() => {});
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo(
    () => ({
      session,
      user,
      loading,
      async signIn(email, password) {
        if (!supabase) throw new Error('Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        if (data.user) await syncUserProfile(supabase, data.user);
        return data;
      },
      async signUp(name, email, password) {
        if (!supabase) throw new Error('Supabase is not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY.');
        
        try {
          window.__isSigningUp = true;
          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: { data: { name, full_name: name } },
          });
          if (error) throw error;
          if (data.user) await syncUserProfile(supabase, data.user, name);
          
          // Supabase auto-logs the user in if email confirmation is disabled.
          // To enforce a manual login step (real-world app behavior), we immediately sign them out.
          await supabase.auth.signOut();
          
          return data ?? {};
        } finally {
          window.__isSigningUp = false;
        }
      },
      async signOut() {
        if (!supabase) return;
        await supabase.auth.signOut();
      },
    }),
    [session, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
