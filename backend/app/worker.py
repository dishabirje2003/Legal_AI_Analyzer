from __future__ import annotations 
 
import argparse 
import logging 
import os 
import socket 
import time 
 
from app.services.job_queue import job_queue 
from app.services.processing_service import processing_service 
 
logger = logging.getLogger(__name__) 
 
def _worker_name(): 
    return '%s:%s' % (socket.gethostname(), os.getpid()) 
 
def process_once(worker_name): 
    job = job_queue.claim_next(worker_name) 
    if job is None: 
        return False 
    try: 
        if job['job_type'] != 'process_document': 
            raise ValueError('Unsupported job type: %s' % job['job_type']) 
        document_id = job['payload'].get('document_id') 
        if not document_id: 
            raise ValueError('Missing document_id in job payload') 
        success = processing_service.process_document(document_id=document_id) 
        if success: 
            job_queue.mark_complete(job['id']) 
        else: 
            job_queue.mark_failed(job['id'], job['attempts'], 'Processing returned unsuccessful status') 
    except Exception as exc: 
        logger.exception('Worker job failed: %s', exc) 
        job_queue.mark_failed(job['id'], job['attempts'], str(exc)) 
    return True 
 
def main(): 
    parser = argparse.ArgumentParser(description='Legal AI Analyzer background worker') 
    parser.add_argument('--poll-interval', type=float, default=2.0) 
    parser.add_argument('--once', action='store_true') 
    args = parser.parse_args() 
 
    logging.basicConfig(level=logging.INFO) 
    worker_name = _worker_name() 
    logger.info('Worker started as %s', worker_name) 
    if args.once: 
        process_once(worker_name) 
        return 
    while True: 
        claimed = process_once(worker_name) 
        if not claimed: 
            time.sleep(args.poll_interval) 
 
if __name__ == '__main__': 
    main()
