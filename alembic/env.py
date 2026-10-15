import os
from logging.config import fileConfig

from dotenv import load_dotenv

load_dotenv()

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.database import Base
import app.models.business  # noqa: F401
import app.models.user  # noqa: F401
import app.models.business_member  # noqa: F401
import app.models.connection  # noqa: F401
import app.models.product  # noqa: F401
import app.models.instagram_post

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set")
    # asyncpg → driver synchrone pour les migrations Alembic
    return url.replace("postgresql+asyncpg://", "postgresql://")


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
