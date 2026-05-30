import { Upload as UploadIcon, CheckCircle } from 'lucide-react';

export default function UploadBox({
  selectedFile,
  onFileChange,
  isDragging,
  onDragOver,
  onDragLeave,
  onDrop,
  inputId = 'file-upload',
}) {
  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`rounded-xl border-2 border-dashed p-10 text-center transition-all sm:p-12 ${
        isDragging
          ? 'border-blue-500 bg-blue-50'
          : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50'
      }`}
    >
      <input
        id={inputId}
        type="file"
        className="sr-only"
        accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        onChange={(e) => {
          const f = e.target.files?.[0];
          onFileChange(f ?? null);
        }}
      />

      {!selectedFile ? (
        <>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
            <UploadIcon className="h-8 w-8 text-blue-600" />
          </div>
          <h3 className="mb-2 text-lg font-medium text-slate-900">Drop your document here</h3>
          <p className="mb-4 text-slate-600">or</p>
          <button
            type="button"
            onClick={() => document.getElementById(inputId)?.click()}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-700"
          >
            Browse Files
          </button>
          <p className="mt-4 text-sm text-slate-500">
            Supported formats: PDF, DOCX
          </p>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
            <CheckCircle className="h-6 w-6 text-green-600" />
          </div>
          <div className="text-center sm:text-left">
            <p className="font-medium text-slate-900">{selectedFile.name}</p>
            <p className="text-sm text-slate-600">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
          </div>
          <button
            type="button"
            onClick={() => onFileChange(null)}
            className="rounded-lg px-3 py-1.5 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}
