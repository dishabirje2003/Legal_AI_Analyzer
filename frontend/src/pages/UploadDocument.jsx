import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Scan, Upload, CheckCircle, Loader2, Shield, Sparkles, ArrowRight, X, File } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card.jsx';
import UploadBox from '../components/upload/UploadBox.jsx';
import { uploadDocument } from '../lib/api.js';
import { useAuth } from '../contexts/AuthContext.jsx';

const DOC_TYPES = [
  { value: 'contract', label: 'Contracts', icon: '📄' },
  { value: 'court_judgment', label: 'Court Judgment', icon: '⚖️' },
  { value: 'property', label: 'Property', icon: '🏠' },
  { value: 'Insurance/Financial', label: 'Insurance / Financial', icon: '💰' },
  { value: 'general_legal_document', label: 'General Legal Document', icon: '📋' },
];

/* ─── Animated upload pipeline steps ─── */
const UPLOAD_STEPS = [
  { id: 'upload',    label: 'Uploading file',            detail: 'Securely transferring to server…' },
  { id: 'store',     label: 'Storing document',          detail: 'Saving to encrypted cloud storage…' },
  { id: 'extract',   label: 'Extracting text',           detail: 'AI-powered OCR and text extraction…' },
  { id: 'analyze',   label: 'Queueing analysis',         detail: 'Starting NLP summarization pipeline…' },
  { id: 'complete',  label: 'Upload complete',           detail: 'Redirecting to document viewer…' },
];

function StepIndicator({ step, currentIndex }) {
  const stepIndex = UPLOAD_STEPS.findIndex(s => s.id === step.id);
  const isActive  = stepIndex === currentIndex;
  const isDone    = stepIndex < currentIndex;
  const isPending = stepIndex > currentIndex;

  return (
    <div className={`flex items-start gap-3 transition-all duration-500 ${isPending ? 'opacity-40' : 'opacity-100'}`}>
      {/* Icon */}
      <div className="relative flex-shrink-0 mt-0.5">
        {isDone ? (
          <div className="h-7 w-7 rounded-full bg-emerald-500 flex items-center justify-center shadow-md shadow-emerald-500/30 animate-[scaleIn_0.3s_ease]">
            <CheckCircle className="h-4 w-4 text-white" />
          </div>
        ) : isActive ? (
          <div className="h-7 w-7 rounded-full bg-blue-600 flex items-center justify-center shadow-md shadow-blue-500/40">
            <Loader2 className="h-4 w-4 text-white animate-spin" />
          </div>
        ) : (
          <div className="h-7 w-7 rounded-full border-2 border-slate-300 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-slate-300" />
          </div>
        )}
        {/* Connector line */}
        {stepIndex < UPLOAD_STEPS.length - 1 && (
          <div className={`absolute left-1/2 top-7 w-0.5 h-6 -translate-x-1/2 transition-colors duration-500 ${isDone ? 'bg-emerald-400' : 'bg-slate-200'}`} />
        )}
      </div>
      {/* Text */}
      <div className="pb-6">
        <p className={`text-sm font-semibold leading-tight ${isActive ? 'text-blue-700' : isDone ? 'text-emerald-700' : 'text-slate-500'}`}>
          {step.label}
        </p>
        <p className={`text-xs mt-0.5 ${isActive ? 'text-blue-500' : isDone ? 'text-emerald-500' : 'text-slate-400'}`}>
          {step.detail}
        </p>
      </div>
    </div>
  );
}

/* ─── Floating particles background for the uploading state ─── */
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {[...Array(6)].map((_, i) => (
        <div
          key={i}
          className="absolute rounded-full bg-blue-400/10"
          style={{
            width:  `${12 + Math.random() * 20}px`,
            height: `${12 + Math.random() * 20}px`,
            left:   `${Math.random() * 100}%`,
            top:    `${Math.random() * 100}%`,
            animation: `floatUp ${4 + Math.random() * 4}s ease-in-out ${Math.random() * 2}s infinite alternate`,
          }}
        />
      ))}
    </div>
  );
}

