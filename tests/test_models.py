"""
tests/test_models.py · Pruebas unitarias de esquemas y validaciones Pydantic.
Verifica campos obligatorios, restricciones de tipos, regex, rangos, normalización
automática de tags y BaseModel según los requerimientos.
"""
import pytest
from pydantic import ValidationError
from models import LibroModel, FragmentoModel, DetalleLibroResponse, MetaCorpusModel


def test_libro_model_campos_validos_y_restricciones():
    """Valida creación exitosa de LibroModel con restricciones correctas."""
    libro = LibroModel(
        slug="libro-historia-1900",
        titulo="Historia de Las Varillas",
        autor="Autor Vía",
        anio=1904,
        fuente_tipo="secundaria",
        estado="publicado",
        resumen="Un resumen histórico",
        temas=["Ferrocarril", "  ferrocarril ", "Estación"]
    )
    assert libro.slug == "libro-historia-1900"
    assert libro.anio == 1904
    assert libro.estado == "publicado"
    # Normalización automática en temas
    assert libro.temas == ["ferrocarril", "estacion"]


def test_libro_model_restriccion_slug_invalido():
    """Valida que un slug con mayúsculas, espacios o caracteres raros sea rechazado."""
    with pytest.raises(ValidationError):
        LibroModel(
            slug="Slug Invalido!",
            titulo="Título Válido"
        )


def test_libro_model_restriccion_anio_fuera_de_rango():
    """Valida que un año fuera del rango (1500-2100) sea rechazado."""
    with pytest.raises(ValidationError):
        LibroModel(
            slug="libro-valido",
            titulo="Título",
            anio=1200  # < 1500
        )

    with pytest.raises(ValidationError):
        LibroModel(
            slug="libro-valido",
            titulo="Título",
            anio=2200  # > 2100
        )


def test_libro_model_restriccion_estado_invalido():
    """Valida que solo se admitan estados de la enumeración/literal."""
    with pytest.raises(ValidationError):
        LibroModel(
            slug="libro-valido",
            titulo="Título",
            estado="invalido_estado"
        )


def test_fragmento_model_validacion_y_normalizacion_tags():
    """Valida FragmentoModel con orden >= 1 y normalización de tags."""
    frag = FragmentoModel(
        id="frag_01",
        libro_slug="fundacion-las-varillas",
        orden=1,
        titulo="Llegada del tren",
        contenido="En 1900...",
        tags=["Ferrocarril", "  ferrocarril  ", "Estación"]
    )
    assert frag.id == "frag_01"
    assert frag.tags == ["ferrocarril", "estacion"]
    assert frag.tagueo.origen == "manual"
    assert frag.tagueo.revisado is True


def test_fragmento_model_restriccion_orden_invalido():
    """Valida que el orden ge=1 no admita 0 o números negativos."""
    with pytest.raises(ValidationError):
        FragmentoModel(
            id="frag_01",
            libro_slug="fundacion-las-varillas",
            orden=0,  # ge=1 requerido
            titulo="Título",
            contenido="Contenido"
        )


def test_detalle_libro_response_composicion():
    """Valida que DetalleLibroResponse componga libro y fragmentos en BaseModel."""
    detalle = DetalleLibroResponse(
        libro=LibroModel(
            slug="fundacion-las-varillas",
            titulo="Origen y Fundación"
        ),
        fragmentos=[
            FragmentoModel(
                id="f1",
                libro_slug="fundacion-las-varillas",
                titulo="T1",
                contenido="C1"
            )
        ]
    )
    dumped = detalle.model_dump()
    assert dumped["libro"]["slug"] == "fundacion-las-varillas"
    assert len(dumped["fragmentos"]) == 1
    assert dumped["fragmentos"][0]["id"] == "f1"


def test_meta_corpus_model():
    """Valida el esquema de control de versión del corpus."""
    meta = MetaCorpusModel(version=3)
    assert meta.id == "corpus"
    assert meta.version == 3

    with pytest.raises(ValidationError):
        MetaCorpusModel(version=0)  # ge=1

