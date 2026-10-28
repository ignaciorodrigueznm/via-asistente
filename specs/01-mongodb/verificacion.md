# Informe de Verificación — Spec 01: Persistencia en MongoDB

Fecha: 2026-10-28
Rama: `feature/mongodb-integration`

## Tabla de Criterios de Aceptación (Sección 18.2)

| Criterio | Estado | Evidencia | Nota |
|---|---|---|---|
| **A1** (Dado Mongo vacío, siembra 1 libro y 6/3 fragmentos, idempotente) | **Cumple** | `tests/test_repository.py:test_criterio_a1_siembra_idempotente` (ejecutado con pytest pasando al 100%) | `seed_from_json.py:sembrar_datos` procesa `fundacion.json` sin duplicar registros en sucesivas ejecuciones. |
| **A2** (Normalización estricta de tags: minúsculas, sin tildes ni duplicados) | **Cumple** | `tests/test_repository.py:test_criterio_a2_normalizacion_de_tags` y `repository.py:normalizar_tags` | Transforma `["Ferrocarril", "  ferrocarril ", "Estación"]` en `["ferrocarril", "estacion"]`. |
| **A3** (Libro borrador no aparece en catálogo; al publicar aparece y `meta.version` incrementa) | **Cumple** | `tests/test_repository.py:test_criterio_a3_libros_borrador_vs_publicado` y `tests/test_api_libros.py` | Validado a nivel repositorio y a nivel endpoint HTTP `/api/libros`. |
| **A4** (MCP se entera de libros publicados sin reiniciar proceso vía `meta.version`) | **Cumple** | `server.py:cargar_datos` | Consulta `repo.obtener_version_corpus()` en cada llamada e invalida la caché en memoria cuando detecta incremento. |
| **A5** (Fallo de conexión o variable inválida avisa claramente sin exponer secretos) | **Cumple** | `tests/test_repository.py:test_criterio_a5_validacion_config_y_sanitizacion` y `config.py:sanitizar_mongodb_url` | Reemplaza contraseñas por `:***@` e identifica explícitamente `MONGODB_URL`. |
| **A6** (Misma batería de tests pasa con FakeRepo y con MongoBookRepository) | **Cumple** | `tests/test_repository.py:repo` fixture parametrizada `["fake", "mongo"]` (13 tests passed) | Se comprobó sin necesidad de base de datos activa usando dobles en memoria. |

## Resumen de Pruebas Automatizadas
- Total tests ejecutados: 17
- Total fallos: 0
- Comando ejecutado: `pytest tests/`
