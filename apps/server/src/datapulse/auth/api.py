from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from datapulse.auth.bootstrap import BootstrapUnavailable, InvalidSetupCode
from datapulse.auth.dependencies import require_admin, require_csrf, require_same_origin
from datapulse.auth.limiter import LoginRateLimited
from datapulse.auth.password import hash_password, verify_password
from datapulse.errors import DataPulseError
from datapulse.metadata import AdminAccount

router = APIRouter(prefix="/api/auth", tags=["authentication"])


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SetupRequest(RequestModel):
    code: str = Field(min_length=1)
    username: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    password: str = Field(min_length=10)


class LoginRequest(RequestModel):
    username: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ]
    password: str = Field(min_length=1)


class PasswordRequest(RequestModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=10)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "127.0.0.1"


def _set_session_cookies(
    response: Response,
    request: Request,
    *,
    session_token: str,
    csrf_token: str,
) -> None:
    secure = request.app.state.settings.environment == "production"
    response.set_cookie(
        "datapulse_session",
        session_token,
        max_age=8 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "datapulse_csrf",
        csrf_token,
        max_age=8 * 60 * 60,
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response, request: Request) -> None:
    secure = request.app.state.settings.environment == "production"
    response.delete_cookie(
        "datapulse_session",
        httponly=True,
        secure=secure,
        samesite="lax",
        path="/",
    )
    response.delete_cookie(
        "datapulse_csrf",
        httponly=False,
        secure=secure,
        samesite="lax",
        path="/",
    )


@router.get("/status")
async def auth_status(request: Request) -> dict[str, bool]:
    return {"initialized": await request.app.state.auth_repository.has_admin()}


@router.post("/setup", status_code=201)
async def setup(payload: SetupRequest, request: Request, response: Response) -> dict[str, str]:
    require_same_origin(request)
    if await request.app.state.auth_repository.has_admin():
        raise DataPulseError(
            code="AUTH_SETUP_NOT_AVAILABLE",
            message="Administrator setup is not available.",
            status_code=404,
        )
    try:
        admin = await request.app.state.bootstrap_service.create_admin(
            code=payload.code,
            username=payload.username,
            password=payload.password,
        )
    except InvalidSetupCode as error:
        raise DataPulseError(
            code="AUTH_INVALID_SETUP_CODE",
            message="The setup code is invalid or expired.",
            status_code=400,
        ) from error
    except BootstrapUnavailable as error:
        raise DataPulseError(
            code="AUTH_SETUP_NOT_AVAILABLE",
            message="Administrator setup is not available.",
            status_code=404,
        ) from error
    created = await request.app.state.session_service.create(admin_id=admin.id)
    _set_session_cookies(
        response,
        request,
        session_token=created.session_token,
        csrf_token=created.csrf_token,
    )
    return {"id": admin.id, "username": admin.username, "role": admin.role}


@router.post("/login", status_code=204)
async def login(payload: LoginRequest, request: Request, response: Response) -> None:
    require_same_origin(request)
    client_ip = _client_ip(request)
    try:
        request.app.state.login_limiter.check_allowed(client_ip)
    except LoginRateLimited as error:
        raise DataPulseError(
            code="AUTH_RATE_LIMITED",
            message="Too many login attempts. Try again later.",
            status_code=429,
        ) from error

    admin = await request.app.state.auth_repository.get_admin_by_username(payload.username)
    if (
        admin is None
        or not admin.active
        or not verify_password(payload.password, admin.password_hash)
    ):
        request.app.state.login_limiter.record_failure(client_ip)
        raise DataPulseError(
            code="AUTH_INVALID_CREDENTIALS",
            message="The username or password is invalid.",
            status_code=401,
        )

    request.app.state.login_limiter.record_success(client_ip)
    created = await request.app.state.session_service.create(admin_id=admin.id)
    _set_session_cookies(
        response,
        request,
        session_token=created.session_token,
        csrf_token=created.csrf_token,
    )


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf)])
async def logout(request: Request, response: Response) -> None:
    await request.app.state.session_service.logout(request.state.session_token)
    _clear_session_cookies(response, request)


@router.get("/session")
async def session(
    admin: Annotated[AdminAccount, Depends(require_admin)],
) -> dict[str, str]:
    return {"id": admin.id, "username": admin.username, "role": admin.role}


@router.patch("/password", status_code=204, dependencies=[Depends(require_csrf)])
async def change_password(
    payload: PasswordRequest,
    request: Request,
) -> None:
    admin: AdminAccount = request.state.admin
    if not verify_password(payload.current_password, admin.password_hash):
        raise DataPulseError(
            code="AUTH_INVALID_CREDENTIALS",
            message="The username or password is invalid.",
            status_code=401,
        )
    changed_at = datetime.now(UTC)
    await request.app.state.auth_repository.update_admin_password(
        admin.id,
        password_hash=hash_password(payload.new_password),
        changed_at=changed_at,
    )
    await request.app.state.session_service.revoke_other_sessions(
        admin.id,
        request.state.session_token,
    )
