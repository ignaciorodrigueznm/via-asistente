"""
config.py · Configuración del sistema y persistencia.
Gestiona variables de entorno con validación temprana y sanitización de credenciales.
Cumple el criterio A5 de specs/01-mongodb/spec.md.
"""
import os
import re
from typing import List, Optional
from urllib.parse import urlparse


def sanitizar_mongodb_url(url: str) -> str:
    """
    Oculta usuario y contraseña de una URL de MongoDB para evitar
    exponer secretos en logs o mensajes de error (Criterio A5).
    """
    if not url:
        return ""
    # Reemplaza :password@ por :***@
    return re.sub(r":([^/@:]+)@", ":***@", url)


class Settings:
    """Configuraciones globales validadas."""

    def __init__(self):
        self.MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.MONGODB_DB: str = os.getenv("MONGODB_DB", "via_biblioteca")
        self.ADMIN_KEY: str = os.getenv("ADMIN_KEY", "admin-secret-token")
        
        # CORS_ORIGINS
        cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:8000")
        self.CORS_ORIGINS: List[str] = [origin.strip() for origin in cors_raw.split(",") if origin.strip()]

    def validar_mongo(self) -> None:
        """
        Valida que la variable MONGODB_URL tenga un formato válido.
        Si es inválida, lanza ValueError indicando la variable a revisar
        sin exponer contraseñas (Criterio A5).
        """
        if not self.MONGODB_URL or not (
            self.MONGODB_URL.startswith("mongodb://") or self.MONGODB_URL.startswith("mongodb+srv://")
        ):
            url_oculta = sanitizar_mongodb_url(self.MONGODB_URL)
            raise ValueError(
                f"Configuración inválida en la variable de entorno 'MONGODB_URL': '{url_oculta}'. "
                "Debe comenzar con 'mongodb://' o 'mongodb+srv://'."
            )


settings = Settings()
