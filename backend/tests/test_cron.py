"""Tests de los endpoints /cron/* (Vercel Cron, protegidos con CRON_SECRET)."""
from datetime import date, time, timedelta
from unittest.mock import patch

import pytest

from app.config import settings
from app.models import Cita, EstadoCita, Rol, Usuario
from app.security import hash_password

_SECRETO = "s3creto-de-prueba-para-cron"
_RUTAS = ["/cron/recordatorio", "/cron/purga"]


@pytest.fixture()
def cron_activo(monkeypatch):
    monkeypatch.setattr(settings, "cron_secret", _SECRETO)


def _bearer(valor):
    return {"Authorization": f"Bearer {valor}"}


# ── Autorización ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ruta", _RUTAS)
def test_sin_cabecera_401(client, cron_activo, ruta):
    assert client.get(ruta).status_code == 401


@pytest.mark.parametrize("ruta", _RUTAS)
def test_secreto_incorrecto_401(client, cron_activo, ruta):
    assert client.get(ruta, headers=_bearer("otro-secreto")).status_code == 401


@pytest.mark.parametrize("ruta", _RUTAS)
def test_formato_incorrecto_401(client, cron_activo, ruta):
    # Sin el prefijo exacto "Bearer " no vale aunque el secreto sea correcto.
    assert client.get(ruta, headers={"Authorization": _SECRETO}).status_code == 401
    assert client.get(ruta, headers={"Authorization": f"bearer {_SECRETO}"}).status_code == 401


@pytest.mark.parametrize("ruta", _RUTAS)
def test_sin_cron_secret_desactivado_404(client, ruta):
    # conftest deja cron_secret=None: endpoints desactivados aunque se mande algo.
    assert client.get(ruta, headers=_bearer("cualquiera")).status_code == 404


def test_no_aparece_en_openapi():
    # Se usa el esquema directamente: /openapi.json está desactivado si ENVIRONMENT=production.
    from app.main import app
    assert not any(p.startswith("/cron") for p in app.openapi()["paths"])


# ── Ejecución con el secreto correcto ─────────────────────────────────────────

def test_recordatorio_200(client, cron_activo):
    with patch("app.tareas.recordatorio.enviar_aviso_peluquero", return_value=True) as mock_fn:
        r = client.get("/cron/recordatorio", headers=_bearer(_SECRETO))
    assert r.status_code == 200
    assert r.json() == {"ok": True, "enviado": True}
    mock_fn.assert_called_once()
    assert "no tienes citas" in mock_fn.call_args[0][0].lower()


def test_purga_200_borra_antiguas(client, cron_activo, db_session, servicio_corte):
    u = Usuario(
        email="cronpurga@test.com",
        password_hash=hash_password("x"),
        telefono="600000098",
        nombre_completo="Cron Purga",
        rol=Rol.cliente,
    )
    db_session.add(u)
    db_session.commit()
    antigua = Cita(
        cliente_id=u.id,
        servicio_id=servicio_corte.id,
        fecha=date.today() - timedelta(days=365 * 3),   # fuera de la ventana de 24 meses
        hora_inicio=time(10, 0),
        hora_fin=time(10, 30),
        estado=EstadoCita.activa,
    )
    db_session.add(antigua)
    db_session.commit()
    antigua_id = antigua.id

    r = client.get("/cron/purga", headers=_bearer(_SECRETO))
    assert r.status_code == 200
    assert r.json() == {"ok": True, "purgadas": 1}
    db_session.expire_all()
    assert db_session.get(Cita, antigua_id) is None


def test_secreto_no_toca_bd_si_no_autorizado(client, cron_activo):
    """Una petición no autorizada no llega a ejecutar la tarea."""
    with (
        patch("app.routers.cron.enviar_recordatorio") as mock_rec,
        patch("app.routers.cron.purgar") as mock_purga,
    ):
        client.get("/cron/recordatorio", headers=_bearer("mal"))
        client.get("/cron/purga", headers=_bearer("mal"))
    mock_rec.assert_not_called()
    mock_purga.assert_not_called()
