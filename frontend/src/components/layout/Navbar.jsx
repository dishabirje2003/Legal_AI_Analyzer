import { Upload, Menu } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext.jsx';
import { getUserInitials, getUserDisplayName } from '../../lib/userDisplay.js';

/**
 * @param {object} props
 * @param {() => void} props.onOpenMobileNav
 */
export default function Navbar({ onOpenMobileNav }) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const initials = getUserInitials(user);
  const displayName = getUserDisplayName(user);

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 shadow-sm sm:px-6">
      <div className="flex items-center gap-2 lg:hidden">
        <button
          type="button"
          onClick={onOpenMobileNav}
          className="rounded-lg p-2 text-slate-600 hover:bg-slate-100"
          aria-label="Open navigation"
        >
          <Menu className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1" />

      <div className="flex shrink-0 items-center gap-2 sm:gap-4">
        <button
          type="button"
          onClick={() => navigate('/upload')}
          className="hidden items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white shadow-md shadow-blue-500/20 transition-colors hover:bg-blue-700 sm:inline-flex"
        >
          <Upload className="h-4 w-4" />
          <span className="hidden md:inline">Upload Document</span>
          <span className="md:hidden">Upload</span>
        </button>

        <button
          type="button"
          onClick={() => navigate('/upload')}
          className="inline-flex rounded-lg bg-blue-600 p-2 text-white shadow-md shadow-blue-500/20 sm:hidden"
          aria-label="Upload document"
        >
          <Upload className="h-5 w-5" />
        </button>

        <div
          className="flex h-9 w-9 cursor-default items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-xs font-semibold text-white ring-2 ring-slate-200"
          title={displayName}
        >
          {initials}
        </div>
      </div>
    </header>
  );
}
