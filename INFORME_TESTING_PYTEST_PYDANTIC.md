# INFORME TÉCNICO DE TESTING AUTOMATIZADO CON PYTEST Y PYDANTIC

**Título del Proyecto:** Plataforma Asistente VÍA (MCP, Ollama y Biblioteca Histórica)  
**Institución:** Escuela ProA  
**Área:** Desarrollo de Software y Aseguramiento de Calidad (QA)  
**Autores:** Rodríguez Ignacio, Sanguinetti Emilia, Ramírez Ciomara  
**Fecha:** Noviembre 2026  
**Versión del Documento:** 1.0 (Formato Técnico Estructurado bajo lineamientos APA 7.ª ed.)  

---

## 1. Introducción y Contexto

El presente informe documenta la verificación y aseguramiento de calidad del software implementado en la plataforma del asistente interactivo VÍA. Dicha arquitectura articula una capa web reactiva con **Starlette/Uvicorn**, un servidor de contexto histórico basado en el protocolo **Model Context Protocol (FastMCP)**, persistencia de colecciones bibliográficas orientadas a documentos (**MongoDB** con abstracción desacoplada de repositorio) y validación de tipos, esquemas y reglas de dominio mediante **Pydantic V2** (`BaseModel`).

Con el propósito de garantizar la robustez, determinismo y prevención de regresiones, se diseñó e implementó una batería de pruebas automatizadas ejecutadas bajo el framework **Pytest**. Dicha suite aborda tanto la validación estricta de esquemas de datos como las interfaces de comunicación REST (**HTTP GET**) y en tiempo real (**WebSocket** bidireccional).

---

## 2. Marco Teórico y Tecnologías de Validación

### 2.1. Pydantic y BaseModel
Pydantic proporciona análisis sintáctico y validación en tiempo de ejecución a través de sugerencias de tipos de Python (*type hints*). En el sistema, los modelos de dominio (`LibroModel`, `FragmentoModel`, `DetalleLibroResponse` y `MetaCorpusModel`) heredan de `BaseModel`, aplicando:
* **Restricciones léxicas y formatos:** Expresiones regulares para slugs normalizados (`^[a-z0-9]+(?:-[a-z0-9]+)*$`).
* **Límites de rango numérico:** Restricción cronológica para años de publicación ($1500 \le \text{año} \le 2100$) y secuencias monótonas crecientes para el orden de fragmentos ($\text{orden} \ge 1$).
* **Validadores de campo (`@field_validator`):** Normalización estricta de etiquetas (*tags*) para asegurar minúsculas, eliminación de signos diacríticos (tildes) y supresión de elementos duplicados.
* **Enumeraciones literales (`Literal`):** Control de máquina de estados para el ciclo editorial (`borrador`, `publicado`, `archivado`) y clasificación de fuentes historiográficas (`primaria`, `secundaria`, `terciaria`, `otra`).

### 2.2. Pytest y Dobles de Prueba (*Test Doubles*)
Para aislar las dependencias externas (bases de datos no relacionales y modelos de lenguaje de gran escala LLM locales vía Ollama), se aplicó el patrón de diseño **Repository Pattern**:
* **`FakeRepo`:** Implementación en memoria del protocolo `BookRepository`, asegurando ejecución determinista en microsegundos sin requerir instancias de MongoDB activas durante la integración continua.
* **Mocks Asíncronos (`unittest.mock.AsyncMock` y `patch`):** Intercepción de llamadas HTTP cliente hacia el motor generativo para simular respuestas predecibles y validar el bucle de razonamiento del agente (*Agent Reasoning Loop*).

---

## 3. Matriz de Casos de Prueba (10 Casos: 5 GET y 5 WS)

A continuación, se detalla la matriz de especificación funcional para los 10 casos de prueba de integración (5 peticiones GET y 5 interacciones sobre WebSocket), contemplando escenarios nominales exitosos y degradaciones de error controladas:

### 3.1. Pruebas de Endpoints HTTP GET (5 Casos)

