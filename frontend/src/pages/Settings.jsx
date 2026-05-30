import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext.jsx';
import { getUserDisplayName } from '../lib/userDisplay.js';
import { supabase } from '../lib/supabase.js';
import {
  deleteAccountForUser,
  deleteAllDocumentsForUser,
  getSettingsProfile,
  updateSettingsProfile,
} from '../lib/api.js';
import {
  User,
  Palette,
  Shield,
  AlertTriangle,
  Clock,
  Monitor,
  Moon,
  Sun,
  LayoutPanelLeft,
  PanelLeftClose,
  Save,
  CheckCircle2
} from 'lucide-react';

/* ─── Modal Component ────────────────────────────── */
function ConfirmModal({
  isOpen,
  title,
  message,
  onConfirm,
  onCancel,
  isProcessing,
  requireDeleteConfirm = false,
}) {
  const [confirmText, setConfirmText] = useState('');
  useEffect(() => {
    if (!isOpen) setConfirmText('');
  }, [isOpen]);
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md animate-in fade-in zoom-in-95 rounded-2xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center gap-3 text-red-600">
          <AlertTriangle className="h-6 w-6" />
          <h3 className="text-lg font-bold text-slate-900">{title}</h3>
        </div>
        <p className="mb-6 text-sm text-slate-600 leading-relaxed">{message}</p>
        {requireDeleteConfirm ? (
          <div className="mb-5">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-slate-500">
              Type DELETE to continue
            </label>
            <input
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
            />
          </div>
        ) : null}
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={isProcessing}
            className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(confirmText)}
            disabled={isProcessing || (requireDeleteConfirm && confirmText.trim().toUpperCase() !== 'DELETE')}
            className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 shadow-sm disabled:opacity-70"
          >
            {isProcessing ? <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-r-transparent" /> : null}
            Yes, proceed
          </button>
        </div>
      </div>
    </div>
  );
}

