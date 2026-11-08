"""
Recordatorio diario de citas al peluquero por Telegram.

Se ejecuta una vez al día (Vercel Cron → GET /cron/recordatorio, o por CLI con
scripts/recordatorio_diario.py). "Mañana" se calcula SIEMPRE en Europe/Madrid:
no depende de la hora UTC a la que corra el cron.
"""
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Cita, EstadoCita
from app.notificaciones.telegram import enviar_aviso_peluquero, nombre_ubicacion, url_instagram

logger = logging.getLogger(__name__)

_MADRID = ZoneInfo("Europe/Madrid")


def enviar_recordatorio(db: Session | None = None, _manana: date | None = None) -> bool:
    """
    Construye y envía al peluquero el resumen de citas del día siguiente.
    Se envía SIEMPRE, haya o no citas.

    Args:
        db:      Sesión SQLAlchemy externa (endpoint / tests). Si None, crea la propia.
        _manana: Fecha "mañana" explícita (para tests). Si None, calcula en Europe/Madrid.

    Returns:
        True si Telegram confirmó la entrega.
    """
    manana = _manana if _manana is not None else datetime.now(_MADRID).date() + timedelta(days=1)

    _own_session = db is None
    if _own_session:
        db = SessionLocal()
    try:
        citas = (
            db.query(Cita)
            .filter(Cita.estado == EstadoCita.activa, Cita.fecha == manana)
            .options(joinedload(Cita.cliente))
            .order_by(Cita.hora_inicio)
            .all()
        )

        fecha_str = manana.strftime("%d/%m")
        if not citas:
            mensaje = f"Mañana {fecha_str} no tienes citas."
        else:
            lineas = [f"Citas para mañana {fecha_str}:"]
            for cita in citas:
                partes = [
                    f"{cita.hora_inicio.strftime('%H:%M')} — {cita.cliente.nombre_completo}",
                    nombre_ubicacion(cita.ubicacion),
                ]
                if cita.cliente.instagram:
                    partes.append(url_instagram(cita.cliente.instagram))
                lineas.append(" · ".join(partes))
            mensaje = "\n".join(lineas)

        enviado = enviar_aviso_peluquero(mensaje)
        # Sin datos personales en el log: solo fecha y número de citas.
        logger.info("Recordatorio %s: %d citas, enviado=%s", manana.isoformat(), len(citas), enviado)
        return enviado
    finally:
        if _own_session:
            db.close()
