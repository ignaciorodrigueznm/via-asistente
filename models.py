"""
models.py · Modelos Pydantic para el dominio de Biblioteca Histórica (VÍA).
Define esquemas de validación estricta, restricciones, tipos y BaseModel.
"""
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, field_validator
from repository import normalizar_tags, normalizar_tag


class MetadataFragmento(BaseModel):
    """Metadatos opcionales o abiertos de un fragmento histórico."""
    extra: Dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "extra": "allow"
    }


class TagueoInfo(BaseModel):
    """Información de procedencia y control del tagueo."""
    origen: Literal["manual", "automatico", "asistido"] = Field(
        default="manual",
        description="Origen de las etiquetas del fragmento"
    )
    revisado: bool = Field(
        default=True,
        description="Indica si los tags fueron revisados humanamente"
    )


class FragmentoModel(BaseModel):
    """
    Modelo de validación con Pydantic para un fragmento histórico.
    Representa un documento en la colección 'fragmentos'.
    """
    id: str = Field(..., min_length=1, description="Identificador único del fragmento (ej: teoria_1900)")
    libro_slug: str = Field(..., min_length=1, description="Slug del libro al que pertenece")
    libro_id: Optional[str] = Field(default=None, description="Identificador o slug referencial del libro")
    orden: int = Field(default=1, ge=1, description="Orden secuencial del fragmento dentro del libro")
    seccion: str = Field(default="", description="Nombre de la sección o capítulo")
    titulo: str = Field(..., min_length=1, description="Título del fragmento")
    contenido: str = Field(..., min_length=1, description="Texto o contenido histórico del fragmento")
    tags: List[str] = Field(default_factory=list, description="Lista de tags temáticos normalizados")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")
    tagueo: TagueoInfo = Field(default_factory=TagueoInfo, description="Auditoría del etiquetado")

    @field_validator("tags", mode="before")
    @classmethod
    def normalizar_lista_tags(cls, v):
        """Asegura que los tags ingresados cumplan con la normalización estricta."""
        if isinstance(v, list):
            return normalizar_tags(v)
        return v


class LibroModel(BaseModel):
    """
    Modelo de validación con Pydantic para un libro del corpus.
    Representa un documento en la colección 'libros'.
    """
    slug: str = Field(
        ...,
        min_length=3,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="Identificador semántico URL-friendly (solo minúsculas, números y guiones)"
    )
    titulo: str = Field(..., min_length=1, max_length=255, description="Título oficial de la obra")
    autor: str = Field(default="Comunidad Historiográfica", min_length=1, description="Autor o autores")
    anio: Optional[int] = Field(default=None, ge=1500, le=2100, description="Año de publicación o referencia")
    fuente_tipo: Literal["primaria", "secundaria", "terciaria", "otra"] = Field(
        default="secundaria",
        description="Clasificación de la fuente histórica"
    )
    estado: Literal["borrador", "publicado", "archivado"] = Field(
        default="borrador",
        description="Estado de publicación del libro"
    )
    resumen: str = Field(default="", description="Síntesis o abstract del libro")
    temas: List[str] = Field(default_factory=list, description="Temas principales normalizados")
    hash_texto: Optional[str] = Field(default=None, description="Hash SHA-256 de integridad del texto")
    creado: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Fecha y hora de registro (UTC)"
    )

    @field_validator("temas", mode="before")
    @classmethod
    def normalizar_lista_temas(cls, v):
        """Asegura que los temas se normalicen con la misma regla de tags."""
        if isinstance(v, list):
            return normalizar_tags(v)
        return v


class DetalleLibroResponse(BaseModel):
    """Respuesta estructurada para GET /api/libros/{slug}."""
    libro: LibroModel
    fragmentos: List[FragmentoModel]


class MetaCorpusModel(BaseModel):
    """Documento de control y versión del corpus en la colección 'meta'."""
    id: Literal["corpus"] = Field(default="corpus", alias="_id")
    version: int = Field(default=1, ge=1, description="Contador monótono de versión")

    model_config = {
        "populate_by_name": True
    }

