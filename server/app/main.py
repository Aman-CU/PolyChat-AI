from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from fastapi import APIRouter

# API routers
from .api.v1.models import router as models_router
from .api.v1.chat import router as chat_router
from .api.v1.conversations import router as conversations_router
from .core.logging import setup_logging
from .db.session import init_db


def create_app() -> FastAPI:
    # Setup logging early
    setup_logging()
    app = FastAPI(title="PolyChat Server", version="0.1.0")

    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.allowed_origins],
        # Robust local dev: allow both localhost and 127.0.0.1 on port 3000 via regex
        allow_origin_regex=r"https?://(localhost|127\\.0\\.0\\.1):3000",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1
    api_v1 = APIRouter()
    api_v1.include_router(models_router, prefix="/v1")
    api_v1.include_router(chat_router, prefix="/v1")
    api_v1.include_router(conversations_router, prefix="/v1")
    app.include_router(api_v1, prefix="/api")

    @app.on_event("startup")
    async def _startup() -> None:
        # Ensure SQLite tables exist
        await init_db()

    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.get("/")
    def root():
        return {"service": "polychat", "version": "0.1.0"}

    return app


app = create_app()


