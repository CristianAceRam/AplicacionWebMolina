"""Tests de la obtención de la IP del cliente para el rate limiting."""
import pytest
from starlette.requests import Request

from app.config import settings
from app.rate_limit import get_real_ip


def _request(headers: dict[str, str] | None = None, client_host: str = "10.0.0.1") -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
        "client": (client_host, 12345),
    }
    return Request(scope)


# ── Vercel ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def en_vercel(monkeypatch):
    monkeypatch.setattr(settings, "vercel", True)


def test_vercel_prefiere_x_vercel_forwarded_for(en_vercel):
    req = _request({
        "x-vercel-forwarded-for": "203.0.113.7",
        "x-real-ip": "198.51.100.1",
        "x-forwarded-for": "192.0.2.1",
    })
    assert get_real_ip(req) == "203.0.113.7"


def test_vercel_usa_x_real_ip(en_vercel):
    req = _request({"x-real-ip": "198.51.100.1", "x-forwarded-for": "192.0.2.1"})
    assert get_real_ip(req) == "198.51.100.1"


def test_vercel_usa_primer_x_forwarded_for(en_vercel):
    req = _request({"x-forwarded-for": "192.0.2.1, 10.1.1.1"})
    assert get_real_ip(req) == "192.0.2.1"


def test_vercel_ipv6(en_vercel):
    req = _request({"x-vercel-forwarded-for": "2001:db8::1"})
    assert get_real_ip(req) == "2001:db8::1"


def test_vercel_ip_invalida_pasa_a_la_siguiente(en_vercel):
    req = _request({"x-vercel-forwarded-for": "no-es-una-ip", "x-real-ip": "198.51.100.1"})
    assert get_real_ip(req) == "198.51.100.1"


def test_vercel_sin_cabeceras_validas_usa_conexion(en_vercel):
    req = _request({"x-forwarded-for": "basura"}, client_host="10.9.9.9")
    assert get_real_ip(req) == "10.9.9.9"


# ── Local / tests: cabeceras de proxy ignoradas ───────────────────────────────

def test_local_ignora_cabeceras_falsificables():
    req = _request(
        {"x-forwarded-for": "1.2.3.4", "x-real-ip": "1.2.3.4", "x-vercel-forwarded-for": "1.2.3.4"},
        client_host="10.0.0.1",
    )
    assert get_real_ip(req) == "10.0.0.1"


# ── Render: comportamiento histórico ──────────────────────────────────────────

def test_render_mantiene_x_forwarded_for(monkeypatch):
    monkeypatch.setattr(settings, "render", True)
    req = _request({"x-forwarded-for": "192.0.2.1, 10.1.1.1"}, client_host="10.0.0.1")
    assert get_real_ip(req) == "192.0.2.1"


# ── Integración: límite de /login por IP ──────────────────────────────────────

def _login(client, ip):
    return client.post(
        "/login",
        json={"email": "nadie@test.com", "password": "x"},
        headers={"x-vercel-forwarded-for": ip},
    )


def test_login_limite_independiente_por_ip_en_vercel(client, en_vercel):
    for _ in range(5):
        assert _login(client, "203.0.113.1").status_code == 401
    # La 6.ª petición desde la misma IP se bloquea...
    assert _login(client, "203.0.113.1").status_code == 429
    # ...pero otro usuario (otra IP) no comparte el límite.
    assert _login(client, "203.0.113.2").status_code == 401


def test_login_local_cabecera_falsificada_no_evita_limite(client):
    # Fuera de Vercel cambiar la cabecera no da cupo nuevo: cuenta la IP de la conexión.
    for i in range(5):
        assert _login(client, f"203.0.113.{i + 10}").status_code == 401
    assert _login(client, "203.0.113.99").status_code == 429
