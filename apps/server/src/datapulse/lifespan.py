import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from datapulse.ai.context import DatasetContextService
from datapulse.ai.gateway import AiGateway
from datapulse.ai.service import AiService
from datapulse.auth.bootstrap import BootstrapService
from datapulse.auth.limiter import LoginLimiter
from datapulse.auth.repository import AuthRepository
from datapulse.auth.session import SessionService
from datapulse.dataset.repository import DatasetRepository
from datapulse.dataset.service import DatasetService
from datapulse.datasource.engine_manager import EngineManager
from datapulse.datasource.mysql import MySQLConnector
from datapulse.datasource.postgresql import PostgreSQLConnector
from datapulse.datasource.registry import ConnectorRegistry
from datapulse.datasource.repository import DatasourceRepository
from datapulse.datasource.secrets import SecretBox
from datapulse.datasource.service import DatasourceService
from datapulse.datasource.sqlite import SQLiteConnector
from datapulse.display.repository import DisplayAccessRepository
from datapulse.display.service import DisplayAccessService
from datapulse.display.tokens import DisplaySessionCodec
from datapulse.embedding.page import install_ticket_redaction_filter
from datapulse.embedding.repository import EmbedAccessRepository
from datapulse.embedding.service import EmbedService
from datapulse.embedding.tokens import EmbedTicketCodec
from datapulse.filedata.duckdb_executor import DuckDBExecutor
from datapulse.filedata.query import FileDatasetQueryService, FileQueryCompiler
from datapulse.filedata.repository import FileAssetRepository
from datapulse.filedata.service import FileAssetService
from datapulse.filedata.storage import FileStorage
from datapulse.metadata import create_metadata_engine, create_session_factory
from datapulse.query.execution import QueryExecutor, QueryRunRepository
from datapulse.query.limits import QueryLimiter
from datapulse.screen.assets import AssetService, ScreenAssetRepository
from datapulse.screen.publishing import PublishingService
from datapulse.screen.repository import ScreenRepository
from datapulse.screen.runtime import ScreenRuntimeService
from datapulse.screen.service import ScreenService
from datapulse.settings import Settings

logger = logging.getLogger(__name__)
SERVER_ROOT = Path(__file__).resolve().parents[2]


