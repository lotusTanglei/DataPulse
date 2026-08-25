from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from datapulse.display.service import (
    DisplayAccessDenied,
    DisplayAddressDenied,
    DisplayScreenUnavailable,
)
from datapulse.embedding.page import embed_page_response
from datapulse.screen.access import request_origin_from_headers
from datapulse.screen.repository import ScreenNotFound


def create_spa_router(static_dir: Path) -> APIRouter:
    root = static_dir.resolve()
    router = APIRouter(include_in_schema=False)

    @router.get("/play/{screen_id}")
    async def standalone_player(request: Request, screen_id: str) -> FileResponse:
        display_access_service = getattr(request.app.state, "display_access_service", None)
        if display_access_service is not None:
            try:
                await display_access_service.authorize_request(
                    screen_id,
                    origin=request_origin_from_headers(
                        origin=request.headers.get("origin"),
                        referer=request.headers.get("referer"),
                    ),
                    client_ip=request.client.host if request.client is not None else None,
                )
            except ScreenNotFound as error:
                raise HTTPException(status_code=404, detail="Screen not found") from error
            except DisplayScreenUnavailable as error:
                raise HTTPException(status_code=409, detail="Screen unavailable") from error
            except (DisplayAddressDenied, DisplayAccessDenied, ValueError) as error:
                raise HTTPException(status_code=403, detail="Display address denied") from error
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