export default function UploadDocument() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [documentType, setDocumentType] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [uploadComplete, setUploadComplete] = useState(false);
  const timerRef = useRef(null);

  // Clean up timer on unmount
  useEffect(() => () => { if (timerRef.current) clearInterval(timerRef.current); }, []);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) setSelectedFile(files[0]);
  };

  const handleUpload = async () => {
    if (!selectedFile || !documentType) return;
    setError(null);
    setIsUploading(true);
    setProgress(0);
    setCurrentStep(0);
    setUploadComplete(false);

    try {
      // Step 0 → Uploading file
      const result = await uploadDocument(
        selectedFile,
        documentType,
        selectedFile?.name || 'Document',
        (p) => {
          setProgress(p);
          // Move to "Storing" once file transfer reaches ~80%
          if (p >= 80) setCurrentStep(prev => Math.max(prev, 1));
        },
        user?.id,
      );

      // Step 1 → Stored
      setProgress(100);
      setCurrentStep(2);

      // Simulate extraction + analysis queue (server is doing this in background)
      await new Promise(r => setTimeout(r, 800));
      setCurrentStep(3);
      await new Promise(r => setTimeout(r, 600));
      setCurrentStep(4);
      setUploadComplete(true);

      await new Promise(r => setTimeout(r, 1200));

      const id =
        result &&
        typeof result === 'object' &&
        (result.id ?? result.document_id ?? result.documentId);
      if (id) navigate(`/document/${id}`);
      else navigate('/library');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setIsUploading(false);
      setProgress(0);
      setCurrentStep(0);
    }
  };

  const fileSize = selectedFile ? (selectedFile.size / 1024 / 1024).toFixed(2) : null;

  // ──────────────────────────────────────────────────
  // UPLOADING STATE — full-screen immersive overlay
  // ──────────────────────────────────────────────────
  if (isUploading) {
    return (
      <div className="mx-auto max-w-2xl p-6 lg:p-8">
        <Card className="relative overflow-hidden border-0 shadow-xl shadow-blue-500/5">
          <FloatingParticles />
          <CardContent className="relative z-10 p-8 sm:p-10">
            {/* Header */}
            <div className="text-center mb-8">
              {/* Pulsing file icon */}
              <div className="relative mx-auto mb-5 h-20 w-20">
                <div className={`absolute inset-0 rounded-2xl ${uploadComplete ? 'bg-emerald-500/20' : 'bg-blue-500/20'} animate-ping`}
                     style={{ animationDuration: '2s' }} />
                <div className={`relative h-20 w-20 rounded-2xl ${uploadComplete ? 'bg-gradient-to-br from-emerald-500 to-emerald-600' : 'bg-gradient-to-br from-blue-500 to-blue-600'} flex items-center justify-center shadow-lg transition-colors duration-700`}>
                  {uploadComplete
                    ? <CheckCircle className="h-10 w-10 text-white" />
                    : <File className="h-10 w-10 text-white" />
                  }
                </div>
              </div>

              <h2 className="text-xl font-bold text-slate-900">
                {uploadComplete ? 'Upload Complete!' : 'Processing Your Document'}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {uploadComplete
                  ? 'Redirecting to document viewer…'
                  : selectedFile?.name || 'Document'}
              </p>
            </div>

            {/* Progress bar */}
            <div className="mb-8">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-slate-600">
                  {UPLOAD_STEPS[currentStep]?.label}
                </span>
                <span className="text-xs font-semibold tabular-nums text-blue-600">
                  {progress}%
                </span>
              </div>
              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full transition-all duration-500 ease-out ${uploadComplete ? 'bg-gradient-to-r from-emerald-400 to-emerald-500' : 'bg-gradient-to-r from-blue-400 via-blue-500 to-indigo-500'}`}
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Step indicators */}
            <div className="rounded-xl bg-slate-50/80 border border-slate-100 p-5">
              {UPLOAD_STEPS.map((step) => (
                <StepIndicator key={step.id} step={step} currentIndex={currentStep} />
              ))}
            </div>

            {/* File details chip */}
            <div className="mt-6 flex items-center justify-center gap-2">
              <div className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-1.5 text-xs text-slate-600">
                <FileText className="h-3.5 w-3.5" />
                <span className="font-medium">{selectedFile?.name}</span>
                <span className="text-slate-400">•</span>
                <span>{fileSize} MB</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // ──────────────────────────────────────────────────
  // NORMAL STATE — file selection + doc type
  // ──────────────────────────────────────────────────
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6 lg:p-8">
      <div>
        <h1 className="text-3xl font-semibold text-slate-900">Upload Document</h1>
        <p className="mt-1 text-slate-600">
          Upload a legal document to analyze and extract structured legal summaries.
        </p>
      </div>

      <Card>
        <CardContent className="p-6 sm:p-8">
          <UploadBox
            selectedFile={selectedFile}
            onFileChange={(f) => { setSelectedFile(f); setError(null); }}
            isDragging={isDragging}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 p-6">
          <div>
            <label htmlFor="doc-type" className="text-sm font-medium text-slate-900">
              Select Document Type
            </label>
            <p className="mb-3 text-sm text-slate-600">
              Choose one of the supported legal document categories.
            </p>

            {/* Doc type cards (replaces plain select for premium feel) */}
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {DOC_TYPES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setDocumentType(t.value)}
                  className={`group relative flex items-center gap-3 rounded-xl border-2 px-4 py-3.5 text-left transition-all duration-200 ${
                    documentType === t.value
                      ? 'border-blue-500 bg-blue-50/80 shadow-sm shadow-blue-500/10'
                      : 'border-slate-200 bg-white hover:border-blue-300 hover:bg-slate-50'
                  }`}
                >
                  <span className="text-xl">{t.icon}</span>
                  <span className={`text-sm font-medium ${documentType === t.value ? 'text-blue-700' : 'text-slate-700'}`}>
                    {t.label}
                  </span>
                  {documentType === t.value && (
                    <CheckCircle className="absolute right-3 h-4 w-4 text-blue-500" />
                  )}
                </button>
              ))}
            </div>

            {/* Keep a hidden native select for accessibility / form fallback */}
            <select
              id="doc-type"
              value={documentType}
              onChange={(e) => setDocumentType(e.target.value)}
              className="sr-only"
              aria-label="Document type"
            >
              <option value="">Select document type</option>
              {DOC_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 gap-4 border-t border-slate-100 pt-6 sm:grid-cols-2">
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-100">
                <Shield className="h-4 w-4 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">Secure upload</p>
                <p className="text-xs text-slate-600">
                  Files are encrypted and stored in your private workspace.
                </p>
              </div>
            </div>
            <div className="flex gap-3">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-purple-100">
                <Sparkles className="h-4 w-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium text-slate-900">AI-powered analysis</p>
                <p className="text-xs text-slate-600">Gemini OCR, NER, clause detection, and risk analysis run automatically.</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
        >
          <X className="h-4 w-4 mt-0.5 flex-shrink-0 text-red-500" />
          <div>
            {error}
            <span className="mt-1 block text-xs text-red-600">
              Ensure the FastAPI server is running or check your network connection.
            </span>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!selectedFile || !documentType || isUploading}
          className="group inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 px-8 py-3 text-sm font-semibold text-white shadow-md shadow-blue-500/25 transition-all hover:shadow-lg hover:shadow-blue-500/30 hover:from-blue-700 hover:to-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none"
        >
          <Upload className="h-4 w-4" />
          Upload Document
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
        </button>
        <button
          type="button"
          onClick={() => navigate('/dashboard')}
          disabled={isUploading}
          className="rounded-xl border border-slate-200 bg-white px-8 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
