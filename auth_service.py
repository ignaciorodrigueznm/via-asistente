"""
auth_service.py · Servicios criptográficos y tokens JWT para VÍA.
Maneja hash de contraseñas con bcrypt y generación/verificación de tokens JWT.
"""
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
import bcrypt
import jwt

# Clave secreta para firma de JWT (por defecto se lee de .env)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "via_secret_jwt_key_2026_super_secure")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 7 días de validez


def hashear_password(password: str) -> str:
    """Hashea una contraseña utilizando bcrypt con salt automático."""
    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = bcrypt.gensalt(rounds=12)
    hashed_bytes = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed_bytes.decode("utf-8")


def verificar_password(password: str, hashed_password: str) -> bool:
    """Verifica si la contraseña coincide con el hash almacenado."""
    if not password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def crear_token_jwt(datos_usuario: Dict[str, Any], expira_horas: int = JWT_EXPIRATION_HOURS) -> str:
    """Genera un token JWT firmado con los datos del usuario y fecha de expiración."""
    payload = dict(datos_usuario)
    expiracion = datetime.now(timezone.utc) + timedelta(hours=expira_horas)
    payload["exp"] = expiracion
    payload["iat"] = datetime.now(timezone.utc)
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


def decodificar_token_jwt(token: str) -> Optional[Dict[str, Any]]:
    """Decodifica y valida la firma y expiración de un token JWT."""
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception):
        return None
