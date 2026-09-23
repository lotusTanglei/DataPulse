from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, UploadFile
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.ecosystem.models import CatalogPackage, PackageKind, TemplateApply
from datapulse.ecosystem.service import MAX_ARCHIVE_BYTES, invalid
from datapulse.metadata import AdminAccount
from datapulse.screen.models import ScreenResponse
from datapulse.screen.repository import ScreenNameConflict


async def require_editor(user: Annotated[AdminAccount, Depends(require_admin)]) -> AdminAccount:
    if getattr(user, "role", None) not in {"admin", "editor"}:
        raise invalid("An editor role is required.", code="AUTH_FORBIDDEN", status=403)
    return user


async def require_package_admin(
    user: Annotated[AdminAccount, Depends(require_editor)],
) -> AdminAccount:
    if getattr(user, "role", None) != "admin":
        raise invalid(
            "Only administrators can install or remove trusted code.",
            code="AUTH_FORBIDDEN",
            status=403,
        )
    return user


router = APIRouter(
    prefix="/api/admin/ecosystem", tags=["ecosystem"], dependencies=[Depends(require_admin)]
)


@router.get("/packages")
async def list_packages(request: Request) -> tuple[CatalogPackage, ...]:
    return await run_in_threadpool(request.app.state.ecosystem_service.list)


@router.post(
    "/packages",
    status_code=201,
    dependencies=[Depends(require_package_admin), Depends(require_csrf)],
)
async def install_package(request: Request, file: UploadFile) -> CatalogPackage:
    try:
        payload = await file.read(MAX_ARCHIVE_BYTES + 1)
        if len(payload) > MAX_ARCHIVE_BYTES:
            raise invalid("Package exceeds upload size limit.", status=413)
        return await run_in_threadpool(request.app.state.ecosystem_service.install, payload)
    finally:
        await file.close()


@router.get("/packages/{kind}/{package_id}/{version}")
async def get_package(
    kind: PackageKind, package_id: str, version: str, request: Request
) -> CatalogPackage:
    return await run_in_threadpool(
        request.app.state.ecosystem_service.get, kind, package_id, version
    )


@router.delete(
    "/packages/{kind}/{package_id}/{version}",
    status_code=204,
    dependencies=[Depends(require_package_admin), Depends(require_csrf)],
)
async def uninstall_package(
    kind: PackageKind, package_id: str, version: str, request: Request
) -> Response:
    await request.app.state.ecosystem_service.uninstall(kind, package_id, version)
    return Response(status_code=204)


@router.post(
    "/packages/template/{package_id}/{version}/apply",
    status_code=201,
    dependencies=[Depends(require_editor), Depends(require_csrf)],
)
async def apply_template(
    package_id: str, version: str, payload: TemplateApply, request: Request
) -> ScreenResponse:
    user = request.state.admin
    identity = getattr(request.app.state, "identity_service", None)
    if identity is None:
        raise invalid(
            "Identity authorization is unavailable.", code="AUTH_UNAVAILABLE", status=503
        )

    async def authorize(kind: str, identifier: str) -> None:
        await identity.require_access(user, kind, identifier, "read")
        await identity.check_stored_references(user, kind, identifier)

    try:
        screen = await request.app.state.ecosystem_service.apply_template(
            package_id, version, payload, authorize_reference=authorize
        )
    except ScreenNameConflict as error:
        raise invalid(
            "A screen with this name already exists.", code="SCREEN_NAME_CONFLICT", status=409
        ) from error
    await identity.register_owner(user, "screen", screen.id)
    return screen


@router.get("/packages/plugin/{package_id}/{version}/files/{file_path:path}")
async def plugin_file(
    package_id: str, version: str, file_path: str, request: Request
) -> FileResponse:
    path = await run_in_threadpool(
        request.app.state.ecosystem_service.file_path, "plugin", package_id, version, file_path
    )
    media_type = {
        ".mjs": "text/javascript",
        ".js": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
    }.get(path.suffix, "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
