"""
config.py · Configuración del sistema y persistencia.
Gestiona variables de entorno con validación temprana y sanitización de credenciales.
Utiliza Pydantic Settings / BaseModel para una validación estricta y tipada.
Cumple el criterio A5 de specs/01-mongodb/spec.md.
"""
import os
import re
import secrets
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


def sanitizar_mongodb_url(url: str) -> str:
    """
    Oculta usuario y contraseña de una URL de MongoDB para evitar
    exponer secretos en logs o mensajes de error (Criterio A5).
    """
    if not url:
        return ""
    # Reemplaza :password@ por :***@
    return re.sub(r":([^/@:]+)@", ":***@", url)


class Settings(BaseModel):
    """Configuraciones globales del sistema validadas con Pydantic BaseModel."""
    MONGODB_URL: str = Field(
        default_factory=lambda: os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
        description="URL de conexión a la base de datos MongoDB"
    )
    MONGODB_DB: str = Field(
        default_factory=lambda: os.getenv("MONGODB_DB", "via_biblioteca"),
        description="Nombre de la base de datos principal"
    )
    ADMIN_KEY: str = Field(
        default_factory=lambda: os.getenv("ADMIN_KEY", "admin-secret-token"),
        description="Token de autenticación de rutas de administración"
    )
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("JWT_SECRET_KEY") or secrets.token_urlsafe(48),
        description="Clave para firmar JWT; si no se define se genera una temporal por proceso"
    )
    CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv(
                "CORS_ORIGINS",
                "http://localhost:5173,http://localhost:5174,http://localhost:8000"
            ).split(",")
            if origin.strip()
        ],
        description="Lista de orígenes autorizados para CORS"
    )

    def validar_jwt(self) -> None:
        """
        Valida la clave de firma JWT sin exponerla en el mensaje de error.
        Si no se configuró, se usa una clave temporal segura (los tokens se
        invalidan al reiniciar el proceso).
        """
        if len(self.JWT_SECRET_KEY) < 32:
            raise ValueError(
                "Configuración inválida en la variable de entorno 'JWT_SECRET_KEY': "
                "debe tener al menos 32 caracteres."
            )

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
