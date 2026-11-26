"""
tests/test_api_libros.py · Pruebas de integración de los endpoints GET utilizando TestClient de Starlette.
Cubre la suite de 5 pruebas GET según el plan de testing del proyecto:
  1. GET /api/libros -> Catálogo con solo libros publicados (200).
  2. GET /api/libros/{slug} -> Detalle y fragmentos de un libro publicado (200).
  3. GET /api/libros/{slug} -> 404 para slug inexistente o libro en borrador.
  4. GET /api/fundacion -> Compatibilidad histórica (200, 'raw' y 'full_text').
  5. GET /api/status -> Estado de salud del sistema, modelo y servidor MCP (200).
"""
import pytest
from starlette.testclient import TestClient
import web_server
from repository import FakeRepo
from models import LibroModel, FragmentoModel, DetalleLibroResponse


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


# --- 1. GET /api/libros ---
def test_get_api_libros_catalogo_solo_publicados(test_app):
    """GET 1: Verifica que /api/libros devuelve únicamente los libros en estado 'publicado' y valida con Pydantic."""
    response = test_app.get("/api/libros")
    assert response.status_code == 200
    libros = response.json()
    assert len(libros) == 1
    assert libros[0]["slug"] == "fundacion-las-varillas"
    assert "libro-borrador" not in [l["slug"] for l in libros]

    # Validación Pydantic del schema recibido
    libros_pydantic = [LibroModel.model_validate(l) for l in libros]
    assert libros_pydantic[0].estado == "publicado"


# --- 2. GET /api/libros/{slug} existente ---
def test_get_api_libros_slug_detalle(test_app):
    """GET 2: Verifica que /api/libros/{slug} devuelve el libro y sus fragmentos con DetalleLibroResponse."""
    response = test_app.get("/api/libros/fundacion-las-varillas")
    assert response.status_code == 200
    data = response.json()
    
    # Validar estructura con BaseModel
    detalle = DetalleLibroResponse.model_validate(data)
    assert detalle.libro.slug == "fundacion-las-varillas"
    assert len(detalle.fragmentos) == 1
    assert detalle.fragmentos[0].id == "teoria_1900"
    assert detalle.fragmentos[0].tags == ["ferrocarril"]


# --- 3. GET /api/libros/{slug} 404 ---
def test_get_api_libros_slug_inexistente_o_borrador(test_app):
    """GET 3: Verifica que un slug inexistente o en borrador responde 404 en el endpoint público."""
    res_inexistente = test_app.get("/api/libros/no-existe")
    assert res_inexistente.status_code == 404
    assert "error" in res_inexistente.json()

    res_borrador = test_app.get("/api/libros/libro-borrador")
    assert res_borrador.status_code == 404
    assert "error" in res_borrador.json()


# --- 4. GET /api/fundacion ---
def test_get_api_fundacion_compatibilidad(test_app):
    """GET 4: Verifica que /api/fundacion sigue funcionando retornando 'raw' y 'full_text'."""
    response = test_app.get("/api/fundacion")
    assert response.status_code == 200
    data = response.json()
    assert "raw" in data
    assert "full_text" in data
    assert isinstance(data["raw"], list)
    assert len(data["raw"]) > 0


# --- 5. GET /api/status ---
def test_get_api_status_salud(test_app):
    """GET 5: Verifica que /api/status responde 200 con el estado del servidor, modelo y MCP."""
    response = test_app.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
    assert "mcp" in data
    assert "ollama" in data
    assert "tools" in data["mcp"]
    assert "default_model" in data["ollama"]


# --- 6. GET /api/fundacion?id=... ---
def test_get_api_fundacion_por_id(test_app):
    """GET 6: /api/fundacion?id= devuelve un array con el fragmento exacto del repositorio."""
    response = test_app.get("/api/fundacion", params={"id": "teoria_1900"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "teoria_1900"


# --- 7. GET /api/fundacion?all=true ---
def test_get_api_fundacion_all(test_app):
    """GET 7: /api/fundacion?all=true devuelve todas las secciones completas."""
    response = test_app.get("/api/fundacion", params={"all": "true"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "teoria_1900"


# --- 8. GET /api/libros con repositorio vacío ---
def test_get_api_libros_repo_vacio_devuelve_default():
    """GET 8: /api/libros sin datos persistidos responde con el libro fundacional por defecto."""
    web_server.book_repo = FakeRepo()
    client = TestClient(web_server.app)
    response = client.get("/api/libros")
    assert response.status_code == 200
    libros = response.json()
    assert len(libros) == 1
    assert libros[0]["slug"] == "fundacion-las-varillas"
    assert libros[0]["estado"] == "publicado"

    # El detalle también cae al JSON fundacional cuando el repositorio está vacío.
    detalle = client.get("/api/libros/fundacion-las-varillas")
    assert detalle.status_code == 200
    assert detalle.json()["libro"]["slug"] == "fundacion-las-varillas"
    assert len(detalle.json()["fragmentos"]) > 0
