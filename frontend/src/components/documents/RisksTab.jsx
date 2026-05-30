import { useMemo, useState } from 'react';
import { ShieldCheck, AlertTriangle, Info, ChevronRight, ChevronDown } from 'lucide-react';

/* ─── Helpers ────────────────────────────────── */
const LEVEL = {
  high:   { label: 'High',   dot: 'bg-red-500',   text: 'text-red-600',   bg: 'bg-red-50',   border: 'border-red-100'   },
  medium: { label: 'Medium', dot: 'bg-amber-400',  text: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-100' },
  low:    { label: 'Low',    dot: 'bg-emerald-500',text: 'text-emerald-600',bg: 'bg-emerald-50',border: 'border-emerald-100' },
};

/* The backend already stores risk_score on a 0-100 scale where 100 = fully safe.
   Do NOT invert. Simply clamp to [0, 100]. */
function safetyScore(raw) {
  const n = Number(raw);
  if (isNaN(n)) return null;
  return Math.max(0, Math.min(100, Math.round(n)));
}

function safetyColor(score) {
  if (score == null) return { arc: '#94a3b8', label: 'Unknown',       text: 'text-slate-500'   };
  if (score >= 70)   return { arc: '#10b981', label: 'Low Risk',       text: 'text-emerald-600' };
  if (score >= 40)   return { arc: '#f59e0b', label: 'Moderate Risk',  text: 'text-amber-600'   };
  return                    { arc: '#ef4444', label: 'High Risk',       text: 'text-red-600'     };
}

/* Centered full-width gauge */
function ScoreGauge({ score }) {
  const pct   = score ?? 0;
  const color = safetyColor(score);
  const TOTAL = Math.PI * 48;          // r=48, half-circle ≈ 150.8
  const filled = (pct / 100) * TOTAL;

  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width="140" height="82" viewBox="0 0 140 82" fill="none">
        {/* Track */}
        <path d="M 16 72 A 48 48 0 0 1 124 72" stroke="#e2e8f0" strokeWidth="11" strokeLinecap="round" />
        {/* Filled */}
        <path
          d="M 16 72 A 48 48 0 0 1 124 72"
          stroke={color.arc}
          strokeWidth="11"
          strokeLinecap="round"
          strokeDasharray={`${Math.max(filled, pct > 0 ? 2 : 0)} ${TOTAL}`}
          style={{ transition: 'stroke-dasharray 0.9s ease-out' }}
        />
        <text x="70" y="67" textAnchor="middle" fontSize="26" fontWeight="800" fill="#0f172a">
          {score != null ? score : '—'}
        </text>
      </svg>
      <p className={`text-[12px] font-bold uppercase tracking-widest ${color.text}`}>{color.label}</p>
      <p className="text-[10px] text-slate-400 mt-0.5">Safety Score · higher is safer</p>
    </div>
  );
}


