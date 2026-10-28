# Plan 01 — Persistencia en MongoDB

## Enfoque
Implementar una capa de persistencia desacoplada utilizando el patrón Repositorio (`BookRepository`). Los datos residirán en MongoDB (colecciones `libros`, `fragmentos` y `meta`), mientras que las pruebas y componentes en desarrollo podrán ejecutarse de forma aislada y rápida utilizando `FakeRepo` en memoria. El repositorio normalizará los tags al momento de persistir para asegurar consultas cruzadas consistentes. El MCP consultará `meta.version` para invalidar y recargar su índice local sin requerir reinicio del subproceso.

## Piezas
| Pieza (archivo/módulo) | Responsabilidad | Criterios que cubre |
|---|---|---|
| `repository.py` | Protocolo `BookRepository`, normalizador de tags, `FakeRepo` y `MongoBookRepository`. | A1, A2, A3, A6 |
| `config.py` | Carga de variables de entorno (`MONGODB_URL`, `MONGODB_DB`, etc.), validación y sanitización (sin loguear contraseñas). | A5 |
| `seed_from_json.py` | Script CLI para sembrar de forma idempotente `fundacion.json` como primer libro en Mongo. | A1 |
| `tests/test_repository.py` | Suite de pruebas unitarias que verifica el contrato del repositorio contra `FakeRepo` y `MongoBookRepository`. | A1, A2, A3, A6 |
| `web_server.py` | Integración con el repositorio en el lifespan (lectura sin acoplamiento a Mongo directo). | A3, A5 |
| `server.py` | Integración del servidor MCP para consultar `meta.version` y cargar fragmentos desde el repositorio. | A4 |

## Decisiones y alternativas descartadas
- **Driver de MongoDB**: Se elige `pymongo` (compatible con la conexión síncrona del MCP y utilizable mediante adaptadores o llamadas controladas en el ciclo de vida del backend). Alternativa descartada: mezclar múltiples drivers dispares que compliquen el entorno y la compatibilidad.
- **Búsqueda (Decisión 4.3 del PDF)**: Opción 1 (Recomendada). Mongo almacena la fuente de verdad y, al arrancar o ante un cambio de `meta.version`, se cargan los fragmentos de libros publicados en memoria. Conserva el buscador por tokens actual con tolerancia a acentos y reduce la latencia en el agente.

## Riesgos
- **Riesgo**: Fallo al conectar con MongoDB si la base de datos no está activa localmente.
  - *Mitigación*: Validación rápida al arrancar con mensaje descriptivo que indica revisar `MONGODB_URL` sin imprimir credenciales (criterio A5).
- **Riesgo**: Inconsistencia en tags entre libros.
  - *Mitigación*: Normalización forzosa en la capa del repositorio al guardar (criterio A2).

## Pruebas
- **Con dobles (`FakeRepo`)**: Tests automatizados de guardado de libro, normalización de tags, listado según estado (borrador/publicado), siembra idempotente e incremento de `meta.version`.
- **A mano**: Ejecutar `python seed_from_json.py` dos veces contra MongoDB real y verificar conteos con Compass; verificar inicio del servidor con variable `MONGODB_URL` errónea.
