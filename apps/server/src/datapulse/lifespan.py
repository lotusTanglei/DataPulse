import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

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
) -> Callable[[FastAPI], AsyncIterator[None]]:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.bootstrap_code_override is not None and settings.environment != "test":
            raise RuntimeError("bootstrap_code_override is only allowed in the test environment.")
        settings.data_dir.resolve().mkdir(parents=True, exist_ok=True)
        settings.resolved_sources_dir().mkdir(parents=True, exist_ok=True)
        settings.resolved_assets_dir().mkdir(parents=True, exist_ok=True)

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
                    global_limit=4,
                    per_source_limit=2,
                    acquire_timeout=0,
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
            app.state.dataset_service = DatasetService(
                repository=dataset_repository,
                datasource_service=app.state.datasource_service,
                registry=connector_registry,
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

            if not await repository.has_admin():
                setup_code = await bootstrap_service.issue_code()
                logger.warning("DataPulse one-time setup code: %s", setup_code)
            yield
        finally:
            await datasource_engine_manager.dispose_all()
            await engine.dispose()

    return lifespan
