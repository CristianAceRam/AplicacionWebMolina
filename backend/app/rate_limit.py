import ipaddress

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Cabeceras que pone el edge de Vercel, por orden de preferencia.
# Vercel SOBRESCRIBE x-forwarded-for / x-real-ip con la IP real del cliente
# (anti-spoofing) y x-vercel-forwarded-for es la suya propia, que no puede
# pisar un proxy situado delante. Requiere Cloudflare en modo "DNS only".
_CABECERAS_VERCEL = ("x-vercel-forwarded-for", "x-real-ip", "x-forwarded-for")


def _primera_ip_valida(valor: str | None) -> str | None:
    """Primer elemento de una lista 'ip1, ip2, ...' si es una IP válida."""
    if not valor:
        return None
    candidata = valor.split(",")[0].strip()
    try:
        return str(ipaddress.ip_address(candidata))
    except ValueError:
        return None


def get_real_ip(request: Request) -> str:
    """
    IP del cliente para el rate limiting, según la plataforma:

    - Vercel (VERCEL=1, lo define la plataforma): cabeceras del edge de Vercel,
      que el cliente no puede falsificar. Sin esto, todos los usuarios podrían
      compartir el mismo límite (la IP de la conexión sería la del proxy).
    - Render (RENDER=true): comportamiento histórico, primer valor de X-Forwarded-For.
    - Resto (local, tests): IP de la conexión. Las cabeceras de proxy se ignoran
      porque sin un proxy de confianza delante cualquiera puede falsificarlas.
    """
    if settings.vercel:
        for cabecera in _CABECERAS_VERCEL:
            ip = _primera_ip_valida(request.headers.get(cabecera))
            if ip:
                return ip
    elif settings.render:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=get_real_ip, default_limits=["100/minute"])
