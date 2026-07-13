"""
Personal Wallet Management Platform — FastAPI Application Factory.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.core.seeder import seed_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - On startup: Create tables and seed defaults.
    - On shutdown: Clean up.
    """
    # ── Startup ──
    # Import all models so Base.metadata knows about them
    import app.models  # noqa: F401

    # Create all tables (idempotent — skips existing)
    Base.metadata.create_all(bind=engine)

    # Seed default data
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()

    print(f"[OK] {settings.APP_NAME} v{settings.APP_VERSION} started successfully")
    print(f"[DOCS] API Docs: http://localhost:8000/docs")
    print(f"[DB] Database: {settings.DATABASE_URL}")

    yield

    # ── Shutdown ──
    print(f"[BYE] {settings.APP_NAME} shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Personal Wallet Management Platform — "
            "Digital wallet, expense tracker, budget planner, savings goals, and financial analytics."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Register Routers ──
    from app.api.auth.router import router as auth_router
    from app.api.wallets.router import router as wallets_router
    from app.api.transactions.router import router as transactions_router
    from app.api.categories.router import router as categories_router

    app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
    app.include_router(wallets_router, prefix=settings.API_V1_PREFIX)
    app.include_router(transactions_router, prefix=settings.API_V1_PREFIX)
    app.include_router(categories_router, prefix=settings.API_V1_PREFIX)

    # ── Health Check ──
    @app.get("/health", tags=["System"])
    def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    # ── Static Files & Dashboard ──
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

        @app.get("/", response_class=HTMLResponse, include_in_schema=False)
        def dashboard():
            index_html = static_dir / "index.html"
            return HTMLResponse(content=index_html.read_text(encoding="utf-8"))

    return app
