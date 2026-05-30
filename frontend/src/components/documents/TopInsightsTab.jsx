import { Sparkles, FileText, Scale } from 'lucide-react';

export default function TopInsightsTab({ topInsights, isLoading }) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="rounded-2xl border border-slate-100 bg-white p-6 animate-pulse">
            <div className="h-4 w-1/3 bg-slate-100 rounded mb-4" />
            <div className="h-3 w-full bg-slate-50 rounded mb-2" />
            <div className="h-3 w-5/6 bg-slate-50 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (!topInsights || topInsights.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 py-16 text-center">
        <Scale className="w-8 h-8 text-slate-200 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-400 uppercase tracking-widest">
          No Insights Generated
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Top insights will appear once the AI completes the analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {topInsights.map((insight, idx) => (
        <article key={idx} className="rounded-2xl border border-blue-100 bg-blue-50/30 p-6 transition-shadow hover:shadow-sm">
          <div className="flex items-start gap-3 mb-3">
            <div className="mt-0.5 p-1.5 rounded-lg bg-blue-100/50">
              <Sparkles className="w-4 h-4 text-blue-600" />
            </div>
            <div>
              <h3 className="text-[15px] font-bold text-slate-900 leading-snug">
                {insight.title}
              </h3>
            </div>
          </div>
          
          <p className="text-[14px] leading-relaxed text-slate-700 mb-4 pl-10">
            {insight.description}
          </p>

          {insight.supporting_text && (
            <div className="ml-10 rounded-xl bg-white/60 border border-slate-200/60 p-4">
              <div className="flex items-center gap-1.5 mb-2">
                <FileText className="w-3 h-3 text-slate-400" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  Supporting Text
                </span>
              </div>
              <p className="text-[12px] leading-relaxed font-mono text-slate-500 whitespace-pre-wrap">
                "{insight.supporting_text}"
              </p>
            </div>
          )}
        </article>
      ))}
    </div>
  );
}