async def check_migration_head(app: FastAPI) -> None:
    config = Config(str(SERVER_ROOT / "alembic.ini"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    try:
        async with app.state.metadata_engine.connect() as connection:
            current = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    except SQLAlchemyError as error:
        raise RuntimeError(
            "DataPulse metadata database is not migrated; run alembic upgrade head."
        ) from error
    if current != expected:
        raise RuntimeError(
            f"DataPulse metadata database revision is {current!r}; expected {expected!r}."
        )


def create_lifespan(
    settings: Settings,
) -> Callable[[FastAPI], AsyncGenerator[None, None]]:
    # Keep startup wiring in one place so tests and production use the same service graph.
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        install_ticket_redaction_filter()
        if settings.bootstrap_code_override is not None and settings.environment != "test":
            raise RuntimeError("bootstrap_code_override is only allowed in the test environment.")
        settings.data_dir.resolve().mkdir(parents=True, exist_ok=True)
        settings.resolved_sources_dir().mkdir(parents=True, exist_ok=True)
        settings.resolved_assets_dir().mkdir(parents=True, exist_ok=True)
        settings.resolved_files_dir().mkdir(parents=True, exist_ok=True)

        engine = create_metadata_engine(settings)
        datasource_engine_manager = EngineManager()
        app.state.settings = settings
        app.state.metadata_engine = engine
        try:
            await check_migration_head(app)
            session_factory = create_session_factory(engine)
            repository = AuthRepository(session_factory)
            token_factory = (
                (lambda: settings.bootstrap_code_override)
                if settings.bootstrap_code_override is not None
                else None
            )
            bootstrap_service = BootstrapService(
                repository,
                token_factory=token_factory,
            )
            app.state.auth_repository = repository
            app.state.bootstrap_service = bootstrap_service
            app.state.session_service = SessionService(repository)
            app.state.login_limiter = LoginLimiter(
                max_failures=5,
                window=timedelta(minutes=15),
            )
            datasource_repository = DatasourceRepository(session_factory)
            connector_registry = ConnectorRegistry(
                [
                    SQLiteConnector(settings),
                    PostgreSQLConnector(),
                    MySQLConnector(),
                ]
            )
            query_executor = QueryExecutor(
                repository=QueryRunRepository(session_factory),
                limiter=QueryLimiter(
                    global_limit=settings.query_global_limit,
                    per_source_limit=settings.query_per_source_limit,
                    acquire_timeout=settings.query_acquire_timeout_seconds,
                ),
                request_id_factory=lambda: str(uuid4()),
            )
            app.state.datasource_engine_manager = datasource_engine_manager
            app.state.datasource_service = DatasourceService(
                repository=datasource_repository,
                secret_box=SecretBox.from_settings(settings),
                registry=connector_registry,
                engine_manager=datasource_engine_manager,
                query_executor=query_executor,
            )
            dataset_repository = DatasetRepository(session_factory)
            file_asset_repository = FileAssetRepository(session_factory)
            file_query_service = FileDatasetQueryService(
                compiler=FileQueryCompiler(),
                executor=DuckDBExecutor(settings),
            )
            app.state.dataset_service = DatasetService(
                repository=dataset_repository,
                datasource_service=app.state.datasource_service,
                registry=connector_registry,
                file_asset_repository=file_asset_repository,
                file_query_service=file_query_service,
            )
            app.state.file_asset_service = FileAssetService(
                repository=file_asset_repository,
                storage=FileStorage(settings),
            )
            app.state.ai_gateway = AiGateway(
                enabled=settings.ai_enabled,
                base_url=settings.ai_base_url,
                api_key=settings.ai_api_key,
                model=settings.ai_model,
                timeout_seconds=settings.ai_timeout_seconds,
            )
            app.state.dataset_context_service = DatasetContextService(
                dataset_repository=dataset_repository,
                datasource_service=app.state.datasource_service,
                registry=connector_registry,
                file_asset_repository=file_asset_repository,
                file_query_service=file_query_service,
            )
            app.state.ai_service = AiService(
                gateway=app.state.ai_gateway,
                context_service=app.state.dataset_context_service,
                dataset_repository=dataset_repository,
                datasource_service=app.state.datasource_service,
                registry=connector_registry,
                file_asset_repository=file_asset_repository,
                file_query_service=file_query_service,
                max_context_rows=settings.ai_max_context_rows,
            )
            screen_repository = ScreenRepository(session_factory)
            app.state.screen_service = ScreenService(
                repository=screen_repository,
            )
            asset_service = AssetService(
                repository=ScreenAssetRepository(session_factory),
                assets_dir=settings.resolved_assets_dir(),
            )
            app.state.asset_service = asset_service
            app.state.publishing_service = PublishingService(
                screen_repository=screen_repository,
                dataset_repository=dataset_repository,
                asset_service=asset_service,
            )
            app.state.screen_runtime_service = ScreenRuntimeService(
                screen_repository=screen_repository,
                dataset_repository=dataset_repository,
                datasource_service=app.state.datasource_service,
                file_asset_repository=file_asset_repository,
                file_query_service=file_query_service,
            )
            signing_key = settings.signing_key_bytes()
            app.state.display_access_service = DisplayAccessService(
                repository=DisplayAccessRepository(session_factory),
                screen_repository=screen_repository,
                codec=(
                    DisplaySessionCodec(signing_key=signing_key)
                    if signing_key is not None
                    else None
                ),
            )
            app.state.embed_service = EmbedService(
                repository=EmbedAccessRepository(session_factory),
                screen_repository=screen_repository,
                codec=(
                    EmbedTicketCodec(signing_key=signing_key)
                    if signing_key is not None
                    else None
                ),
            )

            if not await repository.has_admin():
                setup_code = await bootstrap_service.issue_code()
                logger.warning("DataPulse one-time setup code: %s", setup_code)
            yield
        finally:
            if hasattr(app.state, "ai_gateway"):
                await app.state.ai_gateway.aclose()
            await datasource_engine_manager.dispose_all()
            await engine.dispose()

    return lifespan
