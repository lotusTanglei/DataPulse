from fastapi import FastAPI

from datapulse.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or Settings()
    app = FastAPI(title=resolved.app_name, version=resolved.app_version)

    @app.get("/api/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": resolved.app_version}

    return app


app = create_app()
