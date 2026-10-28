# Spec 01 — Persistencia en MongoDB

## Objetivo
Reemplazar la lectura estática directa de `fundacion.json` por una persistencia robusta en MongoDB para gestionar múltiples libros y fragmentos. Permitir que el backend web y el servidor MCP lean desde MongoDB, detectando libros nuevos o modificaciones mediante un contador de versión sin requerir reiniciar los procesos.

## Historias de usuario
- Como **administrador del sistema**, quiero que los libros y fragmentos se guarden de forma estructurada en MongoDB con colecciones indexadas para asegurar consultas rápidas y consistentes.
- Como **usuario del chat/asistente**, quiero consultar información de libros publicados en la base de datos sin notar degradación en las respuestas previas de `fundacion.json`.
- Como **desarrollador**, quiero un protocolo desacoplado (`BookRepository`) con implementación en memoria (`FakeRepo`) para ejecutar tests unitarios rápidos sin depender de una base de datos activa.
- Como **servidor MCP**, quiero vigilar el documento `meta.version` para invalidar y refrescar mi catálogo e índices de fragmentos en caliente cuando un libro sea publicado en el backoffice.

## Criterios de aceptación
- **A1.** Dado Mongo vacío, cuando ejecuto la siembra (`seed_from_json.py`), entonces hay 1 libro y 6 fragmentos; si la ejecuto otra vez, siguen siendo 1 y 6 (idempotencia).
- **A2.** Dado un fragmento con tags `["Ferrocarril", "  ferrocarril ", "Estación"]`, cuando se guarda, entonces quedan `["ferrocarril", "estacion"]` (normalizados: minúsculas, sin tildes, sin espacios ni duplicados).
- **A3.** Dado un libro en borrador, cuando el usuario consulta el catálogo, entonces no aparece; al publicarlo aparece y `meta.version` aumenta en 1.
- **A4.** Dado el MCP en ejecución, cuando se publica un libro, entonces la siguiente llamada a una herramienta lo encuentra sin reiniciar procesos.
- **A5.** Dado `MONGODB_URL` inválida o Mongo apagado, cuando arranca el backend, entonces falla con un mensaje que indica qué variable revisar y sin imprimir contraseñas en los registros.
- **A6.** Los tests del repositorio corren sin Mongo (con `FakeRepo`) y la misma batería pasa con el repositorio real (`MongoBookRepository`).

## Fuera de alcance
- Carga de archivos por partes vía endpoints HTTP (corresponde a Spec 02).
- Interfaz gráfica del Backoffice en React (corresponde a Spec 03).
- Nuevas herramientas MCP multi-libro avanzadas (`buscar_en_biblioteca`, `relacionados`, etc., corresponden a Spec 05).

## Preguntas abiertas
- [x] **¿Mongo local o Atlas?** — Supuesto inicial: Compatible con ambos vía `MONGODB_URL` en `.env`. Por defecto apuntará a Mongo local (`mongodb://localhost:27017`) con fallback descriptivo si no está activo.
- [x] **¿Qué librería utilizar para Mongo?** — Supuesto: `pymongo` (síncrono para scripts/MCP o tests) y cliente compatible asíncrono o wrappers de PyMongo para el ciclo de vida del backend.
- [x] **¿Qué pasa si dos libros tienen el mismo slug?** — Supuesto: El índice de `libros.slug` debe ser único (`unique=True`). Si se intenta insertar un libro con slug duplicado, se rechaza con error de validación o conflicto.
- [x] **¿Se puede borrar un libro publicado?** — Supuesto: Sí, mediante el método administrativo correspondiente, eliminando tanto el libro como sus fragmentos asociados y actualizando `meta.version`.
- [x] **¿Qué datos de ejemplo usa la siembra si fundacion.json falta?** — Supuesto: La siembra busca prioritariamente `fundacion.json` existente en la raíz; si no existe, avisa con error claro indicando que el archivo fuente es requerido.

## Contrato que usa o expone
- **Colección `libros`**: `slug`, `titulo`, `autor`, `anio`, `fuente_tipo`, `estado`, `resumen`, `temas`, `hash_texto`, `creado`.
- **Colección `fragmentos`**: `id`, `libro_id`, `libro_slug`, `orden`, `seccion`, `titulo`, `contenido`, `tags`, `metadata`, `tagueo`.
- **Colección `meta`**: `_id: "corpus"`, `version: int`.
- **Protocolo**: `BookRepository` con operaciones para listar catálogo, obtener libro, obtener fragmentos, sembrar/guardar y consultar versión del corpus.