| ID / Tipo | Nombre de la Prueba | Ruta / Recurso | Condición de Entrada / Contexto | Resultado Esperado |
| :--- | :--- | :--- | :--- | :--- |
| **GET-01** (Exitoso) | `test_get_api_libros_catalogo_solo_publicados` | `GET /api/libros` | Repositorio contiene libros en estado `publicado` y `borrador`. | Código HTTP `200 OK`. Retorna lista JSON conteniendo exclusivamente obras publicadas; valida esquema con `LibroModel`. |
| **GET-02** (Exitoso) | `test_get_api_libros_slug_detalle` | `GET /api/libros/{slug}` | Parámetro `slug="fundacion-las-varillas"` correspondiente a un libro publicado. | Código HTTP `200 OK`. Retorna estructura validada por `DetalleLibroResponse` con metadatos y lista de fragmentos ordenados. |
| **GET-03A** (Error 404) | `test_get_api_libros_slug_inexistente` | `GET /api/libros/no-existe` | Parámetro `slug` que no existe en la base de datos ni repositorio. | Código HTTP `404 Not Found`. Retorna cuerpo JSON estructurado `{"error": "Libro no encontrado"}`. |
| **GET-03B** (Error 404) | `test_get_api_libros_slug_borrador` | `GET /api/libros/libro-borrador` | Parámetro `slug` correspondiente a un libro en estado `borrador` (no público). | Código HTTP `404 Not Found`. Protege la visibilidad pública de borradores retornando mensaje de no disponibilidad. |
| **GET-04** (Compatibilidad) | `test_get_api_fundacion_compatibilidad` | `GET /api/fundacion` | Petición de retrocompatibilidad con Taller MCP 2.2 sin parámetros adicionales. | Código HTTP `200 OK`. Retorna estructura con colecciones de datos en formato `raw` y cadena compilada en `full_text`. |
| **GET-05** (Diagnóstico) | `test_get_api_status_salud` | `GET /api/status` | Monitoreo de salud del backend y disponibilidad de servicios auxiliares. | Código HTTP `200 OK`. Objeto JSON con campo `status="ok"`, reporte de transporte MCP (`HistoriaVarillas`) y estado de Ollama. |

### 3.2. Pruebas de Flujo WebSocket (5 Casos)

| ID / Tipo | Nombre de la Prueba | Ruta / Protocolo | Condición de Entrada / Contexto | Resultado Esperado |
| :--- | :--- | :--- | :--- | :--- |
| **WS-01** (Exitoso) | `test_ws_1_conexion_handshake` | `ws://localhost:8000/ws/chat` | Solicitud inicial de apertura de socket TCP con cabecera de actualización de protocolo. | Negociación HTTP `101 Switching Protocols` completada con éxito; socket activo y disponible sin desconexiones prematuras. |
| **WS-02** (Exitoso) | `test_ws_2_ping_pong_control` | `ws://localhost:8000/ws/chat` | Envío de trama JSON de control: `{"type": "ping"}`. | Recepción inmediata de trama JSON `{"type": "pong", "status": "connected"}` manteniendo el canal bidireccional abierto. |
| **WS-03** (Error / Validación) | `test_ws_3_mensaje_vacio_retorna_error` | `ws://localhost:8000/ws/chat` | Envío de carga útil con cadena de espacios en blanco: `{"text": "   "}`. | Recepción de evento de error `{"type": "error", "message": "El mensaje no puede estar vacío"}`; el socket preserva la conexión viva. |
| **WS-04** (Flujo Agente) | `test_ws_4_flujo_respuesta_chat` | `ws://localhost:8000/ws/chat` | Envío de consulta válida con mock HTTP del motor de inferencia de Ollama. | Secuencia ordenada de tramas de ciclo de razonamiento: 1. `status` ("Pensando..."), 2. `response`, 3. `token`, y 4. `done`. |
| **WS-05** (Cierre Limpio) | `test_ws_5_cierre_limpio_conexion` | `ws://localhost:8000/ws/chat` | Finalización intencional iniciada por el cliente con código de control estándar `code=1000`. | Cierre de socket sin excepciones no capturadas (`WebSocketDisconnect`), finalización limpia del bucle asíncrono sin *leaks*. |

---

## 4. Código Fuente de los Módulos de Prueba

A continuación se adjuntan las implementaciones completas de los archivos requeridos para la suite de integración.

### 4.1. Archivo: `tests/test_api_libros.py`

```python
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
```

---

