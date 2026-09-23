from fastapi import APIRouter, Depends, Query, Request, Response

from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.identity.models import (
    AuditResponse,
    GrantRequest,
    ResourceAccessResponse,
    ResourceType,
    UserCreate,
    UserPatch,
    UserResponse,
)

router = APIRouter(prefix="/api/admin", tags=["identity"], dependencies=[Depends(require_admin)])


@router.get("/identity/access/{resource_type}/{resource_id}")
async def resource_access(
    resource_type: ResourceType, resource_id: str, request: Request
) -> ResourceAccessResponse:
    service = request.app.state.identity_service
    user = request.state.admin
    await service.require_access(user, resource_type, resource_id)
    return ResourceAccessResponse(
        **{
            permission: await service.can_access(user, resource_type, resource_id, permission)
            for permission in ("read", "write", "publish", "manage")
        }
    )


@router.get("/users")
async def list_users(request: Request) -> tuple[UserResponse, ...]:
    return await request.app.state.identity_service.users(request.state.admin)


@router.post("/users", status_code=201, dependencies=[Depends(require_csrf)])
async def create_user(payload: UserCreate, request: Request) -> UserResponse:
    return await request.app.state.identity_service.create_user(
        request.state.admin, payload, request.state.request_id
    )


@router.patch("/users/{user_id}", dependencies=[Depends(require_csrf)])
async def update_user(user_id: str, payload: UserPatch, request: Request) -> UserResponse:
    return await request.app.state.identity_service.update_user(
        request.state.admin, user_id, payload, request.state.request_id
    )


@router.get("/identity/directory")
async def identity_directory(request: Request) -> tuple[dict[str, str], ...]:
    return await request.app.state.identity_service.directory()


@router.get("/identity/audit")
async def identity_audit(
    request: Request, limit: int = Query(default=100, ge=1, le=500)
) -> tuple[AuditResponse, ...]:
    return await request.app.state.identity_service.audit(request.state.admin, limit)


@router.get("/permissions")
async def list_permissions(
    request: Request,
    resource_type: ResourceType,
    resource_id: str = Query(min_length=1, max_length=36),
) -> tuple[GrantRequest, ...]:
    return await request.app.state.identity_service.grants(
        request.state.admin, resource_type, resource_id
    )


@router.put("/permissions", dependencies=[Depends(require_csrf)])
async def set_permission(payload: GrantRequest, request: Request) -> GrantRequest:
    return await request.app.state.identity_service.set_grant(
        request.state.admin, payload, request.state.request_id
    )


@router.delete(
    "/permissions/{resource_type}/{resource_id}/{user_id}",
    status_code=204,
    dependencies=[Depends(require_csrf)],
)
async def revoke_permission(
    resource_type: ResourceType, resource_id: str, user_id: str, request: Request
) -> Response:
    await request.app.state.identity_service.revoke_grant(
        request.state.admin, resource_type, resource_id, user_id, request.state.request_id
    )
    return Response(status_code=204)
