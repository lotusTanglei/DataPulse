from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from datapulse.embedding.page import embed_page_response


def create_spa_router(static_dir: Path) -> APIRouter:
    root = static_dir.resolve()
    router = APIRouter(include_in_schema=False)

    @router.get("/play/{screen_id}")
    def standalone_player(screen_id: str) -> FileResponse:
        del screen_id
        index = root / "index.html"
        if not index.is_file():
            raise HTTPException(status_code=404, detail="Web application is not built")
        return FileResponse(
            index,
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": "frame-ancestors 'none'",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @router.get("/embed/{screen_id}")
    async def embedded_player(
        request: Request,
        screen_id: str,
        ticket: str = Query(min_length=1),
    ) -> FileResponse:
        return await embed_page_response(
            request=request,
            static_root=root,
            screen_id=screen_id,
            ticket=ticket,
        )

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
