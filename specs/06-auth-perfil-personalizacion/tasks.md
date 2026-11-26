# Tareas 06 — Autenticación, Perfil y Personalización

- [x] **T1** Servicio criptográfico y de tokens (`auth_service.py`).
  - Hashing seguro con `bcrypt` (hash y verificación).
  - Creación y decodificación de tokens JWT con expiración.
  - Se comprueba con: tests unitarios en `tests/test_auth.py`.

- [x] **T2** Modelos Pydantic para Auth y Perfil (`models.py`).
  - Esquemas de registro, login, actualización de perfil y preferencias de AI.
  - Se comprueba con: tests unitarios de validación en `tests/test_auth.py`.

- [x] **T3** Repositorio de Usuarios y Conversaciones en MongoDB y memoria (`repository.py`).
  - Métodos en `BookRepository`, `MongoBookRepository` y `FakeRepo`:
    - `crear_usuario`, `obtener_usuario_por_username`, `obtener_usuario_por_email`, `obtener_usuario_por_id`
    - `actualizar_perfil_usuario`, `actualizar_preferencias_ai`
    - `guardar_conversacion`, `listar_conversaciones_usuario`, `obtener_conversacion`, `eliminar_conversacion`
  - Se comprueba con: tests unitarios contra `FakeRepo` y `MongoBookRepository` con `mongomock`.

- [x] **T4** Endpoints REST de Autenticación y Perfil (`web_server.py`).
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - `GET /api/auth/me`
  - `PUT /api/usuario/perfil` (nombre y foto de perfil)
  - `PUT /api/usuario/preferencias-ai` ("Personalizar AI")
  - Se comprueba con: `TestClient` en `tests/test_auth_endpoints.py`.

- [x] **T5** Endpoints de Conversaciones Pasadas y personalización en Chat (`web_server.py`).
  - `GET /api/conversaciones`, `GET /api/conversaciones/{id}`, `POST /api/conversaciones`, `DELETE /api/conversaciones/{id}`.
  - Inyección de preferencias del usuario en el prompt del sistema (SSE, `/api/chat` y WebSocket).
  - Se comprueba con: `tests/test_auth_endpoints.py` y `tests/test_preferencias_prompt.py`.

- [x] **T6** Persistencia en MongoDB Atlas y carga de `.env`.
  - `config.py` carga `.env` con `python-dotenv`; se agregaron `python-dotenv` y `dnspython` a `requirements.txt`.
  - Timeouts de conexión ampliados para Atlas; errores sanitizados en logs.
  - `seed_from_json.py` incrementa `meta.version` al finalizar la siembra para invalidar la caché del MCP.
  - `.env` queda ignorado por git y se mantiene `.env.example`.
  - Se comprueba con: arranque real contra Atlas, login persistente tras reinicio y `pytest -q`.

- [x] **T7** Fix del endpoint `/api/fundacion` y del catálogo de libros.
  - Una única definición de `fundacion_endpoint`, `listar_libros_endpoint` y `obtener_libro_fragmentos_endpoint`.
  - Filtros `?id=`, `?all=true`, `?tema=`, `?q=` y `?buscar=` resueltos con repositorio, MCP y respaldo directo.
  - Fallback de `/api/libros` y `/api/libros/{slug}` a `fundacion.json`.
  - Se comprueba con: `tests/test_api_libros.py` (id exacto, all y repositorio vacío).
