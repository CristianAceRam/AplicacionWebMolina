from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7   # 7 días = 10 080 min
    # En .env usa formato JSON: ALLOWED_ORIGINS=["http://localhost:5173"]
    allowed_origins: list[str] = ["http://localhost:5173"]
    environment: Literal["development", "production"] = "production"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    retencion_meses: int = 24

    # Serverless (Vercel + Neon): sin pool de conexiones, para que no queden
    # conexiones abiertas entre peticiones y Neon pueda escalar a cero.
    # En local (Docker) se deja en False y se usa el pool normal de SQLAlchemy.
    db_nullpool: bool = False

    # Secreto de los endpoints /cron/*. Vercel lo envía como
    # "Authorization: Bearer <CRON_SECRET>". Si falta, los endpoints quedan desactivados.
    cron_secret: str | None = None

    # Las define la propia plataforma (no hay que configurarlas):
    # Vercel → VERCEL=1, Render → RENDER=true. Se usan para saber en qué
    # cabeceras de proxy se puede confiar para obtener la IP del cliente.
    vercel: bool = False
    render: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @field_validator("database_url", mode="before")
    @classmethod
    def normalizar_database_url(cls, v: str) -> str:
        # Render inyecta postgres:// y Neon da postgresql://; psycopg3 necesita
        # postgresql+psycopg://. El query string (?sslmode=require&...) se conserva.
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+psycopg://", 1)
            elif v.startswith("postgresql://") and "+psycopg" not in v:
                v = v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @field_validator("cron_secret", mode="before")
    @classmethod
    def limpiar_cron_secret(cls, v):
        # Un espacio o salto de línea al pegar el valor haría fallar siempre la comparación.
        if isinstance(v, str):
            v = v.strip()
            return v or None
        return v


settings = Settings()
