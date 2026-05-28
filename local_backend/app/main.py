"""FastAPI application factory and entry point.

Run with:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cells_router, health_router
from app.core.config import config


def create_app() -> FastAPI:
    application = FastAPI(title=config.service_name)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(
        health_router.router,
        prefix=config.api_prefix,
        tags=["health"],
    )
    application.include_router(
        cells_router.router,
        prefix=config.api_prefix,
    )
    return application


app = create_app()
