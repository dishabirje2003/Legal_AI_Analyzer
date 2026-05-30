import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  ChevronLeft,
  ChevronRight,
  Download,
  FileText,
  PanelRight,
  Share2,
  Sparkles,
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card.jsx';
import { getDocument, getDocumentAnalysis, getDocumentClauses, getDocumentRisks, getDocumentSections, triggerCustomSummary } from '../lib/api.js';
import ClausesTab from '../components/documents/ClausesTab.jsx';
import TopInsightsTab from '../components/documents/TopInsightsTab.jsx';
import RisksTab from '../components/documents/RisksTab.jsx';
import QATab from '../components/documents/QATab.jsx';

/* ─── Tab helpers ──────────────────────────────── */
function summaryTabCls(active) {
  return `rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
    active ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600 hover:text-slate-900'
  }`;
}
function sideTabCls(active) {
  return `flex-1 py-2 text-[11px] font-bold uppercase tracking-widest transition-all border-b-2 ${
    active
      ? 'border-slate-900 text-slate-900'
      : 'border-transparent text-slate-400 hover:text-slate-700'
  }`;
}

/* ─── Resizable Sidebar ─────────────────────────── */
const SIDEBAR_MIN = 320;
const SIDEBAR_MAX = 680;
const SIDEBAR_DEFAULT = 420;

function AIInsightSidebar({ isOpen, onToggle, children }) {
  const [width, setWidth] = useState(SIDEBAR_DEFAULT);
  const dragging = useRef(false);
  const startX   = useRef(0);
  const startW   = useRef(0);

  useEffect(() => {
    function onMove(e) {
      if (!dragging.current) return;
      const dx  = startX.current - (e.clientX ?? e.touches?.[0]?.clientX ?? startX.current);
      const nw  = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, startW.current + dx));
      setWidth(nw);
    }
    function onUp() { dragging.current = false; document.body.style.cursor = ''; document.body.style.userSelect = ''; }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup',   onUp);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend',  onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup',   onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend',  onUp);
    };
  }, []);

  function startDrag(e) {
    dragging.current = true;
    startX.current   = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
    startW.current   = width;
    document.body.style.cursor     = 'col-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }

  return (
    <>
      {/* Sidebar panel */}
      <aside
        className="fixed top-0 right-0 h-full z-20 flex flex-col bg-white border-l border-slate-200 shadow-[-4px_0_24px_-8px_rgba(0,0,0,0.08)] transition-transform duration-300 ease-in-out"
        style={{
          width,
          transform: isOpen ? 'translateX(0)' : `translateX(100%)`,
        }}
      >
        {/* Drag handle */}
        <div
          onMouseDown={startDrag}
          onTouchStart={startDrag}
          className="absolute left-0 top-0 h-full w-1 cursor-col-resize hover:bg-blue-200 transition-colors z-10 group"
        >
          <div className="absolute left-0 top-1/2 -translate-y-1/2 h-12 w-1 rounded-full bg-slate-200 group-hover:bg-blue-400 transition-colors" />
        </div>

        {/* Scrollable content */}
        <div className="flex flex-col h-full overflow-hidden">
          {children}
        </div>
      </aside>

      {/* Spacer so main content doesn't hide behind sidebar */}
      <div
        className="shrink-0 transition-all duration-300"
        style={{ width: isOpen ? width : 0 }}
      />
    </>
  );
}

