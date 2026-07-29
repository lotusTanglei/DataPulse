from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse


def create_spa_router(static_dir: Path) -> APIRouter:
    root = static_dir.resolve()
    router = APIRouter(include_in_schema=False)

    @router.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)

        candidate = (root / path).resolve()
        if candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)

        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="Web application is not built")
        return FileResponse(index)

    return router
