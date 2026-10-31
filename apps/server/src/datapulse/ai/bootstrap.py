from fastapi import FastAPI

from datapulse.ai.context import DatasetContextService
from datapulse.ai.gateway import AiGateway
from datapulse.ai.service import AiService


def configure_ai(
    app: FastAPI,
    settings,
    *,
    dataset_repository,
    datasource_service,
    registry,
    file_asset_repository,
    file_query_service,
    profile_service,
    planning_service,
) -> AiGateway:
    gateway = AiGateway(
        enabled=True,
        base_url=settings.ai_base_url,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        timeout_seconds=settings.ai_timeout_seconds,
    )
    context_service = DatasetContextService(
        dataset_repository=dataset_repository,
        datasource_service=datasource_service,
        registry=registry,
        file_asset_repository=file_asset_repository,
        file_query_service=file_query_service,
        profile_service=profile_service,
        max_context_fields=settings.ai_max_context_fields,
        max_context_chars=settings.ai_max_context_chars,
    )
    app.state.ai_gateway = gateway
    app.state.dataset_context_service = context_service
    app.state.ai_service = AiService(
        gateway=gateway,
        context_service=context_service,
        dataset_repository=dataset_repository,
        datasource_service=datasource_service,
        registry=registry,
        file_asset_repository=file_asset_repository,
        file_query_service=file_query_service,
        planning_service=planning_service,
        max_context_rows=settings.ai_max_context_rows,
        screen_timeout_seconds=settings.ai_screen_timeout_seconds,
    )
    return gateway


__all__ = ["configure_ai"]