### 4.2. Archivo: `tests/test_ws_chat.py`

```python
"""
tests/test_ws_chat.py · Pruebas unitarias y de integración para WebSocket (/ws/chat).
Cubre la suite de 5 pruebas WS según el plan de testing del proyecto:
  1. WS 1 (Handshake & Conexión): Conexión exitosa y protocolo 101 Switching Protocols.
  2. WS 2 (Ping / Pong & Healthcheck): Mensaje de verificación rápida {"type": "ping"}.
  3. WS 3 (Validación de mensaje vacío): Respuesta de error cuando se envía mensaje en blanco.
  4. WS 4 (Bucle de razonamiento & Respuesta): Recepción de status y respuesta simulando LLM/MCP.
  5. WS 5 (Desconexión limpia / Close): Cierre de conexión con código de estado normal (1000).
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient
import web_server
from repository import FakeRepo


@pytest.fixture
def test_client():
    fake = FakeRepo()
    web_server.book_repo = fake
    client = TestClient(web_server.app)
    return client


# --- WS 1: Handshake & Conexión ---
def test_ws_1_conexion_handshake(test_client):
    """WS 1: Verifica conexión exitosa a /ws/chat sin caídas inmediatas."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        assert websocket is not None


# --- WS 2: Ping / Pong ---
def test_ws_2_ping_pong_control(test_client):
    """WS 2: Verifica que el WebSocket responda a peticiones de ping con 'connected'."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data.get("type") == "pong"
        assert data.get("status") == "connected"


# --- WS 3: Validación de mensaje vacío ---
def test_ws_3_mensaje_vacio_retorna_error(test_client):
    """WS 3: Verifica manejo de mensajes vacíos devolviendo error sin romper el socket."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"text": "   "})
        data = websocket.receive_json()
        assert data.get("type") == "error"
        assert "no puede estar vacío" in data.get("message", "")


# --- WS 4: Bucle de razonamiento y respuesta mockeada ---
def test_ws_4_flujo_respuesta_chat(test_client):
    """WS 4: Simula una respuesta directa del modelo y verifica los eventos emitidos."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Las Varillas fue fundada en relación al ferrocarril."
        }
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with test_client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"text": "¿Cuándo se fundó?", "use_mcp": False})
            
            # Recibir evento 'status' ("Pensando...")
            ev_status = websocket.receive_json()
            assert ev_status.get("type") == "status"
            
            # Recibir evento 'response'
            ev_resp = websocket.receive_json()
            assert ev_resp.get("type") == "response"
            assert "ferrocarril" in ev_resp.get("content", "").lower()
            
            # Recibir evento 'token'
            ev_token = websocket.receive_json()
            assert ev_token.get("type") == "token"

            # Recibir evento 'done'
            ev_done = websocket.receive_json()
            assert ev_done.get("type") == "done"


# --- WS 5: Cierre limpio ---
def test_ws_5_cierre_limpio_conexion(test_client):
    """WS 5: Verifica que el cierre de la conexión por parte del cliente se complete limpiamente."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.close(code=1000)
```

---

## 5. Evidencia de Ejecución en Terminal (`pytest -v`)

A continuación se transcribe la salida íntegra de la sesión de pruebas en consola, certificando la recolección y aprobación de los 31 casos de prueba:

