import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Loader2, Search, Trash2, Filter } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card.jsx';
import { statusLabel } from '../utils/status.js';
import { deleteDocument, listDocuments } from '../lib/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';

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
    return 'bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20';
  }
  if (s === 'failed') return 'bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20';
  return 'bg-slate-50 text-slate-700 ring-1 ring-inset ring-slate-600/20';
}

export default function DocumentLibrary() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);

  const docId = (doc) => doc.id ?? doc.document_id;

  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const q = searchQuery.trim().toLowerCase();
      const name = (doc.document_name ?? doc.name ?? '').toLowerCase();
      const matchesSearch = !q || name.includes(q);
      const matchesFilter =
        filter === 'all' ||
        (doc.document_type ?? doc.type ?? '').toLowerCase().includes(filter.replace('-', ' '));
      return matchesSearch && matchesFilter;
    });
  }, [documents, filter, searchQuery]);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    listDocuments(user?.id)
      .then((rows) => {
        if (cancelled) return;
        setDocuments(Array.isArray(rows) ? rows : []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load documents');
      })
      .finally(() => {
        if (cancelled) return;
        setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [user?.id]);

  useEffect(() => {
    if (!confirmDelete) return;
    const onKey = (e) => {
      if (e.key === 'Escape' && !deletingId) setConfirmDelete(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [confirmDelete, deletingId]);

  const handleConfirmDelete = async () => {
    if (!confirmDelete) return;
    const id = docId(confirmDelete);
    setDeleteError(null);
    setDeletingId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => docId(d) !== id));
      setConfirmDelete(null);
    } catch (e) {
      setDeleteError(e instanceof Error ? e.message : 'Could not delete document');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="relative space-y-6 p-6 lg:p-8">
      {confirmDelete ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4 backdrop-blur-[2px]"
          role="presentation"
          onClick={() => !deletingId && setConfirmDelete(null)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-doc-title"
            className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-900/10"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="delete-doc-title" className="text-lg font-semibold text-slate-900">
              Delete document?
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">
              <span className="font-medium text-slate-800">
                {confirmDelete.document_name ?? confirmDelete.name}
              </span>{' '}
              will be removed from the library along with extracted text, analysis, embeddings, and the stored file.
              This cannot be undone.
            </p>
            {deleteError ? (
              <p className="mt-3 text-sm text-red-600" role="alert">
                {deleteError}
              </p>
            ) : null}
            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <button
                type="button"
                disabled={!!deletingId}
                onClick={() => setConfirmDelete(null)}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!!deletingId}
                onClick={() => handleConfirmDelete()}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-red-700 disabled:opacity-60"
              >
                {deletingId ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                    Deleting…
                  </>
                ) : (
                  'Delete permanently'
                )}
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <div>
        <div>
          <h1 className="text-3xl font-semibold text-slate-900">Document Library</h1>
          <p className="mt-1 text-slate-600">
            Browse uploaded documents and open them in the viewer.
          </p>
        </div>
      </div>

      <Card>
        <CardContent className="p-4 sm:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center">
            <div className="relative min-w-0 flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                type="search"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="w-full rounded-lg border border-slate-200 bg-white py-2 pl-10 pr-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              />
            </div>
            <div className="flex items-center gap-2 md:w-72">
              <Filter className="hidden h-4 w-4 shrink-0 text-slate-500 sm:block" aria-hidden />
              <select
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="all">All document types</option>
                <option value="property">Property</option>
                <option value="employment">Employment</option>
                <option value="rental">Rental</option>
                <option value="court">Court</option>
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-100 text-left text-sm">
            <thead className="bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-4 py-3 sm:px-6">
                  Document
                </th>
                <th scope="col" className="px-4 py-3 sm:px-6">
                  Type
                </th>
                <th scope="col" className="hidden px-4 py-3 sm:table-cell sm:px-6">
                  Upload date
                </th>
                <th scope="col" className="px-4 py-3 sm:px-6">
                  Status
                </th>
                <th scope="col" className="px-4 py-3 text-right sm:px-6">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {filteredDocuments.map((doc) => (
                <tr key={docId(doc)} className="transition-colors hover:bg-slate-50/50">
                  <td className="px-4 py-4 sm:px-6">
                    <div className="flex items-center gap-3">
                      <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
                        <FileText className="h-4 w-4 text-blue-600" />
                      </span>
                      <span className="font-medium text-slate-900">
                        {doc.document_name ?? doc.name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-4 text-slate-600 sm:px-6">
                    {doc.document_type ?? doc.type}
                  </td>
                  <td className="hidden px-4 py-4 text-slate-600 sm:table-cell sm:px-6">
                    {new Date(doc.upload_date ?? doc.uploadDate ?? Date.now()).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </td>
                  <td className="px-4 py-4 sm:px-6">
                    <span
                      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusBadgeClass(doc.processing_status ?? doc.status)}`}
                    >
                      {statusLabel(doc.processing_status ?? doc.status)}
                    </span>
                  </td>
                  <td className="px-4 py-4 text-right sm:px-6">
                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => navigate(`/document/${docId(doc)}`)}
                        className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-blue-700 sm:text-sm"
                      >
                        Open
                      </button>
                      <button
                        type="button"
                        title="Delete document"
                        aria-label={`Delete ${doc.document_name ?? doc.name ?? 'document'}`}
                        disabled={deletingId === docId(doc)}
                        onClick={() => {
                          setDeleteError(null);
                          setConfirmDelete(doc);
                        }}
                        className="inline-flex items-center justify-center rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-40 sm:px-2.5"
                      >
                        {deletingId === docId(doc) ? (
                          <Loader2 className="h-4 w-4 animate-spin" aria-label="Deleting" />
                        ) : (
                          <Trash2 className="h-4 w-4" aria-hidden />
                        )}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {isLoading && (
          <div className="px-6 py-10 text-sm text-slate-600">Loading documents…</div>
        )}

        {error && (
          <div className="px-6 py-10 text-sm text-red-700">
            Failed to load documents: {error}
          </div>
        )}

        {!isLoading && !error && filteredDocuments.length === 0 && (
          <div className="flex flex-col items-center px-6 py-16 text-center">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
              <FileText className="h-8 w-8 text-slate-400" />
            </div>
            <h3 className="text-lg font-medium text-slate-900">No documents match</h3>
            <p className="mt-1 max-w-md text-slate-600">Try another search or reset filters.</p>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                setFilter('all');
              }}
              className="mt-6 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Clear filters
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
