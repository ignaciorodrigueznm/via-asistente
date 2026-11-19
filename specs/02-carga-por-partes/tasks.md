# Tareas 02 — Carga por partes e Ingesta

- [x] **T1** Fragmentador semántico como función pura (`ingesta.py`).
  - Cubre: B6
  - Se comprueba con: `pytest tests/test_ingesta.py` (títulos `#`, agrupar párrafos ~800-1500 chars, no cortar frases, unir fragmentos cortos).
- [x] **T2** Protocolo `Tagger` e implementación `ManualTagger` (`tagger.py`).
  - Cubre: B7
  - Se comprueba con: tests unitarios verificando que si el tagger lanza excepción, los fragmentos se generan sin tags y la carga no falla.
- [x] **T3** Gestor de sesiones de carga por partes (`carga_session.py`).
  - Cubre: B2, B3, B4, B5
  - Se comprueba con: tests unitarios para recepción de partes idempotente, tope de caracteres (413), consulta de partes faltantes y verificación de hash SHA-256.
- [ ] **T4** Autenticación por token `X-Admin-Key` en rutas `/api/admin/*` (`web_server.py`).
  - Cubre: B8
  - Se comprueba con: petición a `/api/admin/*` sin cabecera o con token erróneo que responde 401/403.
- [ ] **T5** Endpoints de carga por partes y finalización (`web_server.py`).
  - Cubre: B2, B3, B4, B5, B8
  - Se comprueba con: `POST /api/admin/libros`, `PUT /api/admin/cargas/{id}/partes/{n}`, `GET /api/admin/cargas/{id}`, `POST /api/admin/cargas/{id}/finalizar`.
- [ ] **T6** Endpoints CRUD de administración de libros y publicación (`web_server.py`).
  - Cubre: Contrato sección 17.2
  - Se comprueba con: `GET /api/admin/libros`, `GET/PATCH /api/admin/libros/{slug}`, `POST .../publicar`, `POST .../despublicar`, `DELETE /api/admin/libros/{slug}`.
