from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.document_routes import router as document_router
from app.routes.settings_routes import router as settings_router
from app.routes.upload_routes import router as upload_router


def create_app() -> FastAPI:
    app = FastAPI(title="Legal AI Analyzer API", version="0.1.0")

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