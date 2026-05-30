/** @param {import('@supabase/supabase-js').User | null | undefined} user */
export function getUserDisplayName(user) {
  if (!user) return '';
  const m = user.user_metadata ?? {};
  if (typeof m.name === 'string' && m.name.trim()) return m.name.trim();
  if (typeof m.full_name === 'string' && m.full_name.trim()) return m.full_name.trim();
  const email = user.email?.split('@')[0];
  return email || 'Account';
}

/** @param {import('@supabase/supabase-js').User | null | undefined} user */
export function getUserInitials(user) {
  if (!user) return '?';
  const name = getUserDisplayName(user);
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  if (parts.length === 1 && parts[0].length >= 2) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  const ch = user.email?.[0];
  return ch ? ch.toUpperCase() : '?';
}
