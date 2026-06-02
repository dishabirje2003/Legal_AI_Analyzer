from contextlib import asynccontextmanager
import threading
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.document_routes import router as document_router
from app.routes.settings_routes import router as settings_router
from app.routes.upload_routes import router as upload_router

logger = logging.getLogger(__name__)

def _start_background_worker():
    """Start the document processing worker in a background daemon thread."""
    import time
    import os
    import socket
    from app.services.job_queue import job_queue
    from app.services.processing_service import processing_service

    worker_name = '%s:%s' % (socket.gethostname(), os.getpid())
    logger.info("Background worker started as %s", worker_name)

    while True:
        try:
            job = job_queue.claim_next(worker_name)
            if job is None:
                time.sleep(2.0)
                continue
            try:
                document_id = job['payload'].get('document_id')
                if not document_id:
                    raise ValueError('Missing document_id in job payload')
                success = processing_service.process_document(document_id=document_id)
                if success:
                    job_queue.mark_complete(job['id'])
                    logger.info("Job %s completed successfully", job['id'])
                else:
                    job_queue.mark_failed(job['id'], job['attempts'], 'Processing returned unsuccessful status')
                    logger.warning("Job %s marked as failed", job['id'])
            except Exception as exc:
                logger.exception("Worker job %s failed: %s", job['id'], exc)
                job_queue.mark_failed(job['id'], job['attempts'], str(exc))
        except Exception as exc:
            logger.exception("Worker loop error: %s", exc)
            time.sleep(5.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the background worker thread on startup
    worker_thread = threading.Thread(
        target=_start_background_worker,
        daemon=True,
        name="document-worker"
    )
    worker_thread.start()
    logger.info("Background document worker thread started.")
    yield
    # Worker thread is a daemon so it will stop automatically on shutdown


def create_app() -> FastAPI:
    app = FastAPI(title="Legal AI Analyzer API", version="0.1.0", lifespan=lifespan)

    # Always configure CORS. Use env var if set, otherwise fall back to known Vercel URL.
    # This prevents CORS failures if FRONTEND_ORIGIN is missing after a Render redeploy.
    allowed_origins = []
    if settings.frontend_origin:
        allowed_origins.append(settings.frontend_origin)
    # Hardcoded fallback — ensures the Vercel frontend always works
    vercel_fallback = "https://legal-ai-analyzer-beta.vercel.app"
    if vercel_fallback not in allowed_origins:
        allowed_origins.append(vercel_fallback)
    # Also allow localhost for local development
    allowed_origins.append("http://localhost:5173")
    allowed_origins.append("http://localhost:3000")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


    app.include_router(upload_router)
    app.include_router(document_router)
    app.include_router(dashboard_router)
    app.include_router(settings_router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()