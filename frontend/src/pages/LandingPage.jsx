import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Brain,
  FileSearch,
  FileText,
  Gavel,
  Layers,
  Scale,
  ShieldAlert,
  Sparkles,
  Upload,
} from 'lucide-react';
import PublicNavbar from '../components/layout/PublicNavbar.jsx';
import MarketingFooter from '../components/layout/MarketingFooter.jsx';
import { Card, CardContent } from '../components/ui/Card.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';

const ctaPrimary =
  'inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-medium text-white shadow-md shadow-blue-600/15 transition-all duration-200 hover:bg-blue-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 active:scale-[0.98] sm:min-w-[200px] sm:w-auto';

const ctaOutline =
  'inline-flex w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-6 py-3 text-base font-medium text-slate-800 shadow-sm transition-all duration-200 hover:border-slate-300 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/40 focus-visible:ring-offset-2 active:scale-[0.98] sm:min-w-[160px] sm:w-auto';

const ctaDark =
  'inline-flex items-center justify-center gap-2 rounded-lg border-0 bg-white px-6 py-3 text-base font-medium text-slate-900 shadow-sm transition-all duration-200 hover:bg-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/50 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 active:scale-[0.98]';

const features = [
  {
    title: 'AI Document Analysis',
    description: 'Deep understanding of structure, clauses, and obligations across long legal PDFs.',
    icon: Brain,
  },
  {
    title: 'Risk Detection',
    description: 'Spot ambiguous language, one-sided terms, and compliance-sensitive areas faster.',
    icon: ShieldAlert,
  },
  {
    title: 'Smart Summaries',
    description: 'Executive-ready summaries so your team spends time on strategy, not skimming.',
    icon: Sparkles,
  },
];

const steps = [
  { title: 'Upload document', description: 'Drag and drop contracts or judgments securely.', icon: Upload },
  { title: 'AI processing', description: 'Extraction, NER, and analysis run in the background.', icon: Layers },
  { title: 'Get insights', description: 'Review summaries, entities, and risk signals in one place.', icon: FileText },
];

const useCases = [
  {
    title: 'Contracts',
    description: 'MSAs, NDAs, employment agreements, and vendor contracts—reviewed with consistent rigor.',
    icon: FileText,
  },
  {
    title: 'Court judgments',
    description: 'Quickly grasp holdings, reasoning, and citations from lengthy opinions.',
    icon: Gavel,
  },
];

export default function LandingPage() {
  const { user } = useAuth();
  const getStartedPath = user ? '/dashboard' : '/signup';

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <PublicNavbar />

      <section className="relative overflow-hidden border-b border-slate-200/60 bg-white">
        <div
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(37,99,235,0.12),transparent)]"
          aria-hidden
        />
        <div className="relative mx-auto max-w-6xl px-4 pb-20 pt-16 sm:px-6 sm:pb-28 sm:pt-24 lg:pt-28">
          <div className="mx-auto max-w-3xl text-center">
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-600 shadow-sm">
              <Scale className="h-3.5 w-3.5 text-blue-600" aria-hidden />
              Built for legal workflows
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl sm:leading-tight lg:text-4xl lg:leading-tight">
              AI Based Legal Document Summarization and Analysis System
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-lg text-slate-600 sm:text-xl">
              AI-powered legal document analysis—turn dense files into clear summaries, entities, and
              risk signals your team can act on.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row sm:gap-4">
              <Link to={getStartedPath} className={ctaPrimary}>
                Get started
                <ArrowRight className="h-4 w-4" aria-hidden />
              </Link>
              {!user && (
                <Link to="/login" className={ctaOutline}>
                  Log in
                </Link>
              )}
            </div>
            <p className="mt-6 text-sm text-slate-500">
              No clutter—upload, analyze, and review in a focused workspace designed for legal-tech
              teams.
            </p>
          </div>
        </div>
      </section>

      <section id="features" className="scroll-mt-20 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Everything you need to read less and decide faster
            </h2>
            <p className="mt-3 text-slate-600">
              Purpose-built capabilities for contracts and court materials—without noisy dashboards.
            </p>
          </div>
          <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:gap-8">
            {features.map(({ title, description, icon: Icon }) => (
              <Card
                key={title}
                className="group border-slate-200/80 transition-all duration-300 hover:border-slate-300 hover:shadow-md"
              >
                <CardContent className="p-6 sm:p-8">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-50 text-blue-700 transition-transform duration-300 group-hover:scale-105">
                    <Icon className="h-5 w-5" aria-hidden />
                  </div>
                  <h3 className="mt-5 text-lg font-semibold text-slate-900">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">{description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="border-y border-slate-200 bg-white py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              How it works
            </h2>
            <p className="mt-3 text-slate-600">Three calm steps from file to insight.</p>
          </div>
          <div className="mt-14 grid gap-8 md:grid-cols-3">
            {steps.map(({ title, description, icon: Icon }, i) => (
              <div
                key={title}
                className="relative rounded-2xl border border-slate-100 bg-slate-50/50 p-8 text-center transition-all duration-300 hover:border-slate-200 hover:bg-white hover:shadow-sm"
              >
                <span className="mb-4 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white">
                  {i + 1}
                </span>
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-white text-blue-600 shadow-sm ring-1 ring-slate-200">
                  <Icon className="h-6 w-6" aria-hidden />
                </div>
                <h3 className="mt-5 font-semibold text-slate-900">{title}</h3>
                <p className="mt-2 text-sm text-slate-600">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
              Use cases
            </h2>
            <p className="mt-3 text-slate-600">
              From commercial agreements to litigation outputs—one pipeline for serious documents.
            </p>
          </div>
          <div className="mt-14 grid gap-6 md:grid-cols-2">
            {useCases.map(({ title, description, icon: Icon }) => (
              <Card
                key={title}
                className="overflow-hidden border-slate-200/80 transition-all duration-300 hover:shadow-md"
              >
                <CardContent className="flex gap-6 p-8">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/20">
                    <Icon className="h-7 w-7" aria-hidden />
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900">{title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-600">{description}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-slate-200 bg-slate-900 py-16 text-white sm:py-20">
        <div className="mx-auto max-w-6xl px-4 text-center sm:px-6">
          <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
            Ready to analyze your next document?
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm text-slate-400 sm:text-base">
            Create an account in seconds. No unnecessary fields—just your name, email, and password.
          </p>
          <div className="mt-8">
            <Link to={getStartedPath} className={ctaDark}>
              Get started free
              <ArrowRight className="h-4 w-4" aria-hidden />
            </Link>
          </div>
        </div>
      </section>

      <MarketingFooter />
    </div>
  );
}
