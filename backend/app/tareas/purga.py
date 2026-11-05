"""
Purga RGPD: borra citas (y sus franjas) anteriores a la ventana de retención.

Se ejecuta una vez al día (Vercel Cron → GET /cron/purga, o por CLI con
scripts/purga_citas.py [--dry-run]). Es idempotente: ejecutarla varias veces
tiene el mismo efecto que ejecutarla una. RETENCION_MESES (por defecto 24)
controla la ventana.
"""
import calendar
import logging
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Cita, FranjaOcupada

logger = logging.getLogger(__name__)

_MADRID = ZoneInfo("Europe/Madrid")


def _fecha_limite(retencion_meses: int | None = None, hoy: date | None = None) -> date:
    """
    Devuelve hoy (Europe/Madrid) menos la ventana de retención en meses.
    Si el día no existe en el mes destino (p. ej. 29-feb → año no bisiesto,
    o 31 → mes de 30 días), se usa el último día de ese mes.
    """
    meses = retencion_meses if retencion_meses is not None else settings.retencion_meses
    hoy = hoy if hoy is not None else datetime.now(_MADRID).date()
    total = hoy.year * 12 + (hoy.month - 1) - meses
    anio, mes = divmod(total, 12)
    mes += 1
    dia = min(hoy.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def purgar(dry_run: bool = False, db: Session | None = None, _limite: date | None = None) -> int:
    """
    Borra citas cuya fecha sea anterior a la ventana de retención junto con sus FranjaOcupada.

    Args:
        dry_run: Si True, solo cuenta sin borrar nada.
        db:      Sesión SQLAlchemy externa (endpoint / tests). Si None, crea una propia.
        _limite: Fecha límite explícita (usada en tests). Si None, usa _fecha_limite().

    Returns:
        Número de citas que se habrían borrado (dry_run=True) o que se borraron (dry_run=False).
    """
    limite = _limite if _limite is not None else _fecha_limite()

    _own_session = db is None
    if _own_session:
        db = SessionLocal()
    try:
        ids = [r[0] for r in db.query(Cita.id).filter(Cita.fecha < limite).all()]

        if not ids:
            logger.info("Purga: nada que purgar (límite %s).", limite.isoformat())
            return 0

        if dry_run:
            logger.info("Purga [dry-run]: se borrarían %d citas anteriores a %s.", len(ids), limite.isoformat())
            return len(ids)

        db.execute(delete(FranjaOcupada).where(FranjaOcupada.cita_id.in_(ids)))
        db.execute(delete(Cita).where(Cita.id.in_(ids)))
        db.commit()
        logger.info("Purga: borradas %d citas anteriores a %s.", len(ids), limite.isoformat())
        return len(ids)
    finally:
        if _own_session:
            db.close()
