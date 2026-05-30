/**
 * Keeps `public.users` in sync with auth after sign-in / sign-up.
 * Expects columns: id (uuid, PK), email (text), name (text, optional).
 * If your table uses `full_name` instead of `name`, add that column or rename in Supabase.
 *
 * @param {import('@supabase/supabase-js').SupabaseClient} client
 * @param {import('@supabase/supabase-js').User} user
 * @param {string} [nameOverride]
 */
export async function syncUserProfile(client, user, nameOverride) {
  const meta = user.user_metadata ?? {};
  const displayName =
    (typeof nameOverride === 'string' && nameOverride.trim()) ||
    (typeof meta.name === 'string' && meta.name.trim()) ||
    (typeof meta.full_name === 'string' && meta.full_name.trim()) ||
    null;

  const payload = {
    id: user.id,
    email: user.email ?? null,
    name: displayName ?? '',
  };

  const { error } = await client.from('users').upsert(payload, { onConflict: 'id' });
  if (error) {
    console.warn('[auth] Could not sync public.users:', error.message);
  }
}
