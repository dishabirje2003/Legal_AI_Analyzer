/**
 * @deprecated ARCHIVED — This component is no longer rendered in the UI.
 *
 * Entity extraction remains active internally for AI reasoning and powers
 * summaries, risk analysis, clause intelligence, and RAG retrieval.
 *
 * This file is retained for future reuse (e.g., admin dashboards, analytics,
 * PDF source grounding, or contract comparison features).
 */

import { useState } from 'react';

/* ─── Confidence Badge ─── */
function ConfidenceBadge({ score }) {
  if (score == null) return null;
  const pct = Math.round(score * 100);
  const color =
    pct >= 90 ? 'bg-emerald-100 text-emerald-700 border-emerald-200'
    : pct >= 75 ? 'bg-amber-100 text-amber-700 border-amber-200'
    : 'bg-red-100 text-red-700 border-red-200';
  return (
    <span className={`ml-1 inline-flex items-center rounded px-1 py-px text-[9px] font-semibold border ${color}`}>
      {pct}%
    </span>
  );
}

/* ─── Expandable Context Preview ─── */
function ContextPreview({ context }) {
  const [open, setOpen] = useState(false);
  if (!context) return null;
  return (
    <div className="mt-1">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="text-[10px] text-slate-400 hover:text-slate-600 underline underline-offset-2 transition-colors"
      >
        {open ? 'Hide context' : 'Show context'}
      </button>
      {open && (
        <p className="mt-1 rounded bg-slate-50 border border-slate-100 px-2 py-1.5 text-[11px] leading-relaxed text-slate-600 italic">
          "{context}"
        </p>
      )}
    </div>
  );
}

