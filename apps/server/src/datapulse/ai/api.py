from typing import NoReturn

from fastapi import APIRouter, Depends, Request

from datapulse.ai.models import AiAnalysisError, AiGatewayError, AiHealth
from datapulse.auth.dependencies import require_admin, require_csrf
from datapulse.contracts.ai import (
    AiAnalysisRequest,
    AiAnalysisResponse,
    AiChartRequest,
    AiChartResponse,
    AiEditRequest,
    AiEditResponse,
    AiScreenRequest,
    AiScreenResponse,
)
from datapulse.errors import DataPulseError

router = APIRouter(
    prefix="/api/admin/ai",
    tags=["ai"],
    dependencies=[Depends(require_admin)],
)


def _raise_ai_error(error: Exception) -> NoReturn:
    if isinstance(error, AiGatewayError):
        statuses = {
            "AI_NOT_CONFIGURED": 503,
            "AI_UNAVAILABLE": 503,
            "AI_TIMEOUT": 504,
            "AI_INVALID_OUTPUT": 422,
        }
        raise DataPulseError(
            code=error.code,
            message="The AI request could not be completed.",
            status_code=statuses[error.code],
        ) from error
    if isinstance(error, AiAnalysisError):
        raise DataPulseError(
            code=error.code,
            message="The AI analysis request is invalid.",
            status_code=422,
        ) from error
    raise error


@router.get("/status")
async def ai_status(request: Request) -> AiHealth:
    return request.app.state.ai_service.health()


@router.post("/analyze", dependencies=[Depends(require_csrf)])
async def analyze(
    payload: AiAnalysisRequest,
    request: Request,
) -> AiAnalysisResponse:
    try:
        return await request.app.state.ai_service.analyze(
            payload,
            request_id=request.state.request_id,
        )
    except (AiGatewayError, AiAnalysisError) as error:
        _raise_ai_error(error)


@router.post("/chart", dependencies=[Depends(require_csrf)])
async def chart(
    payload: AiChartRequest,
    request: Request,
) -> AiChartResponse:
    try:
        return await request.app.state.ai_service.generate_chart(
            payload,
            request_id=request.state.request_id,
        )
    except (AiGatewayError, AiAnalysisError) as error:
        _raise_ai_error(error)


@router.post("/screen", dependencies=[Depends(require_csrf)])
async def screen(
    payload: AiScreenRequest,
    request: Request,
) -> AiScreenResponse:
    try:
        return await request.app.state.ai_service.generate_screen(
            payload,
            request_id=request.state.request_id,
        )
    except (AiGatewayError, AiAnalysisError) as error:
        _raise_ai_error(error)


@router.post("/edit", dependencies=[Depends(require_csrf)])
async def edit(
    payload: AiEditRequest,
    request: Request,
) -> AiEditResponse:
    try:
        return await request.app.state.ai_service.generate_edit(
            payload,
            request_id=request.state.request_id,
        )
    except (AiGatewayError, AiAnalysisError) as error:
        _raise_ai_error(error)
