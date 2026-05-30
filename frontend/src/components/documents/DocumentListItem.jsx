import { FileText } from 'lucide-react';
import { statusLabel } from '../../utils/status.js';

function statusBadgeClass(status) {
  const s = String(status || '').toLowerCase();
  if (
    s === 'completed' ||
    s === 'analyzed' ||
    s === 'processed' ||
    s === 'processing' ||
    s === 'uploaded' ||
    s === 'extracted'
  ) {
    return 'bg-green-50 text-green-700 border border-green-200';
  }
  if (s === 'failed') return 'bg-red-50 text-red-700 border border-red-200';
  return 'bg-slate-50 text-slate-700 border border-slate-200';
}

/**
 * @param {object} props
 * @param {{ id: string, name: string, type: string, pages: number, status: string }} props.document
 * @param {() => void} props.onOpen
 */
export default function DocumentListItem({ document: doc, onOpen }) {
  return (
    <div className="flex flex-col gap-3 p-4 transition-colors hover:bg-slate-50 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex min-w-0 flex-1 items-center gap-4">
        <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-blue-50">
          <FileText className="h-5 w-5 text-blue-600" />
        </div>
        <div className="min-w-0 flex-1">
          <h4 className="truncate font-medium text-slate-900">{doc.name}</h4>
          <div className="mt-1 flex flex-wrap items-center gap-x-2 text-sm text-slate-500">
            <span>{doc.type}</span>
            {typeof doc.pages === 'number' ? (
              <>
                <span aria-hidden="true">•</span>
                <span>{doc.pages} pages</span>
              </>
            ) : null}
          </div>
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-3 sm:justify-end">
        <span
          className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${statusBadgeClass(doc.status)}`}
        >
          {statusLabel(doc.status)}
        </span>
        <button
          type="button"
          onClick={onOpen}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
        >
          Open
        </button>
      </div>
    </div>
  );
}