/* ─── Main Page ─────────────────────────────────── */
export default function DocumentViewer() {
  const { id }     = useParams();
  const navigate   = useNavigate();
  const location   = useLocation();

  const [doc,       setDoc]       = useState(null);
  const [analysis,  setAnalysis]  = useState(null);
  const [clauses,   setClauses]   = useState(null);
  const [risksData, setRisksData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error,     setError]     = useState(null);

  const [summaryTab,  setSummaryTab]  = useState('extractive');
  const [insightTab,  setInsightTab]  = useState('insights');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [copied,      setCopied]      = useState(false);
  
  const [sections, setSections] = useState([]);
  const [checklistMode, setChecklistMode] = useState('ai_decide');
  const [selectedSections, setSelectedSections] = useState([]);
  const [summaryUpdating, setSummaryUpdating] = useState(false);

  /* ── Data loading ──────────────────────────────── */
  const loadAll = useCallback(async () => {
    if (!id) return;
    const [docRes, analysisRes, clausesRes, risksRes, sectionsRes] = await Promise.allSettled([
      getDocument(id),
      getDocumentAnalysis(id),
      getDocumentClauses(id),
      getDocumentRisks(id),
      getDocumentSections(id),
    ]);

    if (docRes.status === 'fulfilled') setDoc(docRes.value ?? null);
    else throw docRes.reason;

    if (analysisRes.status === 'fulfilled') setAnalysis(analysisRes.value ?? null);
    else setAnalysis(null);

    if (clausesRes.status === 'fulfilled') {
      const data = clausesRes.value ?? {};
      setClauses(Array.isArray(data) ? { clauses: data, insight_groups: [] } : data);
    }
    if (risksRes.status === 'fulfilled') setRisksData(risksRes.value ?? null);
    
    if (sectionsRes.status === 'fulfilled') {
      const s = sectionsRes.value?.sections || [];
      setSections(s);
    }
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    if (!id) return;
    setIsLoading(true);
    setError(null);
    loadAll()
      .catch(e => { if (!cancelled) setError(e instanceof Error ? e.message : 'Failed to load document'); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [id, loadAll]);

  const status     = doc?.processing_status ?? doc?.status;
  const shouldPoll = status && !['analyzed', 'failed'].includes(String(status).toLowerCase());

  useEffect(() => {
    if (!id || !shouldPoll) return;
    const t = setInterval(() => loadAll().catch(() => {}), 8000);
    return () => clearInterval(t);
  }, [id, shouldPoll, loadAll]);

  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(false), 1400);
    return () => clearTimeout(t);
  }, [copied]);

  useEffect(() => {
    if (location.state?.openRiskPanel) {
      setSidebarOpen(true);
      setInsightTab('risk');
    }
  }, [location.state]);

  const title    = doc?.document_name ?? doc?.name ?? 'Document';
  const typeLabel = doc?.document_type ?? doc?.type ?? 'Legal document';
  const fileUrl  = doc?.file_url || '';

  // Show the section checklist ONLY for Loan Agreement documents
  const detectedSubtype = (analysis?.detected_contract_subtype || analysis?.entities?.detected_contract_subtype || '').toLowerCase();
  const isLoanAgreement = detectedSubtype === 'loan_agreement'
    || (title && title.toLowerCase().includes('loan agreement'));
  const showChecklist = isLoanAgreement && sections.length > 0;

  const bullets = useMemo(() => {
    const b = analysis?.extractive_bullets;
    if (Array.isArray(b) && b.length > 0) return b;
    return (analysis?.extractive_summary || '')
      .split(/(?<=[.!?])\s+/)
      .map(s => s.trim())
      .filter(Boolean)
      .slice(0, 8);
  }, [analysis]);

  const simplifiedSections = useMemo(() => {
    const structured = analysis?.entities?.structured_summary;
    if (!structured || typeof structured !== 'object') return [];

    const prettyTitle = (key) =>
      String(key || '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())
        .trim();

    const sectionMeta = {
      executive_summary: { title: 'Executive Summary', tone: 'blue' },
      parties: { title: 'Parties', tone: 'indigo' },
      key_terms: { title: 'Key Terms', tone: 'violet' },
      financials: { title: 'Financial Obligations', tone: 'emerald' },
      obligations: { title: 'Rights & Obligations', tone: 'amber' },
      risks: { title: 'Risks & Red Flags', tone: 'red' },
      termination: { title: 'Termination Conditions', tone: 'orange' },
    };
    const preferredOrder = ['executive_summary', 'parties', 'key_terms', 'financials', 'obligations', 'risks', 'termination'];

    const items = Object.entries(structured)
      .filter(([key]) => key !== 'top_insights')
      .map(([key, value]) => {
        const text = Array.isArray(value) ? value.join('\n') : String(value ?? '').trim();
        if (!text) return null;
        const meta = sectionMeta[key] || { title: prettyTitle(key), tone: 'slate' };
        return { key, title: meta.title, tone: meta.tone, text };
      })
      .filter(Boolean);

    return items;
  }, [analysis]);

  const renderInlineBold = useCallback((text) => {
    const value = String(text ?? '');
    const parts = value.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
    return parts.map((part, idx) => {
      const match = part.match(/^\*\*([^*]+)\*\*$/);
      if (match) {
        return (
          <strong key={idx} className="font-semibold text-slate-900">
            {match[1]}
          </strong>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  }, []);

  /* ─── Render ─────────────────────────────────── */
  return (
    <div className="flex h-full min-h-screen bg-slate-50">

      {/* ── Main scrollable column ─────────────── */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        <div className="space-y-4 p-3 lg:p-5">

          {/* Top bar */}
          <div className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 shadow-sm sm:px-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => navigate('/library')}
                  className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-xs font-medium text-slate-600 hover:bg-slate-100"
                >
                  <ChevronLeft className="h-3.5 w-3.5" /> Back
                </button>
                <div className="h-5 w-px bg-slate-200" />
                <FileText className="h-4 w-4 shrink-0 text-blue-600" />
                <div className="min-w-0">
                  <h1 className="truncate text-sm font-semibold text-slate-900 sm:text-base">{title}</h1>
                  <p className="text-[11px] text-slate-500 sm:text-xs">
                    {typeLabel}
                    {status ? <span className="text-slate-400"> • {String(status)}</span> : null}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={!doc?.file_url}
                  onClick={async () => {
                    if (!doc?.file_url) return;
                    try { await navigator.clipboard.writeText(doc.file_url); setCopied(true); }
                    catch { window.open(doc.file_url, '_blank'); }
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                >
                  <Share2 className="h-3.5 w-3.5" />
                  {copied ? 'Copied' : 'Share'}
                </button>
                <a
                  href={doc?.file_url || '#'}
                  download
                  className={`inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium ${
                    doc?.file_url ? 'text-slate-700 hover:bg-slate-50' : 'pointer-events-none text-slate-400'
                  }`}
                >
                  <Download className="h-3.5 w-3.5" /> Download
                </a>
                <button
                  type="button"
                  onClick={() => setSidebarOpen(o => !o)}
                  title="Toggle AI panel"
                  className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
                >
                  <PanelRight className="h-3.5 w-3.5" />
                  AI Panel
                </button>
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              Failed to load document: {error}
            </div>
          )}
          
          {/* Loan Agreement Checklist */}
          {showChecklist && (
            <Card className="border-blue-200 bg-blue-50/50">
              <CardContent className="p-5 sm:p-6">
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-slate-900">Loan Agreement Section Checklist</h3>
                  <span className="text-xs font-medium text-blue-600">Optional Filter</span>
                </div>
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center gap-4">
                    <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                      <input
                        type="radio"
                        checked={checklistMode === 'ai_decide'}
                        onChange={() => {
                          setChecklistMode('ai_decide');
                          setSelectedSections([]);
                        }}
                        className="text-blue-600 focus:ring-blue-500"
                      />
                      Let AI Decide (default)
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
                      <input type="radio" checked={checklistMode === 'selected'} onChange={() => setChecklistMode('selected')} className="text-blue-600 focus:ring-blue-500" />
                      Select Specific Sections
                    </label>
                  </div>
                  
                  {checklistMode === 'selected' && (
                    <div className="rounded-lg border border-slate-200 bg-white p-4">
                      <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-2">
                        <span className="text-xs font-medium text-slate-500">{sections.length} sections found</span>
                        <button onClick={() => setSelectedSections(sections)} className="text-xs font-medium text-blue-600 hover:text-blue-700">Select All</button>
                      </div>
                      <div className="grid max-h-48 grid-cols-1 gap-2 overflow-y-auto sm:grid-cols-2">
                        {sections.map(s => (
                          <label key={s} className="flex items-start gap-2 text-sm text-slate-700 cursor-pointer">
                            <input type="checkbox" className="mt-0.5 rounded text-blue-600 focus:ring-blue-500" checked={selectedSections.includes(s)} onChange={(e) => {
                              if (e.target.checked) setSelectedSections([...selectedSections, s]);
                              else setSelectedSections(selectedSections.filter(x => x !== s));
                            }} />
                            <span className="line-clamp-2 leading-snug">{s}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  <div className="pt-2">
                    <button 
                      disabled={summaryUpdating}
                      onClick={async () => {
                        // Immediately show loading state BEFORE the API call
                        setSummaryUpdating(true);
                        setDoc(prev => prev ? { ...prev, processing_status: 'processing' } : prev);
                        
                        try {
                          const payloadSections = checklistMode === 'selected' ? selectedSections : [];
                          await triggerCustomSummary(id, checklistMode, payloadSections);
                          
                          // Start aggressive polling every 3 seconds until status is 'analyzed'
                          const pollInterval = setInterval(async () => {
                            try {
                              const freshDoc = await getDocument(id);
                              const freshStatus = freshDoc?.processing_status || freshDoc?.status || '';
                              if (['analyzed', 'failed'].includes(String(freshStatus).toLowerCase())) {
                                clearInterval(pollInterval);
                                await loadAll();
                                setSummaryUpdating(false);
                                setDoc(prev => prev ? { ...prev, processing_status: 'analyzed' } : prev);
                              }
                            } catch {
                              // Keep polling on transient errors
                            }
                          }, 3000);
                          
                          // Safety timeout: stop polling after 2 minutes
                          setTimeout(() => {
                            clearInterval(pollInterval);
                            setSummaryUpdating(false);
                            loadAll();
                          }, 120000);
                        } catch (e) {
                          setSummaryUpdating(false);
                          setDoc(prev => prev ? { ...prev, processing_status: 'analyzed' } : prev);
                          alert("Failed to start resummarization");
                        }
                      }}
                      className={`rounded-lg px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-all ${
                        summaryUpdating 
                          ? 'bg-blue-400 cursor-wait animate-pulse' 
                          : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'
                      }`}
                    >
                      {summaryUpdating ? (
                        <span className="inline-flex items-center gap-2">
                          <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                          </svg>
                          Updating Summary…
                        </span>
                      ) : 'Update Summary'}
                    </button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Summary card */}
          <Card>
            <CardContent className="p-5 sm:p-6">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Sparkles className="h-4 w-4 text-blue-600" />
                AI Generated Summary
              </div>
              <div className="inline-flex rounded-md bg-slate-100 p-1 mb-4">
                <button type="button" className={summaryTabCls(summaryTab === 'extractive')} onClick={() => setSummaryTab('extractive')}>
                  Extractive Summary
                </button>
                <button type="button" className={summaryTabCls(summaryTab === 'simplified')} onClick={() => setSummaryTab('simplified')}>
                  Simplified Summary
                </button>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-4">
                {summaryTab === 'extractive' ? (
                  bullets.length ? (
                    <ul className="list-disc space-y-1 pl-5">
                      {bullets.map((line, i) => <li key={i} className="text-justify text-sm leading-relaxed text-slate-700">{line}</li>)}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">
                      {shouldPoll ? 'Generating summary…' : 'No summary yet.'}
                    </p>
                  )
                ) : (() => {
                  if (simplifiedSections.length > 0) {
                    const toneClassMap = {
                      blue: { card: 'border-blue-200 bg-blue-50/30', title: 'text-blue-700' },
                      indigo: { card: 'border-indigo-200 bg-indigo-50/30', title: 'text-indigo-700' },
                      violet: { card: 'border-violet-200 bg-violet-50/30', title: 'text-violet-700' },
                      emerald: { card: 'border-emerald-200 bg-emerald-50/30', title: 'text-emerald-700' },
                      amber: { card: 'border-amber-200 bg-amber-50/30', title: 'text-amber-700' },
                      red: { card: 'border-red-200 bg-red-50/30', title: 'text-red-700' },
                      orange: { card: 'border-orange-200 bg-orange-50/30', title: 'text-orange-700' },
                      slate: { card: 'border-slate-200 bg-slate-50/40', title: 'text-slate-700' },
                    };
                    return (
                      <div className="space-y-3">
                        {simplifiedSections.map((section) => {
                          const tone = toneClassMap[section.tone] || toneClassMap.slate;
                          return (
                            <div key={section.key} className={`rounded-lg border p-3 ${tone.card}`}>
                              <h4 className={`mb-1.5 text-xs font-bold uppercase tracking-wider ${tone.title}`}>{section.title}</h4>
                              {(() => {
                                const lines = section.text
                                  .split('\n')
                                  .map((line) => line.trim())
                                  .filter(Boolean);
                                const looksLikeBullets = lines.length > 1 || lines.some((line) => line.startsWith('- ') || line.startsWith('* '));
                                if (looksLikeBullets) {
                                  return (
                                    <ul className="list-disc space-y-1 pl-5">
                                      {lines.map((line, idx) => {
                                        const cleaned = line.replace(/^[-*]\s+/, '');
                                        const headingMatch = cleaned.match(/^\*\*([^*]+)\*\*[:\-]?\s*$/);
                                        if (headingMatch) {
                                          return (
                                            <li key={idx} className="list-none pt-1 text-sm font-semibold text-slate-900">
                                              {headingMatch[1]}
                                            </li>
                                          );
                                        }
                                        return (
                                            <li key={idx} className="text-justify text-sm leading-relaxed text-slate-700">
                                            {renderInlineBold(cleaned)}
                                          </li>
                                        );
                                      })}
                                    </ul>
                                  );
                                }
                                const headingMatch = section.text.trim().match(/^\*\*([^*]+)\*\*[:\-]?\s*$/);
                                if (headingMatch) {
                                  return <p className="text-sm font-semibold text-slate-900">{headingMatch[1]}</p>;
                                }
                                return (
                                  <p className="whitespace-pre-wrap text-justify text-sm leading-relaxed text-slate-700">
                                    {renderInlineBold(section.text)}
                                  </p>
                                );
                              })()}
                            </div>
                          );
                        })}
                      </div>
                    );
                  }
                  return (
                    <p className="whitespace-pre-wrap text-justify text-sm leading-relaxed text-slate-700">
                      {analysis?.abstractive_summary || (shouldPoll ? 'Generating simplified summary…' : 'No abstractive summary yet.')}
                    </p>
                  );
                })()}
              </div>
            </CardContent>
          </Card>

          {/* Document preview card */}
          <Card className="overflow-hidden h-fit">
            <div className="border-b border-slate-200 px-4 py-3">
              <p className="text-sm font-semibold text-slate-900">Source Document</p>
            </div>
            <div className="p-4">
              <button
                type="button"
                disabled={!fileUrl}
                onClick={() => fileUrl && window.open(fileUrl, '_blank', 'noopener,noreferrer')}
                className="flex h-40 w-full flex-col items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 text-center transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <FileText className="h-8 w-8 text-slate-300" />
                <p className="text-sm font-medium text-slate-700">{fileUrl ? 'Open Document' : 'No document file available'}</p>
                <p className="text-xs text-slate-400">Opens in browser · supports download</p>
              </button>
            </div>
          </Card>

        </div>
      </div>

      {/* ── AI Insight Sidebar ─────────────────── */}
      <AIInsightSidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(o => !o)}>

        {/* Sidebar header */}
        <div className="border-b border-slate-100 px-5 pt-5 pb-0 shrink-0">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-6 w-6 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center">
              <Sparkles className="w-3.5 h-3.5 text-white" />
            </div>
            <h2 className="text-sm font-bold text-slate-900">AI Legal Advisor</h2>
          </div>

          {/* Tab bar */}
          <div className="flex">
            {[
              { key: 'insights',  label: 'Top Insights' },
              { key: 'risk',      label: 'Risk Score'   },
              { key: 'ask',       label: 'Ask AI'       },
            ].map(tab => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setInsightTab(tab.key)}
                className={sideTabCls(insightTab === tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab content — scrollable */}
        <div className="flex-1 overflow-y-auto px-4 py-5">
          {insightTab === 'insights' && <TopInsightsTab topInsights={analysis?.entities?.top_insights || analysis?.entities?.structured_summary?.top_insights} isLoading={isLoading} />}
          {insightTab === 'risk' && <RisksTab risksData={risksData} isLoading={isLoading} focusedRisk={location.state?.focusRisk} />}
          {insightTab === 'ask' && <QATab documentId={id} />}
        </div>

      </AIInsightSidebar>

    </div>
  );
}
