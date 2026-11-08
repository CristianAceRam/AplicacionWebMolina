"""Tests del validador único de Instagram y de las constantes de ubicación (Fase E)."""
import pytest
from pydantic import ValidationError

from app.constants import INSTAGRAM_MAX_LONGITUD, NOMBRES_UBICACION
from app.models import Ubicacion
from app.schemas import ActualizarPerfilIn, CitaCreate, _validar_instagram


# ── Constantes ────────────────────────────────────────────────────────────────

def test_nombres_cubren_todas_las_ubicaciones():
    assert set(NOMBRES_UBICACION) == {u.value for u in Ubicacion}
    assert NOMBRES_UBICACION["alcala"] == "Alcalá la Real"
    assert NOMBRES_UBICACION["granada"] == "Granada"


# ── Validador ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("juan.perez", "juan.perez"),
        ("@Juan_Perez", "juan_perez"),      # sin @ y en minúsculas
        ("  Molina.Style  ", "molina.style"),  # espacios alrededor
        ("a", "a"),
        ("x" * INSTAGRAM_MAX_LONGITUD, "x" * INSTAGRAM_MAX_LONGITUD),
        ("user_2026", "user_2026"),
        ("_._", "_._"),
    ],
)
def test_instagram_valido_se_normaliza(entrada, esperado):
    assert _validar_instagram(entrada) == esperado


@pytest.mark.parametrize(
    "entrada",
    [
        "",
        "   ",
        "@",
        "x" * (INSTAGRAM_MAX_LONGITUD + 1),
        ".juan",
        "juan.",
        "ju..an",
        "juan-perez",
        "juán",
        "juan perez",
        "@@juan",
        "https://instagram.com/juan",
        "juan/",
        "<script>",
    ],
)
def test_instagram_invalido(entrada):
    with pytest.raises(ValueError):
        _validar_instagram(entrada)


def test_instagram_no_texto():
    with pytest.raises(ValueError):
        _validar_instagram(12345)


# ── El MISMO validador en POST /citas y PATCH /usuarios/me ────────────────────

_BASE_CITA = {"servicio_id": 1, "fecha": "2026-12-01", "hora_inicio": "10:00:00", "ubicacion": "alcala"}


def test_cita_create_usa_el_validador():
    assert CitaCreate(**_BASE_CITA, instagram="@Juan.Perez").instagram == "juan.perez"
    with pytest.raises(ValidationError):
        CitaCreate(**_BASE_CITA, instagram="ju..an")


def test_perfil_usa_el_validador():
    assert ActualizarPerfilIn(instagram="@Juan.Perez").instagram == "juan.perez"
    with pytest.raises(ValidationError):
        ActualizarPerfilIn(instagram="juan.")


def test_cita_create_ubicacion_obligatoria_y_valida():
    sin = {k: v for k, v in _BASE_CITA.items() if k != "ubicacion"}
    with pytest.raises(ValidationError):
        CitaCreate(**sin)
    with pytest.raises(ValidationError):
        CitaCreate(**{**_BASE_CITA, "ubicacion": "madrid"})
    assert CitaCreate(**{**_BASE_CITA, "ubicacion": "granada"}).ubicacion is Ubicacion.granada
