from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_no_toca_la_bd(monkeypatch):
    """/health no abre conexión a la BD (Neon puede seguir escalado a cero)."""
    from sqlalchemy.engine import Engine

    def _prohibido(*args, **kwargs):
        raise AssertionError("/health no debe conectarse a la BD")

    monkeypatch.setattr(Engine, "connect", _prohibido)
    monkeypatch.setattr(Engine, "raw_connection", _prohibido)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_security_headers():
    response = client.get("/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "strict-origin-when-cross-origin" in response.headers["referrer-policy"]
    assert "frame-ancestors" in response.headers["content-security-policy"]
