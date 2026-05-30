import { useState, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Upload,
  FolderOpen,
  AlertTriangle,
  Settings,
  FileText,
  LogOut,
  X,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { getUserDisplayName, getUserInitials } from '../../lib/userDisplay.js';

const mainNav = [
  { icon: LayoutDashboard, label: 'Dashboard',       path: '/dashboard', end: true },
  { icon: Upload,          label: 'Upload Document', path: '/upload' },
  { icon: FolderOpen,      label: 'Document Library',path: '/library' },
];

const soonNav = [
  { icon: AlertTriangle, label: 'Risk Alerts',  path: '/risks'     },
  { icon: Settings,      label: 'Settings',     path: '/settings'  },
];

export default function Sidebar({ mobileOpen, onCloseMobile }) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();
  const displayName = getUserDisplayName(user);
  const initials    = getUserInitials(user);
  const [collapsed, setCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarMode');
    return saved === 'compact';
  });

  // Listen for changes from Settings page
  useEffect(() => {
    const syncSidebar = () => {
      const saved = localStorage.getItem('sidebarMode');
      setCollapsed(saved === 'compact');
    };
    window.addEventListener('storage', syncSidebar);
    return () => window.removeEventListener('storage', syncSidebar);
  }, []);

  // Update localStorage when toggled manually
  const toggleCollapsed = () => {
    setCollapsed(prev => {
      const newVal = !prev;
      localStorage.setItem('sidebarMode', newVal ? 'compact' : 'expanded');
      window.dispatchEvent(new Event('storage')); // Notify other components (like Settings)
      return newVal;
    });
  };

  async function handleLogout() {
    onCloseMobile();
    await signOut();
    navigate('/', { replace: true });
  }

  const linkClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-200 group relative ${
      isActive
        ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30'
        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
    }`;

  const moreClass = ({ isActive }) =>
    `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-all duration-200 group relative ${
      isActive
        ? 'bg-slate-800 text-white'
        : 'text-slate-300 hover:bg-slate-800 hover:text-white'
    }`;

  /* Tooltip shown when collapsed */
  const Tip = ({ label }) => (
    <span className="pointer-events-none absolute left-full top-1/2 ml-2 -translate-y-1/2 whitespace-nowrap rounded-lg bg-slate-900 px-2.5 py-1.5 text-xs font-medium text-white opacity-0 shadow-lg transition-opacity group-hover:opacity-100 z-50">
      {label}
    </span>
  );

  const navBody = (showLabels) => (
    <>
      {/* Logo */}
      <button
        type="button"
        onClick={() => {
          navigate('/');
          onCloseMobile();
        }}
        className="flex w-full items-center gap-3 border-b border-slate-700 px-4 py-5 text-left transition-colors hover:bg-slate-800/40"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-700">
          <FileText className="h-5 w-5 text-white" />
        </div>
        {showLabels && (
          <div className="min-w-0">
            <h1 className="text-base font-bold text-white leading-tight">Legal AI</h1>
            <p className="text-[11px] text-slate-400">Document Intelligence</p>
          </div>
        )}
      </button>

      {/* Nav links */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-4">
        {mainNav.map(item => (
          <NavLink key={item.path} to={item.path} end={item.end} className={linkClass} onClick={onCloseMobile}>
            <item.icon className="h-4.5 w-4.5 shrink-0 h-[18px] w-[18px]" />
            {showLabels ? <span className="truncate">{item.label}</span> : <Tip label={item.label} />}
          </NavLink>
        ))}

        <div className="pt-3">
          {showLabels && (
            <p className="mb-1.5 px-3 text-[10px] font-bold uppercase tracking-widest text-slate-600">More</p>
          )}
          {soonNav.map(item => (
            <NavLink key={item.path} to={item.path} className={moreClass} onClick={onCloseMobile}>
              <item.icon className="h-[18px] w-[18px] shrink-0" />
              {showLabels ? <span className="truncate">{item.label}</span> : <Tip label={item.label} />}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* User / logout */}
      <div className="border-t border-slate-700 p-2">
        <button
          type="button"
          onClick={handleLogout}
          className="flex w-full cursor-pointer items-center gap-3 rounded-lg p-2 text-left transition-colors hover:bg-slate-800 group relative"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
            {initials}
          </div>
          {showLabels ? (
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">{displayName}</p>
              <p className="truncate text-[11px] text-slate-400">{user?.email ?? ''}</p>
            </div>
          ) : (
            <Tip label={`${displayName} · Sign out`} />
          )}
          {showLabels && <LogOut className="h-4 w-4 shrink-0 text-slate-500" />}
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className="hidden h-screen shrink-0 flex-col border-r border-slate-800 bg-[#0f172a] text-white lg:flex transition-all duration-300 ease-in-out overflow-hidden"
        style={{ width: collapsed ? 56 : 220 }}
      >
        {navBody(!collapsed)}

        {/* Collapse toggle */}
        <button
          type="button"
          onClick={toggleCollapsed}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="absolute bottom-20 -right-3 flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-slate-400 hover:text-white shadow-md z-10"
          style={{ position: 'absolute', left: collapsed ? 44 : 208 }}
        >
          {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
        </button>
      </aside>

      {/* Mobile overlay */}
      <div
        className={`fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm transition-opacity lg:hidden ${
          mobileOpen ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
        aria-hidden={!mobileOpen}
        onClick={onCloseMobile}
      />

      {/* Mobile drawer */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col bg-[#0f172a] text-white shadow-2xl transition-transform duration-200 ease-out lg:hidden ${
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-hidden={!mobileOpen}
      >
        <div className="flex items-center justify-end border-b border-slate-700 p-2">
          <button type="button" onClick={onCloseMobile} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{navBody(true)}</div>
      </aside>
    </>
  );
}