/* ─── Enriched Entity Chip (with confidence + context) ─── */
function EnrichedChip({ entity, chipClass }) {
  const text = entity?.text ?? entity;
  const confidence = entity?.confidence;
  const meta = entity?.metadata ?? {};
  const role = meta.role;
  const moneyType = meta.type;
  const context = meta.context;

  return (
    <div className="inline-flex flex-col">
      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs ${chipClass}`}>
        <span>{text}</span>
        {role && <span className="ml-1 opacity-70">({role})</span>}
        {moneyType && moneyType !== 'amount' && <span className="ml-1 opacity-70">• {moneyType}</span>}
        <ConfidenceBadge score={confidence} />
      </span>
      <ContextPreview context={context} />
    </div>
  );
}

/* ─── Entity Group (enriched or simple) ─── */
export function EntityGroup({ title, items, enrichedItems, chipClass }) {
  const useEnriched = enrichedItems?.length > 0;
  const displayItems = useEnriched ? enrichedItems : items;
  if (!displayItems?.length) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">{title}</p>
        <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-1.5 py-0.5 font-medium">
          {displayItems.length}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {displayItems.map((item, i) =>
          useEnriched ? (
            <EnrichedChip key={`${title}-${i}`} entity={item} chipClass={chipClass} />
          ) : (
            <span key={`${title}-${i}`} className={`inline-flex rounded-full px-2.5 py-0.5 text-xs ${chipClass}`}>
              {typeof item === 'object' ? item.text || item.value || JSON.stringify(item) : item}
            </span>
          )
        )}
      </div>
    </div>
  );
}

/* ─── Money Group (by type) ─── */
function MoneyByTypeGroup({ enrichedMoney, simpleMoney, chipClass }) {
  const items = enrichedMoney?.length > 0 ? enrichedMoney : [];

  // Group by type
  const grouped = {};
  for (const m of items) {
    const type = m?.metadata?.type || 'amount';
    if (!grouped[type]) grouped[type] = [];
    grouped[type].push(m);
  }

  const typeLabels = {
    rent: '🏠 Rent', deposit: '🔒 Deposit', penalty: '⚠️ Penalty',
    compensation: '💰 Compensation', premium: '📋 Premium', salary: '💵 Salary',
    tax: '🏛️ Tax', damages: '⚖️ Damages', 'loan amount': '🏦 Loan',
    fee: '💳 Fee', amount: '💲 Amount',
  };

  if (items.length === 0) {
    // Fallback to simple money strings
    if (!simpleMoney?.length) return null;
    return <EntityGroup title="Financial Amounts" items={simpleMoney} chipClass={chipClass} />;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider">Financial Amounts</p>
        <span className="text-[10px] text-slate-400 bg-slate-100 rounded-full px-1.5 py-0.5 font-medium">
          {items.length}
        </span>
      </div>
      <div className="space-y-2">
        {Object.entries(grouped).map(([type, moneyItems]) => (
          <div key={type}>
            <p className="text-[10px] font-semibold text-slate-400 mb-1">{typeLabels[type] || type}</p>
            <div className="flex flex-wrap gap-1.5">
              {moneyItems.map((m, i) => (
                <EnrichedChip key={`money-${type}-${i}`} entity={m} chipClass={chipClass} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Relations Section ─── */
function RelationsSection({ relations }) {
  if (!relations?.length) return null;

  const typeConfig = {
    obligation: { label: 'Obligation', icon: '📋', border: 'border-blue-200', bg: 'bg-blue-50/50' },
    purpose: { label: 'Purpose', icon: '🎯', border: 'border-emerald-200', bg: 'bg-emerald-50/50' },
    risk: { label: 'Risk', icon: '⚠️', border: 'border-red-200', bg: 'bg-red-50/50' },
  };

  return (
    <div>
      <p className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">Entity Relations</p>
      <div className="space-y-1.5">
        {relations.map((rel, i) => {
          const cfg = typeConfig[rel.type] || { label: rel.type, icon: '🔗', border: 'border-slate-200', bg: 'bg-slate-50/50' };
          return (
            <div key={i} className={`rounded-lg border ${cfg.border} ${cfg.bg} px-3 py-2`}>
              <div className="flex items-center gap-1.5 text-xs">
                <span>{cfg.icon}</span>
                <span className="font-medium text-slate-700">{rel.party || rel.amount}</span>
                <span className="text-slate-400">→</span>
                <span className="text-slate-600">{rel.relation}</span>
                <ConfidenceBadge score={rel.confidence} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ─── Main EntitiesTab ─── */
export default function EntitiesTab({ analysis, status, shouldPoll }) {
  const grouped = analysis?.entities?.grouped ?? analysis?.entities ?? {};
  const enriched = grouped.enriched ?? {};
  const relations = grouped.relations ?? [];

  // Backward-compatible simple lists
  const parties = grouped.parties || grouped.party_names || [];
  const money = grouped.money || grouped.amounts || [];
  const dates = grouped.dates?.other_dates || grouped.dates || [];
  const locations = grouped.locations || grouped.jurisdiction || [];
  const legalRefs = grouped.legal_references || [];
  const caseIds = grouped.case_identifiers || [];
  const judges = grouped.judges || [];
  const durations = grouped.durations || [];
  const policyIds = grouped.policy_identifiers || [];

  // Enriched lists
  const eParties = enriched.parties || [];
  const eMoney = enriched.money || [];
  const eDates = enriched.dates || [];
  const eLocations = enriched.locations || [];
  const eLegalRefs = enriched.legal_references || [];
  const eCaseIds = enriched.case_identifiers || [];
  const eJudges = enriched.judges || [];
  const eDurations = enriched.durations || [];
  const ePolicyIds = enriched.policy_identifiers || [];

  const hasEntities =
    parties.length > 0 || money.length > 0 || dates.length > 0 || locations.length > 0 ||
    legalRefs.length > 0 || caseIds.length > 0 || judges.length > 0 || durations.length > 0 || policyIds.length > 0;

  return (
    <div className="space-y-6">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-900 border-b border-slate-100 pb-2">
        <span className="h-2 w-2 rounded-full bg-blue-500 shadow-sm" aria-hidden />
        Extracted Entities
        {hasEntities && (
          <span className="ml-auto text-[10px] font-normal text-slate-400">
            Confidence scores shown per entity
          </span>
        )}
      </h3>
      
      <div className="space-y-5">
        <EntityGroup
          title="Parties & Organizations"
          items={parties}
          enrichedItems={eParties}
          chipClass="bg-blue-50 text-blue-700 border border-blue-200 shadow-sm font-medium"
        />
        <MoneyByTypeGroup
          enrichedMoney={eMoney}
          simpleMoney={money.map(m => typeof m === 'object' ? m.value || m.text : m)}
          chipClass="bg-green-50 text-green-700 border border-green-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Important Dates"
          items={dates}
          enrichedItems={eDates}
          chipClass="bg-purple-50 text-purple-700 border border-purple-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Durations"
          items={durations}
          enrichedItems={eDurations}
          chipClass="bg-indigo-50 text-indigo-700 border border-indigo-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Locations & Jurisdictions"
          items={locations}
          enrichedItems={eLocations}
          chipClass="bg-orange-50 text-orange-700 border border-orange-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Legal References"
          items={legalRefs}
          enrichedItems={eLegalRefs}
          chipClass="bg-rose-50 text-rose-700 border border-rose-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Case Identifiers"
          items={caseIds}
          enrichedItems={eCaseIds}
          chipClass="bg-cyan-50 text-cyan-700 border border-cyan-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Judges"
          items={judges}
          enrichedItems={eJudges}
          chipClass="bg-violet-50 text-violet-700 border border-violet-200 shadow-sm font-medium"
        />
        <EntityGroup
          title="Policy & Claim Identifiers"
          items={policyIds}
          enrichedItems={ePolicyIds}
          chipClass="bg-teal-50 text-teal-700 border border-teal-200 shadow-sm font-medium"
        />

        <RelationsSection relations={relations} />
      </div>

      {!hasEntities ? (
        <div className="rounded-lg border border-slate-200 border-dashed bg-slate-50 p-6 text-center text-sm text-slate-500">
          {shouldPoll || String(status).toLowerCase() === 'extracted' ? 'Analyzing document for entities...' : 'No entities detected in this document.'}
        </div>
      ) : null}
    </div>
  );
}
