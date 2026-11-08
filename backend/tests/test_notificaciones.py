"""Tests para las notificaciones Telegram al peluquero."""
from unittest.mock import patch

import httpx
import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Bloque A: tests de endpoint ───────────────────────────────────────────────
# Mockean enviar_aviso_peluquero en el punto donde está importado en citas.py

def test_reserva_dispara_aviso(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
                "ubicacion": "alcala",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
    mock_fn.assert_called_once()


def test_reserva_mensaje_contiene_datos(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
                "ubicacion": "alcala",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
    mensaje = mock_fn.call_args[0][0]
    assert "Cliente Test" in mensaje          # nombre del fixture cliente_token
    assert "600000001" in mensaje             # teléfono del fixture
    assert "Corte" in mensaje                 # nombre del servicio fixture
    assert fecha_test.strftime("%d/%m/%Y") in mensaje
    assert "10:00" in mensaje


def test_cancelacion_cliente_dispara_aviso(client, cliente_token, servicio_corte, horario_dia, fecha_test):
    r = client.post(
        "/citas",
        json={
            "servicio_id": servicio_corte.id,
            "fecha": str(fecha_test),
            "hora_inicio": "10:00:00",
            "ubicacion": "alcala",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 201
    cita_id = r.json()["id"]

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r2.status_code == 200
    mock_fn.assert_called_once()


def test_cancelacion_admin_no_dispara_aviso(
    client, cliente_token, admin_token, servicio_corte, horario_dia, fecha_test
):
    r = client.post(
        "/citas",
        json={
            "servicio_id": servicio_corte.id,
            "fecha": str(fecha_test),
            "hora_inicio": "10:00:00",
            "ubicacion": "alcala",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 201
    cita_id = r.json()["id"]

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r2 = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(admin_token))
    assert r2.status_code == 200
    mock_fn.assert_not_called()


# ── Bloque B: tests unitarios del módulo telegram ─────────────────────────────
# Mockean httpx.post directamente dentro del módulo

def test_sin_token_telegram_httpx_no_se_llama():
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = None
        mock_cfg.telegram_chat_id = None
        enviar_aviso_peluquero("hola")
    mock_post.assert_not_called()


def test_excepcion_httpx_no_propaga():
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok"
        mock_cfg.telegram_chat_id = "999"
        mock_post.side_effect = httpx.NetworkError("caído")
        enviar_aviso_peluquero("hola")  # no debe lanzar


def test_reserva_falla_envio_devuelve_201(
    client, cliente_token, servicio_corte, horario_dia, fecha_test
):
    with patch(
        "app.routers.citas.enviar_aviso_peluquero",
        side_effect=Exception("Telegram caído"),
    ):
        r = client.post(
            "/citas",
            json={
                "servicio_id": servicio_corte.id,
                "fecha": str(fecha_test),
                "hora_inicio": "10:00:00",
                "ubicacion": "alcala",
            },
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201


# ── Bloque C: envío síncrono (serverless) — nunca rompe la operación ──────────

def _reservar(client, token, servicio_id, fecha, hora="10:00:00"):
    r = client.post(
        "/citas",
        json={"servicio_id": servicio_id, "fecha": str(fecha), "hora_inicio": hora, "ubicacion": "alcala"},
        headers=_auth(token),
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_cancelacion_falla_envio_devuelve_200(
    client, cliente_token, servicio_corte, horario_dia, fecha_test
):
    cita_id = _reservar(client, cliente_token, servicio_corte.id, fecha_test)
    with patch(
        "app.routers.citas.enviar_aviso_peluquero",
        side_effect=Exception("Telegram caído"),
    ):
        r = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r.status_code == 200
    assert r.json()["estado"] == "cancelada"


def test_reprogramacion_falla_envio_devuelve_200(client, db_session, cliente_token, servicio_corte):
    from datetime import date, time, timedelta

    from app.models import HorarioPeluquero

    origen = date.today() + timedelta(days=2)    # >24 h de antelación
    destino = date.today() + timedelta(days=3)
    for f in (origen, destino):
        db_session.add(HorarioPeluquero(dia_semana=f.weekday(), hora_apertura=time(9, 0), hora_cierre=time(18, 0)))
    db_session.commit()

    cita_id = _reservar(client, cliente_token, servicio_corte.id, origen)
    with patch(
        "app.routers.citas.enviar_aviso_peluquero",
        side_effect=Exception("Telegram caído"),
    ):
        r = client.patch(
            f"/citas/{cita_id}/reprogramar",
            json={"fecha": str(destino), "hora_inicio": "11:00:00"},
            headers=_auth(cliente_token),
        )
    assert r.status_code == 200
    assert r.json()["fecha"] == str(destino)


def test_httpx_timeout_corto():
    """El envío usa un timeout corto (~3 s) para no colgar la petición."""
    from app.notificaciones.telegram import TELEGRAM_TIMEOUT_SEGUNDOS, enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok"
        mock_cfg.telegram_chat_id = "999"
        mock_post.return_value = httpx.Response(200)
        assert enviar_aviso_peluquero("hola") is True

    assert TELEGRAM_TIMEOUT_SEGUNDOS <= 3
    assert mock_post.call_args.kwargs["timeout"] == TELEGRAM_TIMEOUT_SEGUNDOS


def test_respuesta_no_2xx_devuelve_false():
    """Telegram responde error (p. ej. token inválido) → False, sin excepción."""
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok"
        mock_cfg.telegram_chat_id = "999"
        mock_post.return_value = httpx.Response(401)
        assert enviar_aviso_peluquero("hola") is False


def test_excepcion_no_se_registra_con_detalle(caplog):
    """El log del fallo no incluye el texto de la excepción (podría contener el token)."""
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok-secreto"
        mock_cfg.telegram_chat_id = "999"
        mock_post.side_effect = httpx.ConnectError("https://api.telegram.org/bottok-secreto/sendMessage")
        assert enviar_aviso_peluquero("hola") is False

    assert "tok-secreto" not in caplog.text
    assert "ConnectError" in caplog.text


# ── Bloque D: Fase E — ciudad e Instagram en los avisos ───────────────────────

def test_reserva_mensaje_incluye_ciudad_e_instagram(
    client, cliente_token, servicio_corte, horario_dia, fecha_test
):
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.post(
            "/citas",
            json={"servicio_id": servicio_corte.id, "fecha": str(fecha_test),
                  "hora_inicio": "10:00:00", "ubicacion": "granada"},
            headers=_auth(cliente_token),
        )
    assert r.status_code == 201
    mensaje = mock_fn.call_args[0][0]
    assert "Ciudad: Granada" in mensaje
    assert "https://instagram.com/cliente_test" in mensaje


def test_cancelacion_mensaje_incluye_ciudad_e_instagram(
    client, cliente_token, servicio_corte, horario_dia, fecha_test
):
    cita_id = _reservar(client, cliente_token, servicio_corte.id, fecha_test)
    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.patch(f"/citas/{cita_id}/cancelar", headers=_auth(cliente_token))
    assert r.status_code == 200
    mensaje = mock_fn.call_args[0][0]
    assert "Ciudad: Alcalá la Real" in mensaje
    assert "https://instagram.com/cliente_test" in mensaje


def test_reprogramacion_mensaje_incluye_ciudad_e_instagram(client, db_session, cliente_token, servicio_corte):
    from datetime import date, time, timedelta

    from app.models import HorarioPeluquero

    origen = date.today() + timedelta(days=2)
    destino = date.today() + timedelta(days=3)
    for f in (origen, destino):
        db_session.add(HorarioPeluquero(dia_semana=f.weekday(), hora_apertura=time(9, 0), hora_cierre=time(18, 0)))
    db_session.commit()
    cita_id = _reservar(client, cliente_token, servicio_corte.id, origen)

    with patch("app.routers.citas.enviar_aviso_peluquero") as mock_fn:
        r = client.patch(
            f"/citas/{cita_id}/reprogramar",
            json={"fecha": str(destino), "hora_inicio": "11:00:00"},
            headers=_auth(cliente_token),
        )
    assert r.status_code == 200
    mensaje = mock_fn.call_args[0][0]
    assert "De:" in mensaje and "A:" in mensaje
    assert "Ciudad: Alcalá la Real" in mensaje
    assert "https://instagram.com/cliente_test" in mensaje


def test_lineas_sin_instagram_omite_la_linea():
    from app.models import Ubicacion
    from app.notificaciones.telegram import lineas_ciudad_instagram

    assert lineas_ciudad_instagram(Ubicacion.granada, None) == "Ciudad: Granada"
    assert lineas_ciudad_instagram("alcala", "juan.p") == (
        "Ciudad: Alcalá la Real\nInstagram: https://instagram.com/juan.p"
    )


def test_payload_desactiva_vista_previa_de_enlaces():
    """Todos los envíos llevan link_preview_options.is_disabled (no el deprecado disable_web_page_preview)."""
    from app.notificaciones.telegram import enviar_aviso_peluquero

    with (
        patch("app.notificaciones.telegram.settings") as mock_cfg,
        patch("app.notificaciones.telegram.httpx.post") as mock_post,
    ):
        mock_cfg.telegram_bot_token = "tok"
        mock_cfg.telegram_chat_id = "999"
        mock_post.return_value = httpx.Response(200)
        enviar_aviso_peluquero("Instagram: https://instagram.com/juan")

    payload = mock_post.call_args.kwargs["json"]
    assert payload["link_preview_options"] == {"is_disabled": True}
    assert "disable_web_page_preview" not in payload
    assert "parse_mode" not in payload
    assert payload["text"] == "Instagram: https://instagram.com/juan"
