import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  ChevronRight,
  CircleAlert,
  Filter,
  FolderOpen,
  ShieldCheck,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card.jsx';
import { getDocumentRisks, listDocuments } from '../lib/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';

const SEVERITY = ['high', 'medium', 'low'];

const SEVERITY_STYLE = {
  high: {
    label: 'High Risk',
    heading: 'High Risk Alerts',
    badge: 'bg-red-100 text-red-700 ring-red-200',
    card: 'border-red-200 bg-red-50/60',
    icon: 'text-red-500',
    stat: 'bg-red-50 border-red-200 text-red-800',
  },
  medium: {
    label: 'Medium Risk',
    heading: 'Medium Risk Alerts',
    badge: 'bg-amber-100 text-amber-700 ring-amber-200',
    card: 'border-amber-200 bg-amber-50/50',
    icon: 'text-amber-500',
    stat: 'bg-amber-50 border-amber-200 text-amber-800',
  },
  low: {
    label: 'Low Risk',
    heading: 'Low Risk Alerts',
    badge: 'bg-slate-100 text-slate-700 ring-slate-200',
    card: 'border-slate-200 bg-slate-50/70',
    icon: 'text-slate-500',
    stat: 'bg-slate-100 border-slate-200 text-slate-800',
  },
};

function normalizeSeverity(value, fallback = 'low') {
  const sev = String(value || fallback).toLowerCase();
  if (sev === 'high' || sev === 'medium' || sev === 'low') return sev;
  if (sev.includes('high')) return 'high';
  if (sev.includes('med')) return 'medium';
  return 'low';
}

function simplifyRisk(record, document, severity) {
  const title = record?.title || record?.risk_title || record?.risk_type || 'Potential Legal Risk';
  const explanation =
    record?.explanation ||
    record?.summary ||
    record?.description ||
    record?.legal_reason ||
    'Potentially problematic contract language detected.';

  return {
    title: String(title),
    severity,
    explanation: String(explanation).trim(),
    document_name: document?.document_name || document?.name || 'Untitled document',
    page: record?.page ?? record?.page_number ?? record?.pageNumber ?? null,
    clause_id: record?.clause_id ?? record?.clauseId ?? null,
    category: record?.category || record?.risk_type || 'General',
    document_id: document?.id ?? document?.document_id,
    document_type: document?.document_type || document?.type || 'General document',
  };
}

function normalizeRisksForDocument(document, payload) {
  if (!payload) return [];

  if (Array.isArray(payload)) {
    return payload.map((risk) => simplifyRisk(risk, document, normalizeSeverity(risk?.severity, 'low')));
  }

  const high = Array.isArray(payload.high_risks) ? payload.high_risks : [];
  const medium = Array.isArray(payload.medium_risks) ? payload.medium_risks : [];
  const low = Array.isArray(payload.low_risks) ? payload.low_risks : [];

  return [
    ...high.map((risk) => simplifyRisk(risk, document, 'high')),
    ...medium.map((risk) => simplifyRisk(risk, document, 'medium')),
    ...low.map((risk) => simplifyRisk(risk, document, 'low')),
  ];
}

function severityCount(risks) {
  return {
    high: risks.filter((risk) => risk.severity === 'high').length,
    medium: risks.filter((risk) => risk.severity === 'medium').length,
    low: risks.filter((risk) => risk.severity === 'low').length,
  };
}

function filterTabClass(active) {
  return `rounded-full px-3.5 py-1.5 text-xs font-semibold transition-colors ${
    active
      ? 'bg-slate-900 text-white shadow-sm'
      : 'border border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'
  }`;
}

