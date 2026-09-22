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
            "AI_RATE_LIMITED": 429,
            "AI_PROVIDER_4XX": 502,
        }
        messages = {
            "AI_NOT_CONFIGURED": "AI 服务尚未配置，请先完成 AI 配置。",
            "AI_UNAVAILABLE": "AI 服务暂时不可用，请稍后重试。",
            "AI_TIMEOUT": "AI 服务响应超时，请稍后重试。",
            "AI_INVALID_OUTPUT": "AI 返回结果无法使用。",
            "AI_RATE_LIMITED": "AI 服务请求过于频繁，请稍后重试。",
            "AI_PROVIDER_4XX": "AI 服务拒绝了请求，请检查模型或请求配置。",
        }
        raise DataPulseError(
            code=error.code,
            message=messages.get(error.code, "AI 请求无法完成。"),
            status_code=statuses.get(error.code, 503),
        ) from error
    if isinstance(error, AiAnalysisError):
        messages = {
            "AI_FIELD_UNKNOWN": "AI 使用了未知字段，请检查组件和字段绑定。",
            "AI_FRAME_OUT_OF_BOUNDS": "AI 生成的组件超出画布边界，请调整组件位置。",
            "AI_VISUAL_MISMATCH": "AI 选择的图表类型与组件不匹配，请调整图表类型。",
            "AI_BINDING_MISSING": "AI 组件缺少数据绑定，请选择数据集和字段。",
            "AI_COMPONENT_UNKNOWN": "AI 使用了不支持的组件类型，请更换组件。",
            "AI_DATASET_INVALID": "AI 使用的数据集无效或未授权，请检查数据集。",
            "AI_SCREEN_INVALID": "AI 生成的大屏存在布局问题，请检查组件和字段。",
        }
        raise DataPulseError(
            code=error.code,
            message=messages.get(error.code, "AI 生成结果无法使用，请检查组件和字段。"),
            status_code=422,
            field_errors=error.issues,
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
