from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.security.api_key import APIKeyHeader
from starlette.responses import JSONResponse

from app.core.settings import get_settings

from app.db import close_pool, init_pool, open_pool
from app.db.migrator import run_migrations

from app.services.graph import build_agent_graph, open_checkpointer

from app.api.routers import health, threads, user_profiles

from app.core.logging import configure_logging

def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        init_pool(
            settings.database_url,
            settings.db_pool_min_size,
            settings.db_pool_max_size,
        )
        await open_pool()
        await run_migrations()

        checkpointer_stack, checkpointer = await open_checkpointer(settings.database_url)
        await checkpointer.setup()

        app.state.checkpointer_stack = checkpointer_stack
        app.state.checkpointer = checkpointer
        app.state.graph = build_agent_graph(checkpointer)

        try:
            yield
        finally:
            # Shutdown
            await close_pool()

            stack = getattr(app.state, "checkpointer_stack", None)
            if stack is not None:
                await stack.aclose()

            app.state.checkpointer_stack = None
            app.state.checkpointer = None
            app.state.graph = None

    app = FastAPI(title=settings.title, version=settings.version, lifespan=lifespan)

    api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            routes=app.routes,
        )
        openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "ApiKeyAuth"
        ] = {"type": "apiKey", "in": "header", "name": "X-API-Key"}
        openapi_schema.setdefault("security", []).append({"ApiKeyAuth": []})
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def api_key_auth(request: Request, call_next):
        public_paths = {"/health", "/docs", "/openapi.json", "/redoc"}
        if request.url.path.startswith("/docs"):
            return await call_next(request)
        if settings.auth_bypass_health and request.url.path in public_paths:
            return await call_next(request)

        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.n8n_api_key:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        return await call_next(request)

    app.include_router(health.router)
    app.include_router(threads.router)
    app.include_router(user_profiles.router)

    return app

app = create_app()
