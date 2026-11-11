"""Tests de la configuración (URL de Neon, NullPool, prepared statements, ENVIRONMENT)."""
import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.database import _engine_kwargs

_NEON_POOLED = (
    "postgresql://usuario:npg_Abc123@ep-algo-123456-pooler.eu-central-1.aws.neon.tech"
    "/neondb?sslmode=require&channel_binding=require"
)


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, secret_key="x", **kw)


def test_url_neon_pooled_se_normaliza_y_conserva_ssl():
    url = _settings(database_url=_NEON_POOLED).database_url
    assert url.startswith("postgresql+psycopg://")
    parsed = make_url(url)
    assert parsed.drivername == "postgresql+psycopg"
    assert parsed.host == "ep-algo-123456-pooler.eu-central-1.aws.neon.tech"
    assert parsed.query["sslmode"] == "require"
    assert parsed.query["channel_binding"] == "require"


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("  postgresql://u:p@h/db?sslmode=require\n", "postgresql+psycopg://u:p@h/db?sslmode=require"),
    ],
)
def test_normalizacion_database_url(entrada, esperado):
    assert _settings(database_url=entrada).database_url == esperado


@pytest.mark.parametrize("valor, esperado", [(" abc \n", "abc"), ("", None), ("   ", None), (None, None)])
def test_cron_secret_se_limpia(valor, esperado):
    assert _settings(database_url="postgresql://u:p@h/db", cron_secret=valor).cron_secret == esperado


def test_engine_nullpool_activado():
    kw = _engine_kwargs("postgresql+psycopg://u:p@h/db", nullpool=True)
    assert kw["poolclass"] is NullPool
    assert kw["connect_args"] == {"prepare_threshold": None}


def test_engine_pool_normal_por_defecto():
    kw = _engine_kwargs("postgresql+psycopg://u:p@h/db", nullpool=False)
    assert "poolclass" not in kw
    # Sin prepared statements también en local (inocuo, mismo comportamiento que en prod).
    assert kw["connect_args"] == {"prepare_threshold": None}


def test_engine_otro_driver_sin_connect_args():
    assert "connect_args" not in _engine_kwargs("sqlite:///:memory:", nullpool=False)


# ── ENVIRONMENT ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("valor", ["staging", "Production", "dev", ""])
def test_environment_invalido_no_arranca(monkeypatch, valor):
    """Un valor no reconocido impide crear Settings (y por tanto arrancar la API)."""
    monkeypatch.setenv("ENVIRONMENT", valor)
    with pytest.raises(ValidationError):
        _settings(database_url="postgresql://u:p@h/db")


@pytest.mark.parametrize("valor", ["development", "production"])
def test_environment_valido(monkeypatch, valor):
    monkeypatch.setenv("ENVIRONMENT", valor)
    assert _settings(database_url="postgresql://u:p@h/db").environment == valor


def test_environment_por_defecto_production(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert _settings(database_url="postgresql://u:p@h/db").environment == "production"
