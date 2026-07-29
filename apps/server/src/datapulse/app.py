from fastapi import FastAPI

from datapulse.settings import Settings
from datapulse.static import create_spa_router


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(title=resolved.app_name, version=resolved.app_version)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": resolved.app_version}

    if resolved.static_dir is not None:
        app.include_router(create_spa_router(resolved.static_dir))

    return app


app = create_app()
