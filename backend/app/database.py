from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


def _engine_kwargs(url: str, nullpool: bool) -> dict:
    """Opciones de create_engine según el entorno."""
    kwargs: dict = {}
    if url.startswith("postgresql+psycopg"):
        # El pooler de Neon es PgBouncer en modo transacción. Con conexiones de vida
        # corta los prepared statements no aportan nada, así que se desactivan para
        # no depender de la configuración del pooler. Inocuo en local.
        kwargs["connect_args"] = {"prepare_threshold": None}
    if nullpool:
        # Serverless: cada sesión abre y cierra su conexión; no quedan conexiones
        # ociosas y Neon puede escalar a cero.
        kwargs["poolclass"] = NullPool
    return kwargs


engine = create_engine(
    settings.database_url,
    **_engine_kwargs(settings.database_url, settings.db_nullpool),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
