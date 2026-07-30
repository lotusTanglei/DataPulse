from fastapi import Request

from datapulse.errors import DataPulseError
from datapulse.metadata import AdminAccount


def require_same_origin(request: Request) -> None:
    expected = f"{request.url.scheme}://{request.url.netloc}"
    if request.headers.get("Origin") != expected:
        raise DataPulseError(
            code="AUTH_ORIGIN_INVALID",
            message="The request origin is not allowed.",
            status_code=403,
        )


async def require_admin(request: Request) -> AdminAccount:
    existing = getattr(request.state, "admin", None)
    if existing is not None:
        return existing
    session_token = request.cookies.get("datapulse_session")
    if session_token is None:
        raise DataPulseError(
            code="AUTH_REQUIRED",
            message="Authentication is required.",
            status_code=401,
        )
    admin = await request.app.state.session_service.authenticate(session_token)
    if admin is None:
        raise DataPulseError(
            code="AUTH_REQUIRED",
            message="Authentication is required.",
            status_code=401,
        )
    request.state.admin = admin
    request.state.session_token = session_token
    return admin


async def require_csrf(request: Request) -> None:
    require_same_origin(request)
    await require_admin(request)
    session_token = request.state.session_token
    cookie_token = request.cookies.get("datapulse_csrf")
    header_token = request.headers.get("X-CSRF-Token")
    if (
        cookie_token is None
        or header_token is None
        or not await request.app.state.session_service.verify_csrf(
            session_token,
            cookie_token=cookie_token,
            header_token=header_token,
        )
    ):
        raise DataPulseError(
            code="AUTH_CSRF_INVALID",
            message="The CSRF token is invalid.",
            status_code=403,
        )