/* Risk breakdown row — tighter + visual progress track */
const LEVEL_BAR = { high: 100, medium: 60, low: 28 };
function RiskDimension({ label, level }) {
  const cfg = LEVEL[level?.toLowerCase()] || LEVEL.low;
  const barW = LEVEL_BAR[level?.toLowerCase()] ?? 20;
  return (
    <div className="flex items-center gap-3 py-1.5 border-b border-slate-100/80 last:border-0">
      <span className="text-[13px] text-slate-700 font-medium w-36 shrink-0">{label}</span>
      <div className="flex-1 relative h-1.5 rounded-full bg-slate-100">
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all duration-700"
          style={{ width: `${barW}%`, background: cfg.dot.includes('red') ? '#ef4444' : cfg.dot.includes('amber') ? '#f59e0b' : '#10b981' }}
        />
      </div>
      <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${cfg.bg} border ${cfg.border} shrink-0`}>
        <div className={`h-1.5 w-1.5 rounded-full ${cfg.dot}`} />
        <span className={`text-[10px] font-bold uppercase tracking-wider ${cfg.text}`}>{cfg.label}</span>
      </div>
    </div>
  );
}


const RISK_TYPE_TO_TAGS = {
  liability: ['Liability', 'Financial'],
  indemnity: ['Liability', 'Financial'],
  financial: ['Financial'],
  termination: ['Termination', 'Operational'],
  compliance: ['Compliance'],
  operational: ['Operational'],
  ambiguity: ['Operational'],
  litigation: ['Litigation'],
  tax: ['Financial', 'Compliance'],
  insurance: ['Insurance'],
  timeline: ['Timeline', 'Operational'],
};

function cleanExplanation(value) {
  const raw = String(value || '')
    .replace(/key pattern observed\s*:\s*/gi, '')
    .replace(/primary impact areas\s*:\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim();
  if (!raw) return 'Material contractual exposure is identified and requires legal review.';
  const parts = raw
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return parts.slice(0, 2).join(' ');
}

function getRiskTags(risk) {
  if (Array.isArray(risk.tags) && risk.tags.length) {
    return [...new Set(risk.tags.map((t) => String(t).trim()).filter(Boolean))].slice(0, 3);
  }
  const key = String(risk.risk_type || '').toLowerCase();
  return RISK_TYPE_TO_TAGS[key] || ['Operational'];
}

/* Individual risk card */
function RiskCard({ risk, highlighted }) {
  const [openLegalText, setOpenLegalText] = useState(false);
  const sev = risk.severity?.toLowerCase() || 'low';
  const cfg = LEVEL[sev] || LEVEL.low;
  const tags = getRiskTags(risk);
  const affectedParty = risk.affected_party || risk.party || null;
  const legalTexts = useMemo(() => {
    const raw = [
      risk.clause_text,
      ...(Array.isArray(risk.source_clause_texts) ? risk.source_clause_texts : []),
    ]
      .map((x) => String(x || '').trim())
      .filter(Boolean);
    return [...new Set(raw)].slice(0, 4);
  }, [risk.clause_text, risk.source_clause_texts]);

  return (
    <div className={`rounded-xl border ${cfg.border} ${cfg.bg} p-4 ${highlighted ? 'ring-2 ring-blue-300 ring-offset-2 ring-offset-white' : ''}`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 shrink-0">
          {sev === 'high'   && <AlertTriangle className="w-4 h-4 text-red-500" />}
          {sev === 'medium' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
          {sev === 'low'    && <Info          className="w-4 h-4 text-emerald-500" />}
        </div>
        <div className="min-w-0">
          {risk.title && (
            <p className="text-[13px] font-semibold text-slate-900 mb-0.5">{risk.title}</p>
          )}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className={`text-[10px] font-bold uppercase tracking-widest ${cfg.text}`}>
              {cfg.label} Risk
            </span>
          </div>
          <p className="text-[13.5px] text-slate-700 leading-relaxed mb-2">{cleanExplanation(risk.explanation)}</p>

          <div className="flex flex-wrap items-center gap-1.5 mb-2.5">
            {tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-slate-200 bg-white/80 px-2 py-0.5 text-[10px] font-medium text-slate-600"
              >
                {tag}
              </span>
            ))}
          </div>

          {affectedParty ? (
            <p className="text-[11px] text-slate-500 mb-2">
              Affected Party: <span className="font-semibold text-slate-700">{affectedParty}</span>
            </p>
          ) : null}

          {legalTexts.length > 0 ? (
            <div className="pt-1">
              <button
                type="button"
                onClick={() => setOpenLegalText((v) => !v)}
                className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-slate-800"
              >
                {openLegalText ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                View Legal Text
              </button>
              {openLegalText ? (
                <div className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-slate-200 bg-slate-100/70 p-2.5">
                  {legalTexts.map((txt, idx) => (
                    <p key={idx} className="mb-2 text-[11px] leading-relaxed text-slate-600 last:mb-0">
                      {txt}
                    </p>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/* Shared section heading style */
function SectionHeading({ children }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-0.5 h-4 rounded-full bg-slate-400" />
      <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{children}</p>
    </div>
  );
}

export default function RisksTab({ risksData, isLoading, focusedRisk }) {

  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-44 rounded-2xl bg-slate-100" />
        <div className="h-36 rounded-2xl bg-slate-100" />
        <div className="h-24 rounded-2xl bg-slate-100" />
      </div>
    );
  }

  if (!risksData || !risksData.summary) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 py-14 px-8 text-center">
        <ShieldCheck className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
        <p className="text-sm font-bold text-slate-700 mb-1">No Major Risks Detected</p>
        <p className="text-[13px] text-slate-500 leading-relaxed max-w-xs mx-auto">
          No major legal or financial risks were detected. The agreement appears structurally balanced,
          though standard contractual obligations still apply.
        </p>
      </div>
    );
  }

  const { summary, high_risks = [], medium_risks = [], low_risks = [] } = risksData;
  const allRisks = [...high_risks, ...medium_risks, ...low_risks];
  const score = safetyScore(summary.risk_score);

  const hasRiskType = (types) =>
    allRisks.some(r => types.some(t => (r.risk_type || '').toLowerCase().includes(t)));

  const dimensions = [
    { label: 'Financial Risk', level: hasRiskType(['financial', 'payment', 'fee', 'rent', 'tax']) ? (high_risks.some(r => (r.risk_type || '').toLowerCase().includes('financial')) ? 'high' : 'medium') : 'low' },
    { label: 'Liability Exposure', level: hasRiskType(['indemnity', 'liabilit', 'harm']) ? 'high' : 'low' },
    { label: 'Termination Risk', level: hasRiskType(['terminat', 'cancel', 'exit']) ? 'high' : 'low' },
    { label: 'Compliance Risk', level: hasRiskType(['compli', 'regulat', 'approv', 'permit']) ? 'medium' : 'low' },
    { label: 'Operational Risk', level: hasRiskType(['construct', 'deadline', 'timeline', 'delay']) ? 'medium' : 'low' },
  ];

  const prioritizedRisks = useMemo(() => {
    const sevWeight = { high: 0, medium: 1, low: 2 };
    return [...allRisks]
      .sort((a, b) => (sevWeight[a.severity?.toLowerCase() || 'low'] - sevWeight[b.severity?.toLowerCase() || 'low']))
      .slice(0, 8);
  }, [allRisks]);

  return (
    <div className="space-y-4">

      {/* ── Score + Overview (stacked) ──────── */}
      <div className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm text-center">
        <ScoreGauge score={score} />
        <div className="mt-4 grid grid-cols-3 gap-2 text-left">
          <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-red-600">High</p>
            <p className="text-lg font-semibold text-red-700">{high_risks.length}</p>
          </div>
          <div className="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600">Medium</p>
            <p className="text-lg font-semibold text-amber-700">{medium_risks.length}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-600">Low</p>
            <p className="text-lg font-semibold text-slate-700">{low_risks.length}</p>
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-slate-100 text-left">
          <SectionHeading>AI Risk Overview</SectionHeading>
          <p className="text-[13px] leading-relaxed text-slate-700">
            {summary.overview ||
              `This agreement has been classified as a ${summary.contract_type || 'legal'} contract with a ${summary.risk_level?.toLowerCase() || 'standard'} risk profile. ` +
              (high_risks.length > 0
                ? `${high_risks.length} high-priority risk${high_risks.length > 1 ? 's were' : ' was'} identified requiring immediate review.`
                : 'No critical risk factors were identified.')}
          </p>
          <p className="mt-2 text-[11px] text-slate-400">
            Contract type: <span className="text-slate-600 font-medium">{summary.contract_type || 'General Agreement'}</span>
          </p>
        </div>
      </div>

      {/* ── Risk Breakdown ───────────────────── */}
      <div className="rounded-2xl border border-slate-100 bg-white px-5 py-4 shadow-sm">
        <SectionHeading>Risk Breakdown</SectionHeading>
        <div>
          {dimensions.map(d => <RiskDimension key={d.label} {...d} />)}
        </div>
      </div>

      {/* ── Individual Risk Cards ────────────── */}
      {prioritizedRisks.length > 0 && (
        <div className="space-y-3">
          <SectionHeading>Identified Risks</SectionHeading>
          {prioritizedRisks.map((risk, i) => {
            const target = focusedRisk;
            const matches =
              !!target &&
              (
                (target.clause_id && risk.clause_id && String(target.clause_id) === String(risk.clause_id)) ||
                (target.explanation &&
                  risk.explanation &&
                  String(target.explanation).toLowerCase() === String(risk.explanation).toLowerCase())
              );
            return <RiskCard key={i} risk={risk} highlighted={matches} />;
          })}
        </div>
      )}

    </div>
  );
}
