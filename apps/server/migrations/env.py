import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from datapulse.metadata import Base, metadata_database_url
from datapulse.settings import Settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def synchronous_url(url: str) -> str:
    replacements = {
        "sqlite+aiosqlite": "sqlite",
        "postgresql+asyncpg": "postgresql",
        "mysql+asyncmy": "mysql",
    }
    for async_driver, sync_driver in replacements.items():
        if url.startswith(f"{async_driver}:"):
            return url.replace(async_driver, sync_driver, 1)
    return url


def configured_url() -> str:
    if "DATAPULSE_DATABASE_URL" in os.environ or "DATAPULSE_DATA_DIR" in os.environ:
        url = metadata_database_url(Settings())
    else:
        url = config.get_main_option("sqlalchemy.url")
    return synchronous_url(url)


def run_migrations_offline() -> None:
    context.configure(
        url=configured_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = configured_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
