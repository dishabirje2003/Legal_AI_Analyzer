import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.jsx';
import DocumentListItem from '../components/documents/DocumentListItem.jsx';
import { getDashboardRiskSummary, getQueueStatus, listDocuments } from '../lib/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [queueStatus, setQueueStatus] = useState(null);
  const [riskSummary, setRiskSummary] = useState({
    total_risks: 0,
    high_risk_count: 0,
    medium_risk_count: 0,
    low_risk_count: 0,
  });

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard(withSpinner = false) {
      if (withSpinner) setIsLoading(true);
      setError(null);
      try {
        const [rows, queue, risks] = await Promise.all([
          listDocuments(user?.id),
          getQueueStatus().catch(() => null),
          getDashboardRiskSummary(user?.id).catch(() => ({
            total_risks: 0,
            high_risk_count: 0,
            medium_risk_count: 0,
            low_risk_count: 0,
          })),
        ]);
        if (cancelled) return;
        setDocuments(Array.isArray(rows) ? rows : []);
        setQueueStatus(queue);
        setRiskSummary(risks || {
          total_risks: 0,
          high_risk_count: 0,
          medium_risk_count: 0,
          low_risk_count: 0,
        });
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : 'Failed to load documents');
      } finally {
        if (cancelled || !withSpinner) return;
        setIsLoading(false);
      }
    }

    loadDashboard(true);
    const intervalId = window.setInterval(() => {
      loadDashboard(false);
    }, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [user?.id]);

  const recentDocuments = useMemo(() => documents.slice(0, 5), [documents]);

  const totalDocuments = documents.length;
  const analyzedDocuments = documents.filter((doc) => {
    const s = String(doc.processing_status ?? doc.status ?? '').toLowerCase();
    return s === 'analyzed' || s === 'processed' || s === 'completed';
  }).length;
  const totalRisks = Number(riskSummary?.total_risks || 0);

  const stats = [
    {
      title: 'Total Documents',
      value: String(totalDocuments),
      icon: FileText,
      color: 'bg-blue-500',
    },
    {
      title: 'Documents Analyzed',
      value: String(analyzedDocuments),
      icon: CheckCircle,
      color: 'bg-green-500',
    },
    {
      title: 'Total Risks Detected',
      value: String(totalRisks),
      icon: AlertTriangle,
      color: 'bg-red-500',
    },
  ];

  return (
    <div className="space-y-8 p-6 lg:p-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-1 text-slate-600">
          Welcome back! Here&apos;s an overview of your legal documents.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {stats.map((stat) => (
          <Card
            key={stat.title}
            className="transition-shadow hover:shadow-md"
          >
            <CardContent className="p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-slate-600">{stat.title}</p>
                  <p className="mt-2 text-3xl font-semibold text-slate-900">{stat.value}</p>
                  {stat.title === 'Total Risks Detected' ? (
                    totalRisks > 0 ? (
                      <p className="mt-2 text-[11px] text-slate-500">
                        H: {riskSummary.high_risk_count} · M: {riskSummary.medium_risk_count} · L: {riskSummary.low_risk_count}
                      </p>
                    ) : (
                      <p className="mt-2 text-[11px] text-slate-500">No analyzed risks yet</p>
                    )
                  ) : null}
                </div>
                <div
                  className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-lg ${stat.color}`}
                >
                  <stat.icon className="h-6 w-6 text-white" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent Documents</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="divide-y divide-slate-100">
            {isLoading ? (
              <div className="p-6 text-sm text-slate-600">Loading…</div>
            ) : error ? (
              <div className="p-6 text-sm text-red-700">Failed to load: {error}</div>
            ) : recentDocuments.length === 0 ? (
              <div className="p-6 text-sm text-slate-600">
                No uploaded documents yet.{' '}
                <button
                  type="button"
                  onClick={() => navigate('/upload')}
                  className="font-medium text-blue-700 hover:underline"
                >
                  Upload your first document
                </button>
                .
              </div>
            ) : (
              recentDocuments.map((doc) => (
                <DocumentListItem
                  key={doc.id ?? doc.document_id}
                  document={{
                    id: doc.id ?? doc.document_id,
                    name: doc.document_name ?? doc.name,
                    type: doc.document_type ?? doc.type,
                    status: doc.processing_status ?? doc.status,
                  }}
                  onOpen={() => navigate(`/document/${doc.id ?? doc.document_id}`)}
                />
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
