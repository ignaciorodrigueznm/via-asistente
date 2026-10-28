"""
tests/test_api_libros.py · Pruebas de integración de los endpoints /api/libros y /api/fundacion
utilizando TestClient de Starlette con repositorio en memoria.
"""
import pytest
from starlette.testclient import TestClient
import web_server
from repository import FakeRepo


@pytest.fixture
def test_app():
    fake = FakeRepo()
    # Sembrar un libro publicado y un libro borrador
    fake.guardar_libro({
        "slug": "fundacion-las-varillas",
        "titulo": "Origen y Fundación de Las Varillas",
        "autor": "Comunidad Historiográfica",
        "anio": 1900,
        "fuente_tipo": "secundaria",
        "estado": "publicado",
        "resumen": "Resumen fundacional",
        "temas": ["fundacion"]
    })
    fake.guardar_fragmentos("fundacion-las-varillas", [
        {
            "id": "teoria_1900",
            "titulo": "1900 Ferrocarril",
            "contenido": "Llegada del tren",
            "tags": ["ferrocarril"],
            "metadata": {}
        }
    ])
    fake.guardar_libro({
        "slug": "libro-borrador",
        "titulo": "Libro Oculto",
        "estado": "borrador"
    })

    # Inyectar el repositorio en el backend
    web_server.book_repo = fake
    client = TestClient(web_server.app)
    return client


def test_get_api_libros_catalogo_solo_publicados(test_app):
    """Verifica que GET /api/libros devuelve únicamente los libros en estado 'publicado'."""
    response = test_app.get("/api/libros")
    assert response.status_code == 200
    libros = response.json()
    assert len(libros) == 1
    assert libros[0]["slug"] == "fundacion-las-varillas"
    assert "libro-borrador" not in [l["slug"] for l in libros]


def test_get_api_libros_slug_detalle(test_app):
    """Verifica que GET /api/libros/{slug} devuelve el libro y sus fragmentos."""
    response = test_app.get("/api/libros/fundacion-las-varillas")
    assert response.status_code == 200
    data = response.json()
    assert "libro" in data
    assert "fragmentos" in data
    assert len(data["fragmentos"]) == 1
    assert data["fragmentos"][0]["id"] == "teoria_1900"


def test_get_api_libros_slug_inexistente_o_borrador(test_app):
    """Verifica que un slug inexistente o en borrador responde 404 en el endpoint público."""
    res_inexistente = test_app.get("/api/libros/no-existe")
    assert res_inexistente.status_code == 404

    res_borrador = test_app.get("/api/libros/libro-borrador")
    assert res_borrador.status_code == 404


def test_get_api_fundacion_compatibilidad(test_app):
    """Verifica que GET /api/fundacion sigue funcionando retornando 'raw' y 'full_text'."""
    response = test_app.get("/api/fundacion")
    assert response.status_code == 200
    data = response.json()
    assert "raw" in data
    assert "full_text" in data
