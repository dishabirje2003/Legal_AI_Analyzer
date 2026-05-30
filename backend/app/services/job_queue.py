from __future__ import annotations  
  
import json  
import logging  
import sqlite3  
from datetime import datetime, timedelta, timezone  
from pathlib import Path  
  
logger = logging.getLogger(__name__)  
  
_QUEUE_DB_PATH = Path(__file__).resolve().parents[2] / 'tmp' / 'job_queue.sqlite3'  
_RETRY_DELAY_SECONDS = 30  
_MAX_ATTEMPTS = 3  
  
def _utcnow():  
    return datetime.now(timezone.utc)  
  
class JobQueue:  
    def __init__(self, db_path=None):  
        self.db_path = Path(db_path) if db_path else _QUEUE_DB_PATH  
        self.db_path.parent.mkdir(parents=True, exist_ok=True)  
        self._init_db()  
  
    def _connect(self):  
        conn = sqlite3.connect(self.db_path, timeout=30)  
        conn.row_factory = sqlite3.Row  
        return conn  
  
    def _init_db(self):  
        with self._connect() as conn:  
            conn.execute('PRAGMA journal_mode=WAL')  
            conn.execute('CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY AUTOINCREMENT, job_type TEXT NOT NULL, payload TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, available_at TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT, worker_name TEXT, last_error TEXT)')  
            conn.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status_available ON jobs(status, available_at, created_at)')  
            conn.commit() 
  
    def enqueue_document(self, document_id):  
        now = _utcnow().isoformat()  
        payload = json.dumps({'document_id': document_id})  
        with self._connect() as conn:  
            cursor = conn.execute('INSERT INTO jobs (job_type, payload, status, attempts, available_at, created_at) VALUES (?, ?, ?, ?, ?, ?)', ('process_document', payload, 'queued', 0, now, now))  
            conn.commit()  
            return cursor.lastrowid  
  
    def claim_next(self, worker_name):  
        now = _utcnow().isoformat()  
        with self._connect() as conn:  
            conn.execute('BEGIN IMMEDIATE')  
            row = conn.execute('SELECT id, job_type, payload, attempts FROM jobs WHERE status = ? AND available_at <= ? ORDER BY created_at ASC LIMIT 1', ('queued', now)).fetchone()  
            if row is None:  
                conn.commit()  
                return None  
            conn.execute('UPDATE jobs SET status = ?, attempts = attempts + 1, started_at = ?, worker_name = ?, last_error = NULL WHERE id = ?', ('processing', now, worker_name, row['id']))  
            conn.commit()  
        return {'id': row['id'], 'job_type': row['job_type'], 'payload': json.loads(row['payload']), 'attempts': int(row['attempts']) + 1}  
  
    def mark_complete(self, job_id):  
        finished_at = _utcnow().isoformat()  
        with self._connect() as conn:  
            conn.execute('UPDATE jobs SET status = ?, finished_at = ? WHERE id = ?', ('completed', finished_at, job_id))  
            conn.commit() 
  
    def mark_failed(self, job_id, attempts, error):  
        message = (error or 'Unknown worker error')[:2000]  
        with self._connect() as conn:  
            if attempts >= _MAX_ATTEMPTS:  
                conn.execute('UPDATE jobs SET status = ?, finished_at = ?, last_error = ? WHERE id = ?', ('failed', _utcnow().isoformat(), message, job_id))  
            else:  
                available_at = (_utcnow() + timedelta(seconds=_RETRY_DELAY_SECONDS)).isoformat()  
                conn.execute('UPDATE jobs SET status = ?, available_at = ?, worker_name = NULL, last_error = ? WHERE id = ?', ('queued', available_at, message, job_id))  
            conn.commit()  
  
    def get_status(self):  
        counts = {'queued': 0, 'processing': 0, 'completed': 0, 'failed': 0, 'total': 0}  
        with self._connect() as conn:  
            rows = conn.execute('SELECT status, COUNT(*) AS count FROM jobs GROUP BY status').fetchall()  
            for row in rows:  
                status = row['status']  
                if status in counts:  
                    counts[status] = int(row['count'])  
                    counts['total'] += int(row['count'])  
            oldest_queued = conn.execute('SELECT created_at FROM jobs WHERE status = ? ORDER BY created_at ASC LIMIT 1', ('queued',)).fetchone()  
            active_workers = [row['worker_name'] for row in conn.execute('SELECT DISTINCT worker_name FROM jobs WHERE status = ? AND worker_name IS NOT NULL AND worker_name != ? ORDER BY worker_name ASC', ('processing', '')).fetchall()]  
            recent_failures = []  
            for row in conn.execute('SELECT id, last_error, finished_at, attempts FROM jobs WHERE status = ? ORDER BY finished_at DESC, id DESC LIMIT 5', ('failed',)).fetchall():  
                recent_failures.append({'id': int(row['id']), 'last_error': row['last_error'], 'finished_at': row['finished_at'], 'attempts': int(row['attempts'])})  
        return {'counts': counts, 'oldest_queued_at': oldest_queued['created_at'] if oldest_queued else None, 'active_workers': active_workers, 'recent_failures': recent_failures}  
  
  
job_queue = JobQueue() 
