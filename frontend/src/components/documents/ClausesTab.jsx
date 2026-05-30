import { useState, useMemo } from 'react';
import { Scale, ChevronRight, ChevronDown, Info, ShieldAlert } from 'lucide-react';

/* ─────────────────────────────────────────────
   Severity Config — drives background tint,
   border colour, dot, and badge label per card
───────────────────────────────────────────── */
const SEVERITY = {
  Critical: {
    wrap:   'bg-red-50/60 border-red-100',
    badge:  'bg-red-100 text-red-700 border-red-200',
    dot:    'bg-red-500',
    label:  'Critical Risk',
  },
  Important: {
    wrap:   'bg-amber-50/50 border-amber-100',
    badge:  'bg-amber-100 text-amber-700 border-amber-200',
    dot:    'bg-amber-400',
    label:  'High Priority',
  },
  Standard: {
    wrap:   'bg-white border-slate-100',
    badge:  'bg-slate-100 text-slate-500 border-slate-200',
    dot:    'bg-slate-300',
    label:  'Standard',
  },
};

/* ─────────────────────────────────────────────
   Strip leading emoji from category labels
   (backend stores them with emoji prefix)
───────────────────────────────────────────── */
function stripEmoji(str) {
  if (!str) return 'Legal Insight';
  return str.replace(/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}️]\s*/u, '').trim();
}

function conciseSummary(text) {
  const clean = String(text || '')
    .replace(/key pattern observed\s*:\s*/gi, '')
    .replace(/primary impact areas\s*:\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!clean) return '';
  const parts = clean.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean);
  return parts.slice(0, 2).join(' ');
}

/* ─────────────────────────────────────────────
   Insight Group Card — executive briefing style
───────────────────────────────────────────── */
function InsightGroupCard({ group }) {
  const [open, setOpen] = useState(false);
  const sev = SEVERITY[group.importance_label] || SEVERITY.Standard;
  const title = stripEmoji(group.label ?? group.category);

  /* Ensure summary is displayed in full — never truncated */
  const summary = conciseSummary(group.summary || '');

  const hasRisks = group.key_risks?.length > 0;

  return (
    <article className={`rounded-2xl border ${sev.wrap} transition-shadow duration-300 hover:shadow-[0_8px_32px_-8px_rgba(0,0,0,0.08)]`}>
      <div className="p-6 sm:p-8">

        {/* ── Header ─────────────────────────────── */}
        <div className="flex items-start justify-between gap-4 mb-5">
          <h3 className="text-[17px] font-bold text-slate-900 leading-snug tracking-tight">
            {title}
          </h3>
          <div className={`flex items-center gap-1.5 shrink-0 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-widest ${sev.badge}`}>
            <div className={`h-1.5 w-1.5 rounded-full ${sev.dot}`} />
            {sev.label}
          </div>
        </div>

        {/* ── AI Summary (NEVER truncated) ────────── */}
        {summary && (
          <p className="text-[15px] leading-[1.75] text-slate-700 font-normal mb-6">
            {summary}
          </p>
        )}

        {/* keep card concise: no extra narrative blocks */}

        {/* ── Footer: source count + expandable legal text ── */}
        <div className={`flex items-center justify-between ${hasRisks ? 'pt-5 border-t border-slate-200/60' : ''}`}>
          <div className="flex items-center gap-1.5">
            <Info className="w-3 h-3 text-slate-300" />
            <span className="text-[11px] text-slate-400">
              Synthesized from {group.source_count ?? group.clauses?.length ?? 1} source clause{(group.source_count ?? 1) !== 1 ? 's' : ''}
            </span>
          </div>
          {group.clauses?.length > 0 && (
            <button
              onClick={() => setOpen(o => !o)}
              className="flex items-center gap-1 text-[11px] font-bold text-slate-400 hover:text-slate-800 transition-colors uppercase tracking-widest"
            >
              {open
                ? <><ChevronDown className="w-3 h-3" /> Hide Legal Text</>
                : <><ChevronRight className="w-3 h-3" /> View Original Legal Text</>}
            </button>
          )}
        </div>

        {/* ── Expandable Legal Text (secondary, collapsed by default) ── */}
        {open && group.clauses?.length > 0 && (
          <div className="mt-5 rounded-2xl bg-slate-950/[0.03] border border-slate-200/60 divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {group.clauses.map((clause, i) => (
              <div key={i} className="px-5 py-4">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-2">
                  {clause.title || `Clause ${i + 1}`}
                </p>
                <p className="text-[12px] leading-relaxed text-slate-400 font-mono whitespace-pre-wrap">
                  {clause.full_text || clause.text || '—'}
                </p>
              </div>
            ))}
          </div>
        )}

      </div>
    </article>
  );
}

