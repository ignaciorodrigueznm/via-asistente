"""
tests/test_tagger.py · Pruebas unitarias para el protocolo Tagger y ManualTagger.
Cumple el criterio de aceptación B7 de specs/02-carga-por-partes/spec.md y sección 5.2.
"""
import pytest
from tagger import Tagger, ManualTagger, aplicar_tagger_seguro


class TaggerQueFalla:
    """Simula un tagger defectuoso o con timeout que lanza excepción."""
    def sugerir(self, fragmento: dict, libro: dict) -> dict:
        raise RuntimeError("Error de conexión con el modelo de tagueo")


class TaggerExitoso:
    """Simula un tagger que sugiere tags y título."""
    def sugerir(self, fragmento: dict, libro: dict) -> dict:
        return {
            "titulo": "Título Sugerido",
            "tags": ["ferrocarril", "historia"],
            "metadata": {"confianza": 0.95}
        }


def test_manual_tagger_cumple_protocolo():
    tagger = ManualTagger()
    assert isinstance(tagger, Tagger)


def test_manual_tagger_no_modifica_tags():
    tagger = ManualTagger()
    fragmento = {"id": "libro_01", "contenido": "Texto...", "tags": []}
    res = tagger.sugerir(fragmento, {"titulo": "Libro"})
    assert res.get("tags") == []


def test_criterio_b7_tagger_que_falla_no_bloquea_y_genera_aviso():
    """
    Criterio B7: Dado un Tagger que falla, cuando termina la carga,
    entonces los fragmentos quedan sin tags y con un aviso, y la carga no se cancela.
    """
    tagger_roto = TaggerQueFalla()
    fragmentos = [
        {"id": "libro_01", "contenido": "Texto 1", "tags": []},
        {"id": "libro_02", "contenido": "Texto 2", "tags": []}
    ]
    libro = {"slug": "mi-libro", "titulo": "Mi Libro"}

    fragmentos_procesados, avisos = aplicar_tagger_seguro(tagger_roto, fragmentos, libro)

    assert len(fragmentos_procesados) == 2
    assert fragmentos_procesados[0]["tags"] == []
    assert fragmentos_procesados[1]["tags"] == []
    assert len(avisos) > 0
    assert "Error" in avisos[0] or "falló" in avisos[0].lower()


def test_tagger_exitoso_asigna_tags_como_no_revisados():
    tagger = TaggerExitoso()
    fragmentos = [{"id": "libro_01", "contenido": "Texto 1", "tags": []}]
    libro = {"slug": "mi-libro", "titulo": "Mi Libro"}

    fragmentos_procesados, avisos = aplicar_tagger_seguro(tagger, fragmentos, libro)
    assert len(avisos) == 0
    assert fragmentos_procesados[0]["tags"] == ["ferrocarril", "historia"]
    assert fragmentos_procesados[0]["tagueo"]["revisado"] is False
