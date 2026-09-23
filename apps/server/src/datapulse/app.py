from fastapi import FastAPI, Request, Response

from datapulse.ai.api import router as ai_router
from datapulse.auth.api import router as auth_router
from datapulse.dataset.api import router as dataset_router
from datapulse.datasource.api import router as datasource_router
from datapulse.display.api import admin_router as display_admin_router
from datapulse.display.api import player_router
from datapulse.ecosystem.api import router as ecosystem_router
from datapulse.ecosystem.runtime_api import router as plugin_runtime_router
from datapulse.embedding.api import admin_router as embed_admin_router
from datapulse.embedding.api import router as embed_router
from datapulse.errors import install_error_handlers, install_request_logging, request_id_middleware
from datapulse.filedata.api import router as file_router
from datapulse.identity.api import router as identity_router
from datapulse.lifespan import create_lifespan
from datapulse.screen.access import ScreenAccessPolicyInvalid, normalize_origin
from datapulse.screen.api import router as screen_router
from datapulse.screen.asset_api import router as screen_asset_router
from datapulse.screen.runtime_api import router as screen_runtime_router
from datapulse.settings import Settings
from datapulse.speech.api import internal_router as speech_internal_router
from datapulse.speech.api import router as speech_router
from datapulse.static import create_spa_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    install_request_logging()
    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        lifespan=create_lifespan(resolved),
    )
    app.middleware("http")(request_id_middleware)

    @app.middleware("http")
    async def embed_cors_preflight(request: Request, call_next):
        # Authorization on cross-origin Embed fetches requires a preflight. The
        # ticket and origin are still enforced on the actual endpoint request.
        if request.method == "OPTIONS" and request.url.path.startswith("/api/embed/"):
            raw_origin = request.headers.get("origin")
            try:
                origin = normalize_origin(raw_origin) if raw_origin else "null"
            except ScreenAccessPolicyInvalid:
                origin = "null"
            headers = {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
                "Access-Control-Max-Age": "600",
                "Vary": "Origin",
            }
            return Response(status_code=204, headers=headers)
        return await call_next(request)

    @app.middleware("http")
    async def embed_cors_errors(request: Request, call_next):
        response = await call_next(request)
        if (
            request.url.path.startswith("/api/embed/")
            and "access-control-allow-origin" not in response.headers
        ):
            raw_origin = request.headers.get("origin")
            if raw_origin:
                try:
                    origin = normalize_origin(raw_origin)
                except ScreenAccessPolicyInvalid:
                    origin = "null"
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Expose-Headers"] = (
                    "Content-Length, ETag, X-Request-ID"
                )
                response.headers["Vary"] = "Origin"
        return response

    install_error_handlers(app)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": resolved.app_version}

    app.include_router(auth_router)
    app.include_router(identity_router)
    app.include_router(ecosystem_router)
    app.include_router(plugin_runtime_router)
    app.include_router(ai_router)
    app.include_router(datasource_router)
    app.include_router(dataset_router)
    app.include_router(file_router)
    app.include_router(screen_router)
    app.include_router(screen_asset_router)
    app.include_router(screen_runtime_router)
    app.include_router(speech_router)
    app.include_router(speech_internal_router)
    app.include_router(display_admin_router)
    app.include_router(player_router)
    app.include_router(embed_admin_router)
    app.include_router(embed_router)

    if resolved.static_dir is not None:
        app.include_router(create_spa_router(resolved.static_dir))

    return app


app = create_app()