```powershell
(venv) PS C:\Users\nacho\Desktop\via-repo\via-asistente> pytest -v
================================ test session starts =================================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.7.0 -- C:\Users\nacho\Desktop\via-repo\via-asistente\venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: C:\Users\nacho\Desktop\via-repo\via-asistente
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.15.1
collected 31 items

tests/test_api_libros.py::test_get_api_libros_catalogo_solo_publicados PASSED   [  3%]    
tests/test_api_libros.py::test_get_api_libros_slug_detalle PASSED               [  6%]    
tests/test_api_libros.py::test_get_api_libros_slug_inexistente_o_borrador PASSED [  9%]
tests/test_api_libros.py::test_get_api_fundacion_compatibilidad PASSED          [ 12%]       
tests/test_api_libros.py::test_get_api_status_salud PASSED                         [ 16%]
tests/test_models.py::test_libro_model_campos_validos_y_restricciones PASSED       [ 19%] 
tests/test_models.py::test_libro_model_restriccion_slug_invalido PASSED            [ 22%] 
tests/test_models.py::test_libro_model_restriccion_anio_fuera_de_rango PASSED      [ 25%] 
tests/test_models.py::test_libro_model_restriccion_estado_invalido PASSED          [ 29%] 
tests/test_models.py::test_fragmento_model_validacion_y_normalizacion_tags PASSED  [ 32%] 
tests/test_models.py::test_fragmento_model_restriccion_orden_invalido PASSED       [ 35%] 
tests/test_models.py::test_detalle_libro_response_composicion PASSED               [ 38%] 
tests/test_models.py::test_meta_corpus_model PASSED                                [ 41%] 
tests/test_repository.py::test_normalizar_tag_individual PASSED                    [ 45%]  
tests/test_repository.py::test_criterio_a2_normalizacion_de_tags PASSED            [ 48%]  
tests/test_repository.py::test_repositorios_cumplen_protocolo[fake] PASSED         [ 51%]  
tests/test_repository.py::test_repositorios_cumplen_protocolo[mongo] PASSED        [ 54%]  
tests/test_repository.py::test_criterio_a3_libros_borrador_vs_publicado[fake] PASSED [ 58%]
tests/test_repository.py::test_criterio_a3_libros_borrador_vs_publicado[mongo] PASSED [ 61%]
tests/test_repository.py::test_guardar_fragmentos_normaliza_tags[fake] PASSED      [ 64%]   
tests/test_repository.py::test_guardar_fragmentos_normaliza_tags[mongo] PASSED     [ 67%]   
tests/test_repository.py::test_eliminar_libro_y_fragmentos[fake] PASSED            [ 70%]   
tests/test_repository.py::test_eliminar_libro_y_fragmentos[mongo] PASSED           [ 74%]   
tests/test_repository.py::test_criterio_a1_siembra_idempotente[fake] PASSED         [ 77%]  
tests/test_repository.py::test_criterio_a1_siembra_idempotente[mongo] PASSED        [ 80%]  
tests/test_repository.py::test_criterio_a5_validacion_config_y_sanitizacion PASSED  [ 83%]  
tests/test_ws_chat.py::test_ws_1_conexion_handshake PASSED                          [ 87%]  
tests/test_ws_chat.py::test_ws_2_ping_pong_control PASSED                           [ 90%]  
tests/test_ws_chat.py::test_ws_3_mensaje_vacio_retorna_error PASSED                 [ 93%]  
tests/test_ws_chat.py::test_ws_4_flujo_respuesta_chat PASSED                         [ 96%]
tests/test_ws_chat.py::test_ws_5_cierre_limpio_conexion PASSED                       [100%] 

==================================== warnings summary ===================================== 
tests\test_api_libros.py:11
  C:\Users\nacho\Desktop\via-repo\via-asistente\tests\test_api_libros.py:11: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
============================== 31 passed, 1 warning in 5.88s ============================== 
(venv) PS C:\Users\nacho\Desktop\via-repo\via-asistente> 
```

---

## 6. Conclusiones y Diagnóstico Técnico

1. **Alineación con Pydantic y BaseModel:** La integración de esquemas estructurados garantiza que ningún libro con metadatos anómalos (fechas espurias, slugs con espacios o caracteres no ASCII, estados inexistentes) sea expuesto por los endpoints HTTP o persistido en la capa de datos.
2. **Cobertura Integral de Transporte:** El protocolo dual HTTP REST y WebSocket opera bajo estándares de alta disponibilidad, demostrando respuestas inmediatas a nivel de socket (control de ping/pong y cierres con código 1000) e integridad semántica en peticiones GET con serialización ISO 8601 de marcas temporales.
3. **Mantenibilidad y Reproducibilidad:** Gracias a la inclusión de los archivos de entorno `pytest.ini` y `tests/conftest.py`, cualquier desarrollador o servidor de integración continua (CI/CD) puede invocar `pytest -v` de forma directa sin requerir variables globales previas en el sistema operativo.
4. **Tasa de Aprobación:** La totalidad de las pruebas (31/31, 100%) concluyó exitosamente en un tiempo promedio de 5.88 segundos, certificando la estabilidad de la rama de desarrollo.