/* ─── Settings Page ──────────────────────────────── */
export default function Settings() {
  const { user, signOut, session } = useAuth();
  const navigate = useNavigate();
  const displayName = getUserDisplayName(user);

  const [isSaving, setIsSaving] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [actionMessage, setActionMessage] = useState('');
  const [actionError, setActionError] = useState('');

  // Form states
  const [name, setName] = useState(displayName);
  const [email] = useState(user?.email || '');
  const [role, setRole] = useState(user?.user_metadata?.role || 'Legal Analyst');
  
  // Load preferences from local storage
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  const [sidebarMode, setSidebarMode] = useState(() => localStorage.getItem('sidebarMode') || 'expanded');

  // Password change states
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Modal state
  const [modalConfig, setModalConfig] = useState({ isOpen: false, title: '', message: '', onConfirm: () => {} });
  const [isProcessingDestructive, setIsProcessingDestructive] = useState(false);
  const [baseline, setBaseline] = useState({
    name: displayName || '',
    role: user?.user_metadata?.role || 'Legal Analyst',
    theme: localStorage.getItem('theme') || 'light',
    sidebarMode: localStorage.getItem('sidebarMode') || 'expanded',
  });
  const accessToken = session?.access_token || '';

  useEffect(() => {
    let cancelled = false;
    async function loadProfile() {
      if (!user?.id) return;
      try {
        const p = await getSettingsProfile(user.id, accessToken);
        if (cancelled || !p) return;
        const nextName = (typeof p.name === 'string' && p.name.trim()) ? p.name : displayName;
        const nextRole = (typeof p.role === 'string' && p.role.trim()) ? p.role : 'Legal Analyst';
        const nextTheme = (typeof p.theme_preference === 'string' && p.theme_preference.trim()) ? p.theme_preference : (localStorage.getItem('theme') || 'light');
        const nextSidebar = (typeof p.sidebar_mode === 'string' && p.sidebar_mode.trim()) ? p.sidebar_mode : (localStorage.getItem('sidebarMode') || 'expanded');
        setName(nextName);
        setRole(nextRole);
        setTheme(nextTheme);
        setSidebarMode(nextSidebar);
        setBaseline({
          name: nextName,
          role: nextRole,
          theme: nextTheme,
          sidebarMode: nextSidebar,
        });
      } catch {
        // Keep local defaults on failure.
      }
    }
    loadProfile();
    return () => {
      cancelled = true;
    };
  }, [user?.id, accessToken, displayName]);

  const applyTheme = (value) => {
    const resolved = value === 'system'
      ? ((window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light')
      : value;
    document.documentElement.setAttribute('data-theme', resolved === 'dark' ? 'dark' : 'light');
    if (value === 'dark') {
      document.documentElement.classList.add('dark');
    } else if (value === 'light') {
      document.documentElement.classList.remove('dark');
    } else {
      const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.classList.toggle('dark', !!prefersDark);
    }
  };

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Keep state in sync with localStorage if changed elsewhere (e.g. Sidebar toggle)
  useEffect(() => {
    const syncPrefs = () => {
      setTheme(localStorage.getItem('theme') || 'light');
      setSidebarMode(localStorage.getItem('sidebarMode') || 'expanded');
    };
    window.addEventListener('storage', syncPrefs);
    return () => window.removeEventListener('storage', syncPrefs);
  }, []);

  // Scroll Refs
  const profileRef = useRef(null);
  const appearanceRef = useRef(null);
  const securityRef = useRef(null);

  const handleScrollTo = (ref) => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const handleSaveAll = async () => {
    setIsSaving(true);
    setSaveError('');
    setActionError('');
    setActionMessage('');
    try {
      if (!name.trim()) throw new Error('Full name cannot be empty.');
      // 1) Persist profile + preferences in backend
      await updateSettingsProfile({
        user_id: user.id,
        full_name: name.trim(),
        role,
        theme_preference: theme,
        sidebar_mode: sidebarMode,
      }, accessToken);

      // 2) Keep auth metadata in sync for immediate UI usage
      const { error: profileError } = await supabase.auth.updateUser({
        data: { full_name: name.trim(), name: name.trim(), role },
      });
      if (profileError) throw profileError;

      // 3) Save local preferences for fast restore
      localStorage.setItem('theme', theme);
      localStorage.setItem('sidebarMode', sidebarMode);
      window.dispatchEvent(new Event('storage'));
      applyTheme(theme);

      // 4) Update password with real validation
      if (currentPassword || newPassword || confirmPassword) {
        if (!currentPassword) throw new Error('Current password is required.');
        if (newPassword !== confirmPassword) {
          throw new Error('New passwords do not match.');
        }
        if (newPassword.length < 8) {
          throw new Error('Password must be at least 8 characters.');
        }
        const { error: checkError } = await supabase.auth.signInWithPassword({
          email,
          password: currentPassword,
        });
        if (checkError) throw new Error('Current password is incorrect.');
        const { error: passError } = await supabase.auth.updateUser({
          password: newPassword,
        });
        if (passError) throw passError;
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setActionMessage('Password updated successfully.');
      } else {
        setActionMessage('Settings saved successfully.');
      }
      setBaseline({
        name: name.trim(),
        role,
        theme,
        sidebarMode,
      });

      setShowSaved(true);
      setTimeout(() => setShowSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteDocuments = async (confirmationText) => {
    setIsProcessingDestructive(true);
    setActionError('');
    setActionMessage('');
    try {
      await deleteAllDocumentsForUser(user.id, confirmationText || '', accessToken);
      setModalConfig((prev) => ({ ...prev, isOpen: false }));
      setActionMessage('All documents and analysis data deleted.');
      window.dispatchEvent(new Event('documents:changed'));
    } catch (err) {
      setActionError('Failed to delete documents: ' + err.message);
    } finally {
      setIsProcessingDestructive(false);
    }
  };

  const handleDeleteAccount = async (confirmationText) => {
    setIsProcessingDestructive(true);
    setActionError('');
    setActionMessage('');
    try {
      await deleteAccountForUser(user.id, confirmationText || '', accessToken);
      setModalConfig((prev) => ({ ...prev, isOpen: false }));
      await signOut();
      navigate('/');
    } catch (err) {
      setActionError('Account deletion failed: ' + err.message);
    } finally {
      setIsProcessingDestructive(false);
    }
  };

  const confirmDestructive = (title, message, action) => {
    setModalConfig({
      isOpen: true,
      title,
      message,
      onConfirm: action,
      onCancel: () => setModalConfig((prev) => ({ ...prev, isOpen: false }))
    });
  };

  const lastLogin = user?.last_sign_in_at 
    ? new Date(user.last_sign_in_at).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
    : 'Unknown';
  const hasPasswordInput = Boolean(currentPassword || newPassword || confirmPassword);
  const isDirty =
    name.trim() !== baseline.name.trim() ||
    role !== baseline.role ||
    theme !== baseline.theme ||
    sidebarMode !== baseline.sidebarMode;
  const canSave = !isSaving && (isDirty || hasPasswordInput);

  useEffect(() => {
    const onBeforeUnload = (event) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = 'You have unsaved changes';
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [isDirty]);

  return (
    <div className="flex h-full flex-col bg-slate-50 relative overflow-hidden">
      
      {/* ── Internal Top Navigation (Scroll Links) ── */}
      <div className="sticky top-0 z-20 border-b border-slate-200 bg-white/80 backdrop-blur-md px-5 py-3 shadow-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Settings</h1>
            <p className="text-xs text-slate-500">Manage your account and preferences.</p>
          </div>
          <nav className="hidden sm:flex items-center gap-2">
            <button onClick={() => handleScrollTo(profileRef)} className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors">
              <User className="h-4 w-4" /> Profile
            </button>
            <button onClick={() => handleScrollTo(appearanceRef)} className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors">
              <Palette className="h-4 w-4" /> Appearance
            </button>
            <button onClick={() => handleScrollTo(securityRef)} className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900 transition-colors">
              <Shield className="h-4 w-4" /> Security
            </button>
          </nav>
        </div>
      </div>

      {/* ── Main Scrolling Content ── */}
      <div className="flex-1 overflow-y-auto relative scroll-smooth">
        <div className="mx-auto max-w-4xl p-5 md:p-8 lg:p-10 pb-32 space-y-12">
          
          {/* === PROFILE SECTION === */}
          <section ref={profileRef} className="scroll-mt-24 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <User className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-bold text-slate-900">Profile Information</h2>
            </div>
            
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-sm font-medium text-slate-700">Full Name</label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    disabled
                    className="w-full rounded-lg border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm text-slate-500 cursor-not-allowed"
                  />
                  <p className="text-xs text-slate-400 mt-1">Email cannot be changed directly.</p>
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-slate-700">Role</label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    className="w-full rounded-lg border border-slate-200 px-4 py-2.5 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
                  >
                    <option value="Legal Analyst">Legal Analyst</option>
                    <option value="Student">Student</option>
                    <option value="Lawyer">Lawyer</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          {/* === APPEARANCE SECTION === */}
          <section ref={appearanceRef} className="scroll-mt-24 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <Palette className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-bold text-slate-900">Appearance & Layout</h2>
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-slate-400">Theme Preference</h3>
                <div className="grid gap-4 sm:grid-cols-3">
                  {[
                    { id: 'light', label: 'Light', icon: Sun },
                    { id: 'dark', label: 'Dark', icon: Moon },
                  ].map(t => (
                    <button
                      key={t.id}
                      onClick={() => {
                        setTheme(t.id);
                        localStorage.setItem('theme', t.id);
                        applyTheme(t.id);
                        window.dispatchEvent(new Event('storage'));
                      }}
                      className={`flex flex-col items-center justify-center gap-2 rounded-xl border-2 p-3 transition-all ${
                        theme === t.id
                          ? 'border-blue-600 bg-blue-50/50 text-blue-700'
                          : 'border-slate-100 bg-white text-slate-500 hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <t.icon className={`h-5 w-5 ${theme === t.id ? 'text-blue-600' : 'text-slate-400'}`} />
                      <span className="text-xs font-medium">{t.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-slate-400">Sidebar Layout</h3>
                <div className="grid gap-4 sm:grid-cols-2">
                  {[
                    { id: 'expanded', label: 'Expanded', icon: LayoutPanelLeft },
                    { id: 'compact', label: 'Compact', icon: PanelLeftClose },
                  ].map(m => (
                    <button
                      key={m.id}
                      onClick={() => {
                        setSidebarMode(m.id);
                        localStorage.setItem('sidebarMode', m.id);
                        window.dispatchEvent(new Event('storage'));
                      }}
                      className={`flex items-center justify-center gap-3 rounded-xl border-2 p-4 transition-all ${
                        sidebarMode === m.id
                          ? 'border-blue-600 bg-blue-50/50 text-blue-700'
                          : 'border-slate-100 bg-white text-slate-500 hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <m.icon className={`h-5 w-5 ${sidebarMode === m.id ? 'text-blue-600' : 'text-slate-400'}`} />
                      <span className="text-sm font-medium">{m.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          {/* === SECURITY SECTION === */}
          <section ref={securityRef} className="scroll-mt-24 space-y-4">
            <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
              <Shield className="h-5 w-5 text-blue-600" />
              <h2 className="text-lg font-bold text-slate-900">Security & Authentication</h2>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-slate-400">Active Session</h3>
                <div className="flex items-start gap-4 rounded-xl border border-slate-100 bg-slate-50 p-4">
                  <div className="mt-1 shrink-0 rounded-full bg-emerald-100 p-2">
                    <Monitor className="h-4 w-4 text-emerald-600" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-900">Current Session</p>
                    <p className="text-sm text-slate-600 mt-0.5">{email}</p>
                    <div className="mt-2 flex items-center gap-1.5 text-xs font-medium text-slate-500">
                      <Clock className="h-3.5 w-3.5" />
                      Last login: {lastLogin}
                    </div>
                    <div className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                      Active session
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-sm font-bold uppercase tracking-widest text-slate-400">Change Password</h3>
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">Current Password</label>
                    <input
                      type="password"
                      placeholder="••••••••"
                      value={currentPassword}
                      onChange={(e) => setCurrentPassword(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">New Password</label>
                    <input 
                      type="password" 
                      placeholder="••••••••" 
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-slate-700">Confirm New Password</label>
                    <input 
                      type="password" 
                      placeholder="••••••••" 
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      className="w-full rounded-lg border border-slate-200 px-4 py-2 text-sm text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500" 
                    />
                  </div>
                  <p className="text-xs text-slate-400">Leave all password fields blank if you do not wish to change it.</p>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-red-200 bg-red-50/50 p-6 mt-6">
              <h3 className="mb-2 text-sm font-bold uppercase tracking-widest text-red-600">Danger Zone</h3>
              <p className="mb-5 text-sm text-slate-600">Irreversible and destructive actions. Proceed with caution.</p>
              
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-red-100 bg-white p-4 shadow-sm">
                  <div>
                    <p className="text-sm font-bold text-slate-900">Delete all documents</p>
                    <p className="text-xs text-slate-500 mt-0.5">Permanently remove all uploaded files and AI analyses.</p>
                  </div>
                  <button 
                    onClick={() => confirmDestructive("Delete all documents?", "This will permanently delete all your uploaded documents, clauses, risks, summaries, and embeddings. Type DELETE to confirm.", handleDeleteDocuments)}
                    className="shrink-0 rounded-lg border border-red-200 bg-white px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 hover:border-red-300 transition-colors"
                  >
                    Delete Documents
                  </button>
                </div>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-xl border border-red-100 bg-white p-4 shadow-sm">
                  <div>
                    <p className="text-sm font-bold text-slate-900">Delete account</p>
                    <p className="text-xs text-slate-500 mt-0.5">Permanently delete your account and all associated data.</p>
                  </div>
                  <button 
                    onClick={() => confirmDestructive("Delete account?", "This will permanently delete your auth account, profile, and all associated document intelligence data. Type DELETE to confirm.", handleDeleteAccount)}
                    className="shrink-0 rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-red-700 transition-colors"
                  >
                    Delete Account
                  </button>
                </div>
              </div>
            </div>
          </section>

        </div>
        
        {/* ── Sticky Save Button ── */}
        <div className="sticky bottom-0 left-0 right-0 border-t border-slate-200 bg-white/80 backdrop-blur-md px-5 py-4 md:px-8 shadow-[0_-4px_10px_-5px_rgba(0,0,0,0.05)] z-20">
          <div className="mx-auto flex max-w-4xl items-center justify-between">
            <div className="flex flex-col">
              {saveError ? (
                <span className="text-sm font-medium text-red-600">{saveError}</span>
              ) : actionError ? (
                <span className="text-sm font-medium text-red-600">{actionError}</span>
              ) : actionMessage ? (
                <span className="text-sm font-medium text-emerald-600">{actionMessage}</span>
              ) : showSaved ? (
                <span className="flex items-center gap-1.5 text-emerald-600 text-sm font-medium animate-in fade-in">
                  <CheckCircle2 className="h-4 w-4" /> Preferences saved successfully
                </span>
              ) : (
                <span className="text-sm text-slate-500">{isDirty ? 'You have unsaved changes' : 'All changes are saved'}</span>
              )}
            </div>
            <button
              onClick={handleSaveAll}
              disabled={!canSave}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-70 transition-all"
            >
              {isSaving ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-r-transparent" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              Save Changes
            </button>
          </div>
        </div>
      </div>

      <ConfirmModal {...modalConfig} isProcessing={isProcessingDestructive} requireDeleteConfirm />
    </div>
  );
}
