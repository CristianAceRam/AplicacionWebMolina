"""Tests para PATCH /usuarios/me y PATCH /usuarios/me/password."""
import pytest


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── PATCH /usuarios/me ────────────────────────────────────────────────────────

def test_actualizar_nombre_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Juan Pedro García"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["nombre_completo"] == "Juan Pedro García"


def test_actualizar_telefono_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"telefono": "698765432"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["telefono"] == "698765432"


def test_actualizar_ambos_campos(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Ana María López", "telefono": "711222333"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nombre_completo"] == "Ana María López"
    assert data["telefono"] == "711222333"


def test_actualizar_nombre_normaliza_espacios(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "  Juan   Pérez  "},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json()["nombre_completo"] == "Juan Pérez"


def test_actualizar_nombre_una_sola_palabra_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Solo"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_telefono_invalido_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"telefono": "512345678"},  # empieza por 5 — no válido en España
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_sin_campos_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_email_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"email": "otro@example.com"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_rol_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"rol": "admin"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_campo_bloqueado_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me",
        json={"bloqueado": False, "nombre_completo": "Juan Pedro García"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_actualizar_perfil_sin_token_401(client):
    r = client.patch(
        "/usuarios/me",
        json={"nombre_completo": "Juan Pedro García"},
    )
    assert r.status_code == 401


# ── PATCH /usuarios/me/password ───────────────────────────────────────────────

def test_cambiar_password_exitoso(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200


def test_cambiar_password_actual_incorrecta_400(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "contraseñaErronea", "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 400
    assert "contraseña actual" in r.json()["detail"].lower()


def test_cambiar_password_nueva_demasiado_corta_422(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "corta"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_cambiar_password_campo_extra_rechazado(client, cliente_token):
    r = client.patch(
        "/usuarios/me/password",
        json={
            "password_actual": "clientepass123",
            "password_nueva": "nuevaClave99",
            "email": "hacker@x.com",
        },
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


def test_cambiar_password_revoca_sesiones(client, cliente_token):
    """Cambiar la contraseña cierra todas las sesiones, incluida la actual."""
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 200
    assert r.json() == {"detail": "Contraseña actualizada correctamente"}

    assert client.get("/usuarios/me", headers=_auth(cliente_token)).status_code == 401

    r = client.post("/login", json={"email": "cli@test.com", "password": "nuevaClave99"})
    assert r.status_code == 200
    nuevo = r.json()["access_token"]
    assert client.get("/usuarios/me", headers=_auth(nuevo)).status_code == 200


def test_cambiar_password_sin_token_401(client):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": "nuevaClave99"},
    )
    assert r.status_code == 401


@pytest.mark.parametrize("password_nueva", ["A" * 80, "ñ" * 40])  # más de 72 bytes
def test_cambiar_password_nueva_mas_de_72_bytes_422(client, cliente_token, password_nueva):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": "clientepass123", "password_nueva": password_nueva},
        headers=_auth(cliente_token),
    )
    assert r.status_code == 422


@pytest.mark.parametrize("password_actual, esperado", [
    ("ñ" * 40, 400),   # 80 bytes: simplemente no coincide
    ("A" * 101, 422),  # supera max_length
])
def test_cambiar_password_actual_larga_no_da_500(client, cliente_token, password_actual, esperado):
    r = client.patch(
        "/usuarios/me/password",
        json={"password_actual": password_actual, "password_nueva": "nuevaClave99"},
        headers=_auth(cliente_token),
    )
    assert r.status_code == esperado


# ── Fase E: Instagram en el perfil ────────────────────────────────────────────

def test_me_incluye_instagram(client, cliente_token):
    r = client.get("/usuarios/me", headers=_auth(cliente_token))
    assert r.status_code == 200
    assert r.json()["instagram"] == "cliente_test"


def test_actualizar_instagram_normaliza(client, cliente_token):
    r = client.patch("/usuarios/me", json={"instagram": "@Mi.Nuevo_IG"}, headers=_auth(cliente_token))
    assert r.status_code == 200
    assert r.json()["instagram"] == "mi.nuevo_ig"
    assert client.get("/usuarios/me", headers=_auth(cliente_token)).json()["instagram"] == "mi.nuevo_ig"


def test_actualizar_instagram_invalido_422(client, cliente_token):
    for malo in ["juan.", ".juan", "ju..an", "juan-perez", "", "x" * 31]:
        r = client.patch("/usuarios/me", json={"instagram": malo}, headers=_auth(cliente_token))
        assert r.status_code == 422, malo
    assert client.get("/usuarios/me", headers=_auth(cliente_token)).json()["instagram"] == "cliente_test"


def test_actualizar_instagram_no_se_puede_vaciar(client, cliente_token):
    r = client.patch("/usuarios/me", json={"instagram": None}, headers=_auth(cliente_token))
    assert r.status_code == 422
    assert client.get("/usuarios/me", headers=_auth(cliente_token)).json()["instagram"] == "cliente_test"


def test_patch_whitelist_rechaza_campos_ajenos(client, cliente_token):
    for campo, valor in [("rol", "admin"), ("bloqueado", False), ("id", 999), ("inasistencias", 0)]:
        r = client.patch(
            "/usuarios/me",
            json={"instagram": "valido_ok", campo: valor},
            headers=_auth(cliente_token),
        )
        assert r.status_code == 422, campo


def test_patch_instagram_solo_toca_al_usuario_del_token(client, db_session, admin_token, cliente_token):
    from app.models import Usuario
    r = client.patch("/usuarios/me", json={"instagram": "cambio_propio"}, headers=_auth(cliente_token))
    assert r.status_code == 200
    admin = db_session.query(Usuario).filter_by(email="admin@test.com").one()
    db_session.refresh(admin)
    assert admin.instagram is None
