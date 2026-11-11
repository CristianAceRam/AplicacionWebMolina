from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings
from app.models import Rol


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ValueError:
        # > 72 bytes (bcrypt 5) o hash no bcrypt (cuenta anonimizada)
        return False


def create_access_token(user_id: int, rol: str, version: int = 0) -> str:
    """JWT con la versión de sesión del usuario ("ver"). Admin: 12 h; cliente: 7 días."""
    minutos = (
        settings.admin_token_expire_minutes if rol == Rol.admin
        else settings.access_token_expire_minutes
    )
    payload = {
        "sub": str(user_id),
        "rol": rol,
        "ver": version,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=minutos),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decodifica y valida el JWT. Lanza jwt.InvalidTokenError si es inválido o ha caducado."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
