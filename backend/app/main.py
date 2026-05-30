from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.document_routes import router as document_router
from app.routes.settings_routes import router as settings_router
from app.routes.upload_routes import router as upload_router


def create_app() -> FastAPI:
    app = FastAPI(title="Legal AI Analyzer API", version="0.1.0")

    if settings.frontend_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.frontend_origin],
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