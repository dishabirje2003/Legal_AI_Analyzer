/** @param {string} status */
export function statusLabel(status) {
  if (!status) return '—';
  const s = String(status).toLowerCase();
  if (s === 'completed' || s === 'analyzed') return 'Completed';
  if (s === 'processing' || s === 'uploaded' || s === 'extracted') return 'Processed';
  if (s === 'processed') return 'Processed';
  if (s === 'failed') return 'Failed';
  return status;
}

/** @param {string} status */
export function statusBadgeTone(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'analyzed' || s === 'completed' || s === 'processed') return 'success';
  if (s === 'failed') return 'danger';
  if (s === 'extracted') return 'info';
  return 'pending';
}
