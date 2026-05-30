import { Link } from 'react-router-dom';

export default function MarketingFooter() {
  return (
    <footer className="border-t border-slate-200 bg-slate-50/80">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-12 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div>
          <p className="text-sm font-semibold text-slate-900">AI Based Legal Document Summarization and Analysis System</p>
          <p className="mt-1 text-sm text-slate-500">AI-powered legal document analysis</p>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-slate-600">
          <Link to="/login" className="transition-colors hover:text-slate-900">
            Log in
          </Link>
          <Link to="/signup" className="transition-colors hover:text-slate-900">
            Sign up
          </Link>
          <a
            href="#features"
            className="transition-colors hover:text-slate-900"
            onClick={(e) => {
              e.preventDefault();
              document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
            }}
          >
            Features
          </a>
        </div>
      </div>
      <div className="border-t border-slate-200/80 py-4 text-center text-xs text-slate-400">
        © {new Date().getFullYear()} Legal AI Analyzer. All rights reserved.
      </div>
    </footer>
  );
}
