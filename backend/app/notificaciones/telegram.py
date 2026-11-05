import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# En serverless el aviso se envía de forma síncrona dentro de la petición:
# un timeout corto acota lo que puede retrasar la respuesta si Telegram no contesta.
TELEGRAM_TIMEOUT_SEGUNDOS = 3.0


def enviar_aviso_peluquero(mensaje: str) -> bool:
    """
    Envía un mensaje al peluquero por Telegram. Nunca lanza excepciones.

    Returns:
        True si Telegram confirmó la entrega; False si no está configurado o falló.
    """
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        logger.warning(
            "Telegram no configurado (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes) — aviso omitido."
        )
        return False
    try:
        respuesta = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": mensaje},
            timeout=TELEGRAM_TIMEOUT_SEGUNDOS,
        )
    except Exception as exc:
        # Solo el tipo: el texto de la excepción de httpx puede incluir la URL con el token.
        logger.warning(
            "Fallo al enviar aviso Telegram (%s) — la operación principal no se ve afectada.",
            type(exc).__name__,
        )
        return False
    if not respuesta.is_success:
        logger.warning("Telegram respondió %s — aviso no entregado.", respuesta.status_code)
        return False
    return True
