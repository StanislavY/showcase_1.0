"""FastAPI application factory and entry point.

Run with:
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from app.api import (
    admin_auth_router,
    auth_router,
    cells_router,
    courier_router,
    hardware_router,
    health_router,
    online_sales_router,
    sales_router,
    sync_router,
)
from app.core.config import config
from app.db.init_db import init_database


@asynccontextmanager
async def lifespan(_application: FastAPI):
    # On startup: create SQLite tables and the 27 empty cells if absent.
    init_database()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title=config.service_name, lifespan=lifespan)
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
    application.include_router(
        courier_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        auth_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        hardware_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        admin_auth_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        sales_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        online_sales_router.router,
        prefix=config.api_prefix,
    )
    application.include_router(
        sync_router.router,
        prefix=config.api_prefix,
        tags=["sync"],
    )
    return application


app = create_app()
