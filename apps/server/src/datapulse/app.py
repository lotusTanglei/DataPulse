from fastapi import FastAPI

from datapulse.auth.api import router as auth_router
from datapulse.dataset.api import router as dataset_router
from datapulse.datasource.api import router as datasource_router
from datapulse.errors import install_error_handlers, request_id_middleware
from datapulse.lifespan import create_lifespan
from datapulse.settings import Settings
from datapulse.static import create_spa_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(
        title=resolved.app_name,
        version=resolved.app_version,
        lifespan=create_lifespan(resolved),
    )
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": resolved.app_version}

    app.include_router(auth_router)
    app.include_router(datasource_router)
    app.include_router(dataset_router)

    if resolved.static_dir is not None:
        app.include_router(create_spa_router(resolved.static_dir))

    return app


app = create_app()
