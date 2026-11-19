"""
tests/test_ingesta.py · Pruebas unitarias para el fragmentador semántico (ingesta pura).
Cumple el criterio de aceptación B6 de specs/02-carga-por-partes/spec.md.
"""
import pytest
from ingesta import fragmentar_texto, limpiar_texto


def test_limpiar_texto_elimina_bom_y_normaliza_saltos():
    texto_con_bom = "\ufeffCapítulo 1\r\n\r\nEste es el contenido.\r\n"
    limpio = limpiar_texto(texto_con_bom)
    assert not limpio.startswith("\ufeff")
    assert "\r" not in limpio
    assert limpio.startswith("Capítulo 1")


def test_fragmentar_texto_genera_ids_correctos():
    texto = (
        "# Origen del Pueblo\n\n"
        + "Párrafo extenso con suficiente contenido para generar un bloque válido. " * 15
        + "\n\n# Segunda Parte\n\n"
        + "Otro párrafo sustancial que forma la segunda sección del libro. " * 15
    )
    fragmentos = fragmentar_texto("mi-libro", texto, min_chars=200, max_chars=800)
    assert len(fragmentos) >= 2
    assert fragmentos[0]["id"] == "mi-libro_01"
    assert fragmentos[0]["orden"] == 1
    assert fragmentos[0]["libro_slug"] == "mi-libro"
    assert fragmentos[1]["id"] == "mi-libro_02"
    assert fragmentos[1]["orden"] == 2


def test_fragmentar_respeta_titulos_markdown():
    texto = (
        "# Capítulo I: Los Inicios\n\n"
        + "Detalles iniciales del capítulo I. " * 20
        + "\n\n## Sección 1.1: El Ferrocarril\n\n"
        + "Detalles específicos sobre la llegada del tren a la localidad. " * 20
    )
    fragmentos = fragmentar_texto("libro-ferro", texto, min_chars=200, max_chars=900)
    assert len(fragmentos) >= 2
    # El primer fragmento debe tener la sección Capítulo I
    assert "Capítulo I" in fragmentos[0]["seccion"] or "Capítulo I" in fragmentos[0]["titulo"]
    # El segundo fragmento debe reconocer el subtítulo
    titulos = [f["titulo"] for f in fragmentos]
    assert any("Sección 1.1" in t for t in titulos)


def test_fragmentar_no_corta_frases():
    # Una frase nunca debe terminar partida sin punto ni signo de cierre
    texto = (
        "# Sección Única\n\n"
        + "Primera oración completa. Segunda oración también completa. Tercera oración con datos importantes. " * 12
    )
    fragmentos = fragmentar_texto("libro-frases", texto, min_chars=300, max_chars=600)
    for f in fragmentos:
        contenido = f["contenido"].strip()
        # Debe terminar en signo de puntuación (., !, ?, etc.)
        assert contenido[-1] in ".!?\"'»"


def test_fragmentar_une_fragmentos_demasiado_cortos():
    texto = (
        "# Título Principal\n\n"
        + "Párrafo normal de introducción con extensión adecuada. " * 10
        + "\n\nPárrafo diminuto.\n\n"
        + "Párrafo siguiente que complementa al anterior con buen detalle. " * 10
    )
    fragmentos = fragmentar_texto("libro-cortos", texto, min_chars=500, max_chars=1500)
    # Ningún fragmento debe quedar con solo "Párrafo diminuto." aislado
    for f in fragmentos:
        if "Párrafo diminuto." in f["contenido"]:
            assert len(f["contenido"]) >= 200
