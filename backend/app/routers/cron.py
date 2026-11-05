"""
Endpoints de tareas programadas (Vercel Cron).

Vercel Cron hace un GET a estas rutas en producción y, si la variable CRON_SECRET
existe, envía "Authorization: Bearer <CRON_SECRET>". Sin CRON_SECRET los endpoints
quedan desactivados (404). Fuera del esquema OpenAPI.
"""
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.tareas.purga import purgar
from app.tareas.recordatorio import enviar_recordatorio


def verificar_cron_secret(authorization: str | None = Header(default=None)) -> None:
    secreto = settings.cron_secret
    if not secreto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    esperado = f"Bearer {secreto}".encode()
    recibido = (authorization or "").encode()
    # Comparación en tiempo constante (no revela cuántos caracteres coinciden).
    if not hmac.compare_digest(recibido, esperado):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autorizado")


router = APIRouter(
    prefix="/cron",
    include_in_schema=False,
    dependencies=[Depends(verificar_cron_secret)],
)


@router.get("/recordatorio")
def cron_recordatorio(db: Session = Depends(get_db)):
    """Resumen de las citas de mañana al peluquero (Telegram)."""
    enviado = enviar_recordatorio(db=db)
    return {"ok": True, "enviado": enviado}


@router.get("/purga")
def cron_purga(db: Session = Depends(get_db)):
    """Purga RGPD de citas anteriores a la ventana de retención."""
    purgadas = purgar(db=db)
    return {"ok": True, "purgadas": purgadas}