/* ─────────────────────────────────────────────
   Category Filter Pills
───────────────────────────────────────────── */
const CATEGORY_LABELS = {
  risks:        'Risk',
  finance:      'Finance',
  construction: 'Construction',
  exit:         'Exit Rights',
  dispute:      'Disputes',
  protections:  'Protections',
};

function CategoryFilter({ groups, active, onChange }) {
  const cats = useMemo(() => {
    const seen = new Map();
    seen.set(null, 0);
    for (const g of groups) {
      if (!seen.has(g.category)) seen.set(g.category, 0);
      seen.set(g.category, seen.get(g.category) + 1);
      seen.set(null, seen.get(null) + 1);
    }
    return [...seen.entries()].map(([key, count]) => ({
      key,
      label: key === null ? `All (${count})` : `${CATEGORY_LABELS[key] ?? key} (${count})`,
    }));
  }, [groups]);

  if (cats.length <= 2) return null;

  return (
    <div className="flex flex-wrap gap-2 mb-7">
      {cats.map(({ key, label }) => (
        <button
          key={key ?? 'all'}
          onClick={() => onChange(active === key ? null : key)}
          className={`rounded-full px-4 py-1.5 text-[12px] font-semibold border transition-all ${
            active === key
              ? 'bg-slate-900 text-white border-slate-900 shadow-md'
              : 'bg-white text-slate-500 border-slate-200 hover:border-slate-400 hover:text-slate-800'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Fallback Card — for raw-clause fallback path
───────────────────────────────────────────── */
function FallbackClauseCard({ clause }) {
  const [open, setOpen] = useState(false);
  const sev = SEVERITY[clause.importance_label] || SEVERITY.Standard;
  const title = stripEmoji(clause.title ?? clause.clause_type ?? 'Legal Provision');
  const summary = (clause.summary || clause.ai_summary || '').trim();

  return (
    <article className={`rounded-2xl border ${sev.wrap} p-6`}>
      <div className="flex items-start justify-between gap-4 mb-4">
        <h3 className="text-base font-bold text-slate-900">{title}</h3>
        <div className={`flex items-center gap-1.5 shrink-0 px-2.5 py-1 rounded-full border text-[10px] font-bold uppercase tracking-widest ${sev.badge}`}>
          <div className={`h-1.5 w-1.5 rounded-full ${sev.dot}`} />
          {sev.label}
        </div>
      </div>
      {summary && (
        <p className="text-[14px] leading-relaxed text-slate-700 mb-5">{summary}</p>
      )}
      <div className="flex items-center justify-between pt-4 border-t border-slate-200/60">
        <span className="text-[11px] text-slate-400">Single provision</span>
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-1 text-[11px] font-bold text-slate-400 hover:text-slate-800 transition-colors uppercase tracking-widest"
        >
          {open ? <><ChevronDown className="w-3 h-3" /> Hide</> : <><ChevronRight className="w-3 h-3" /> View Legal Text</>}
        </button>
      </div>
      {open && (
        <div className="mt-4 rounded-xl bg-slate-950/[0.03] border border-slate-200/60 px-5 py-4 max-h-48 overflow-y-auto">
          <p className="text-[12px] leading-relaxed text-slate-400 font-mono whitespace-pre-wrap">
            {clause.full_text || clause.text || '—'}
          </p>
        </div>
      )}
    </article>
  );
}

/* ─────────────────────────────────────────────
   Loading Skeleton
───────────────────────────────────────────── */
function LoadingSkeleton() {
  return (
    <div className="space-y-5">
      {[220, 180, 260].map((h, i) => (
        <div key={i} className="rounded-2xl border border-slate-100 bg-white p-7 animate-pulse">
          <div className="flex justify-between mb-5">
            <div className="h-4 w-40 bg-slate-100 rounded" />
            <div className="h-5 w-24 bg-slate-100 rounded-full" />
          </div>
          <div className="space-y-2 mb-6">
            <div className="h-3 w-full bg-slate-50 rounded" />
            <div className="h-3 w-5/6 bg-slate-50 rounded" />
            <div className="h-3 w-3/4 bg-slate-50 rounded" />
          </div>
          <div className="h-px bg-slate-100 mb-4" />
          <div className="flex justify-between">
            <div className="h-3 w-28 bg-slate-100 rounded" />
            <div className="h-3 w-32 bg-slate-100 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Empty State
───────────────────────────────────────────── */
function EmptyState() {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 py-16 text-center">
      <Scale className="w-8 h-8 text-slate-200 mx-auto mb-3" />
      <p className="text-sm font-semibold text-slate-400 uppercase tracking-widest">
        No Insights Available
      </p>
      <p className="text-xs text-slate-400 mt-1">
        Legal intelligence will appear once the document has been fully analyzed.
      </p>
    </div>
  );
}

/* ─────────────────────────────────────────────
   Main Export
───────────────────────────────────────────── */
const CRITICAL_TYPES = ['indemnity', 'termination', 'liability', 'penalty', 'default', 'arbitration', 'insurance'];

export default function ClausesTab({ clausesData, isLoading }) {
  const [filter, setFilter] = useState(null);

  /* Parse incoming data — handles both new {clauses, insight_groups} and legacy array */
  const { insightGroups, rawClauses } = useMemo(() => {
    if (!clausesData) return { insightGroups: [], rawClauses: [] };
    if (Array.isArray(clausesData)) return { insightGroups: [], rawClauses: clausesData };
    return {
      insightGroups: Array.isArray(clausesData.insight_groups) ? clausesData.insight_groups : [],
      rawClauses:    Array.isArray(clausesData.clauses)        ? clausesData.clauses        : [],
    };
  }, [clausesData]);

  const filtered = useMemo(() => {
    if (!filter) return insightGroups;
    return insightGroups.filter(g => g.category === filter);
  }, [insightGroups, filter]);

  if (isLoading) return <LoadingSkeleton />;

  /* ── Grouped executive briefing view ──────── */
  if (insightGroups.length > 0) {
    return (
      <div className="max-w-3xl mx-auto">
        <CategoryFilter groups={insightGroups} active={filter} onChange={setFilter} />
        <div className="space-y-5">
          {filtered.map((group, i) => (
            <InsightGroupCard key={`${group.category}-${i}`} group={group} />
          ))}
          {filtered.length === 0 && filter && (
            <p className="py-10 text-center text-sm text-slate-400">
              No insights in this category.
            </p>
          )}
        </div>
      </div>
    );
  }

  /* ── Fallback: render sorted raw clauses ──── */
  if (rawClauses.length > 0) {
    const sorted = [...rawClauses]
      .sort((a, b) => {
        const pa = CRITICAL_TYPES.includes(a.clause_type) ? 0 : 1;
        const pb = CRITICAL_TYPES.includes(b.clause_type) ? 0 : 1;
        return pa !== pb ? pa - pb : (b.importance_score || 0) - (a.importance_score || 0);
      })
      .slice(0, 8);

    return (
      <div className="max-w-3xl mx-auto space-y-5">
        {sorted.map((clause, i) => (
          <FallbackClauseCard key={i} clause={clause} />
        ))}
      </div>
    );
  }

  return <EmptyState />;
}
