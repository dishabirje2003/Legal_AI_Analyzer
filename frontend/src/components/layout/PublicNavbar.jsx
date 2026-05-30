import { Link, NavLink } from 'react-router-dom';

/**
 * Minimal top bar for marketing and auth pages (matches app typography and colors).
 */
export default function PublicNavbar() {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link
          to="/"
          className="flex items-center gap-2 text-slate-900 transition-opacity hover:opacity-80"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-blue-800 text-sm font-bold text-white shadow-sm shadow-blue-600/25">
            LA
          </span>
          <span className="text-sm font-semibold tracking-tight sm:text-base">Legal AI Analyzer</span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink
            to="/login"
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? 'text-blue-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
            }
          >
            Log in
          </NavLink>
          <Link
            to="/signup"
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white shadow-sm transition-all hover:bg-slate-800 active:scale-[0.98]"
          >
            Sign up
          </Link>
        </nav>
      </div>
    </header>
  );
}