function RiskCard({ risk, onView }) {
  const cfg = SEVERITY_STYLE[risk.severity] ?? SEVERITY_STYLE.low;

  return (
    <article className={`rounded-xl border p-4 sm:p-5 ${cfg.card}`}>
      <div className="flex flex-wrap items-start justify-between gap-2.5">
        <div className="min-w-0 space-y-1.5">
          <h3 className="text-sm font-semibold text-slate-900 sm:text-[15px]">{risk.title}</h3>
          <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-semibold ring-1 ${cfg.badge}`}>
            {cfg.label}
          </span>
        </div>
        <button
          type="button"
          onClick={onView}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
        >
          View in Document
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>

      <p className="mt-3 line-clamp-2 text-sm leading-relaxed text-slate-700">{risk.explanation}</p>

      <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-slate-500">
        <span>
          Document: <span className="font-medium text-slate-700">{risk.document_name}</span>
        </span>
        {risk.page ? (
          <span>
            Page <span className="font-medium text-slate-700">{risk.page}</span>
          </span>
        ) : null}
        {risk.category ? (
          <span>
            Category <span className="font-medium text-slate-700">{risk.category}</span>
          </span>
        ) : null}
      </div>
    </article>
  );
}

export default function RiskAlerts() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [allRisks, setAllRisks] = useState([]);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [documentTypeFilter, setDocumentTypeFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [isLowRiskExpanded, setIsLowRiskExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRisks() {
      setIsLoading(true);
      setError(null);
      try {
        const docs = await listDocuments(user?.id);
        if (cancelled) return;

        const rows = Array.isArray(docs) ? docs : [];
        const analyzedDocs = rows.filter((doc) => {
          const status = String(doc.processing_status ?? doc.status ?? '').toLowerCase();
          return status === 'analyzed' || status === 'processed' || status === 'completed';
        });

        const settled = await Promise.allSettled(
          analyzedDocs.map((doc) => getDocumentRisks(doc.id ?? doc.document_id)),
        );
        if (cancelled) return;

        const merged = [];
        settled.forEach((result, index) => {
          if (result.status !== 'fulfilled') return;
          const normalized = normalizeRisksForDocument(analyzedDocs[index], result.value);
          merged.push(...normalized);
        });

        merged.sort((a, b) => SEVERITY.indexOf(a.severity) - SEVERITY.indexOf(b.severity));
        setAllRisks(merged);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load risk alerts');
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    loadRisks();
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  const summary = useMemo(() => severityCount(allRisks), [allRisks]);

  const documentTypeOptions = useMemo(() => {
    return [...new Set(allRisks.map((risk) => risk.document_type).filter(Boolean))].sort((a, b) =>
      String(a).localeCompare(String(b)),
    );
  }, [allRisks]);

  const categoryOptions = useMemo(() => {
    return [...new Set(allRisks.map((risk) => risk.category).filter(Boolean))].sort((a, b) =>
      String(a).localeCompare(String(b)),
    );
  }, [allRisks]);

  const filtered = useMemo(() => {
    return allRisks.filter((risk) => {
      const bySeverity = severityFilter === 'all' || risk.severity === severityFilter;
      const byDocType = documentTypeFilter === 'all' || risk.document_type === documentTypeFilter;
      const byCategory = categoryFilter === 'all' || risk.category === categoryFilter;
      return bySeverity && byDocType && byCategory;
    });
  }, [allRisks, categoryFilter, documentTypeFilter, severityFilter]);

  const grouped = useMemo(() => {
    return {
      high: filtered.filter((risk) => risk.severity === 'high'),
      medium: filtered.filter((risk) => risk.severity === 'medium'),
      low: filtered.filter((risk) => risk.severity === 'low'),
    };
  }, [filtered]);

  const noRisksAtAll = !isLoading && !error && allRisks.length === 0;
  const noFilterResult = !isLoading && !error && allRisks.length > 0 && filtered.length === 0;

  const openInDocument = (risk) => {
    navigate(`/document/${risk.document_id}`, {
      state: {
        openRiskPanel: true,
        focusRisk: {
          title: risk.title,
          explanation: risk.explanation,
          severity: risk.severity,
          clause_id: risk.clause_id,
          page: risk.page,
          category: risk.category,
        },
      },
    });
  };

  return (
    <div className="relative h-full bg-slate-50">
      <div className="mx-auto h-full max-w-[1600px] px-4 py-6 sm:px-6 lg:px-8">
        <div className="min-h-0 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold text-slate-900 sm:text-3xl">Risk Alerts</h1>
              <p className="mt-1 text-sm text-slate-600">
                Executive AI risk overview across all uploaded legal documents.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {SEVERITY.map((sev) => {
              const cfg = SEVERITY_STYLE[sev];
              return (
                <Card key={sev} className={`border ${cfg.stat}`}>
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide">{cfg.label}</p>
                        <p className="mt-1 text-3xl font-semibold leading-none">{summary[sev]}</p>
                      </div>
                      <CircleAlert className={`h-5 w-5 ${cfg.icon}`} />
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>

          <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3">
            <span className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <Filter className="h-3.5 w-3.5" />
              Filters
            </span>
            <div className="inline-flex flex-wrap items-center gap-2">
              {['all', ...SEVERITY].map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => setSeverityFilter(option)}
                  className={filterTabClass(severityFilter === option)}
                >
                  {option === 'all' ? 'All' : SEVERITY_STYLE[option].label}
                </button>
              ))}
            </div>
            <select
              value={documentTypeFilter}
              onChange={(e) => setDocumentTypeFilter(e.target.value)}
              className="min-w-[190px] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All document types</option>
              {documentTypeOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="min-w-[190px] rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All categories</option>
              {categoryOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </div>

          {isLoading ? (
            <div className="space-y-3">
              <div className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white" />
              <div className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white" />
              <div className="h-32 animate-pulse rounded-xl border border-slate-200 bg-white" />
            </div>
          ) : error ? (
            <Card className="border-red-200 bg-red-50">
              <CardContent className="p-5">
                <p className="text-sm text-red-700">Unable to load risk alerts: {error}</p>
              </CardContent>
            </Card>
          ) : noRisksAtAll ? (
            <Card className="border-emerald-200 bg-emerald-50/40">
              <CardContent className="p-8 text-center">
                <ShieldCheck className="mx-auto h-10 w-10 text-emerald-500" />
                <h2 className="mt-3 text-lg font-semibold text-slate-900">No critical legal risks detected</h2>
                <p className="mx-auto mt-1 max-w-xl text-sm text-slate-600">
                  No critical legal risks detected across uploaded documents.
                </p>
              </CardContent>
            </Card>
          ) : noFilterResult ? (
            <Card>
              <CardContent className="p-8 text-center">
                <FolderOpen className="mx-auto h-10 w-10 text-slate-400" />
                <h2 className="mt-3 text-lg font-semibold text-slate-900">No alerts match current filters</h2>
                <p className="mt-1 text-sm text-slate-600">Adjust severity, document type, or category filters.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-6">
              {SEVERITY.map((sev) =>
                grouped[sev].length ? (
                  <section key={sev} className="space-y-3">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className={`h-4 w-4 ${SEVERITY_STYLE[sev].icon}`} />
                      <h2 className="text-xl font-semibold text-slate-900">{SEVERITY_STYLE[sev].heading}</h2>
                      <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-500 ring-1 ring-slate-200">
                        {grouped[sev].length}
                      </span>
                      {sev === 'low' ? (
                        <button
                          type="button"
                          onClick={() => setIsLowRiskExpanded((open) => !open)}
                          className="ml-2 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
                        >
                          {isLowRiskExpanded ? 'Hide' : 'Show'}
                        </button>
                      ) : null}
                    </div>
                    {sev !== 'low' || isLowRiskExpanded ? (
                      <div className="space-y-3">
                        {grouped[sev].map((risk, idx) => (
                          <RiskCard key={`${risk.document_id}-${risk.clause_id ?? idx}`} risk={risk} onView={() => openInDocument(risk)} />
                        ))}
                      </div>
                    ) : null}
                  </section>
                ) : null,
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
