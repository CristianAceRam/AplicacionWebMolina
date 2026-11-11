FRANJA_MINUTOS = 30
DIAS_MAX_RESERVA = 30
DURACION_MAX_MINUTOS = 300
MAX_CITAS_ACTIVAS = 2

# Ciudades donde trabaja el peluquero (agenda única para las dos).
# Las claves son los valores de Cita.ubicacion (enum Ubicacion en models.py).
NOMBRES_UBICACION = {
    "alcala": "Alcalá la Real",
    "granada": "Granada",
}

# Longitud máxima de un usuario de Instagram (regla de Instagram).
INSTAGRAM_MAX_LONGITUD = 30
