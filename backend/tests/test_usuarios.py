from datetime import date, time, timedelta

from app.models import Cita, EstadoCita, Rol, Usuario, Ubicacion
from app.security import create_access_token, hash_password


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _payload(servicio_id, fecha, hora="10:00:00"):
    return {"servicio_id": servicio_id, "fecha": str(fecha), "hora_inicio": hora, "ubicacion": "alcala"}


# ---------------------------------------------------------------------------
# Contador de inasistencias
# ---------------------------------------------------------------------------

def test_contador_inasistencias(client, db_session, admin_token, cliente_token, servicio_corte):
    """Después de 2 citas marcadas no_asistida via endpoint, GET /usuarios/{id} devuelve inasistencias=2."""
    cliente = db_session.query(Usuario).filter_by(email="cli@test.com").first()

    for hora in [time(10, 0), time(11, 0)]:
        cita = Cita(
            cliente_id=cliente.id,
            servicio_id=servicio_corte.id,
            fecha=date.today() - timedelta(days=1),
            hora_inicio=hora,
            hora_fin=time(hora.hour, hora.minute + 30),
            estado=EstadoCita.activa,
            ubicacion=Ubicacion.alcala,
        )
        db_session.add(cita)
    db_session.commit()

    citas = db_session.query(Cita).filter_by(cliente_id=cliente.id).all()
    for cita in citas:
        r = client.patch(f"/citas/{cita.id}/no-asistida", headers=_auth(admin_token))
        assert r.status_code == 200

    r = client.get(f"/usuarios/{cliente.id}", headers=_auth(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert data["inasistencias"] == 2
    assert data["id"] == cliente.id


# ---------------------------------------------------------------------------
# Bloqueo de clientes
# ---------------------------------------------------------------------------

def test_bloquear_cliente_impide_reservar(
    client, db_session, admin_token, cliente_token, servicio_corte, horario_dia, fecha_test
):
    """Admin bloquea a un cliente → POST /citas devuelve 403."""
    cliente = db_session.query(Usuario).filter_by(email="cli@test.com").first()

    r = client.patch(f"/usuarios/{cliente.id}/bloquear", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["bloqueado"] is True

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    assert r.status_code == 403


def test_desbloquear_cliente_permite_reservar(
    client, db_session, admin_token, cliente_token, servicio_corte, horario_dia, fecha_test
):
    """Admin desbloquea a un cliente bloqueado → POST /citas devuelve 201."""
    cliente = db_session.query(Usuario).filter_by(email="cli@test.com").first()

    client.patch(f"/usuarios/{cliente.id}/bloquear", headers=_auth(admin_token))

    r = client.patch(f"/usuarios/{cliente.id}/desbloquear", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["bloqueado"] is False

    r = client.post("/citas", json=_payload(servicio_corte.id, fecha_test), headers=_auth(cliente_token))
    assert r.status_code == 201


# ---------------------------------------------------------------------------
# Fase E — Instagram visible para el admin, nunca para otro cliente
# ---------------------------------------------------------------------------

def test_admin_lista_incluye_instagram(client, admin_token, cliente_token):
    r = client.get("/usuarios", headers=_auth(admin_token))
    assert r.status_code == 200
    cliente = next(u for u in r.json() if u["email"] == "cli@test.com")
    assert cliente["instagram"] == "cliente_test"


def test_admin_detalle_incluye_instagram(client, db_session, admin_token, cliente_token):
    cliente = db_session.query(Usuario).filter_by(email="cli@test.com").one()
    r = client.get(f"/usuarios/{cliente.id}", headers=_auth(admin_token))
    assert r.status_code == 200
    assert r.json()["instagram"] == "cliente_test"


def test_cliente_no_ve_instagram_de_otro(client, db_session, cliente_token):
    otro = Usuario(email="otro@test.com", password_hash=hash_password("x"), telefono="600000030",
                   nombre_completo="Otro Cliente", rol=Rol.cliente, instagram="secreto_ajeno")
    db_session.add(otro)
    db_session.commit()

    assert client.get(f"/usuarios/{otro.id}", headers=_auth(cliente_token)).status_code == 403
    assert client.get("/usuarios", headers=_auth(cliente_token)).status_code == 403
    me = client.get("/usuarios/me", headers=_auth(cliente_token)).json()
    assert me["instagram"] == "cliente_test"
    assert "secreto_ajeno" not in str(client.get("/citas/mias", headers=_auth(cliente_token)).json())


def test_cliente_no_puede_editar_instagram_de_otro(client, db_session, cliente_token):
    otro = Usuario(email="otro2@test.com", password_hash=hash_password("x"), telefono="600000031",
                   nombre_completo="Otro Cliente", rol=Rol.cliente, instagram="intacto")
    db_session.add(otro)
    db_session.commit()

    # No existe ruta para editar a otro usuario...
    r = client.patch(f"/usuarios/{otro.id}", json={"instagram": "pirata"}, headers=_auth(cliente_token))
    assert r.status_code in (403, 404, 405)
    # ...y PATCH /usuarios/me no acepta un id de destino.
    r = client.patch("/usuarios/me", json={"id": otro.id, "instagram": "pirata"}, headers=_auth(cliente_token))
    assert r.status_code == 422
    db_session.refresh(otro)
    assert otro.instagram == "intacto"
