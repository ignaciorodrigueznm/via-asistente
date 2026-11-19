# Spec 02 — Carga por partes e Ingesta

## Objetivo
Permitir que el backoffice cargue libros grandes mediante transporte secuencial por partes (~100.000 caracteres por parte), asegurando idempotencia, verificación estricta de hash SHA-256 al finalizar, ensamblado, limpieza, fragmentación semántica (~800-1500 caracteres respetando títulos `#` y límites de párrafo/frase) y tagueo extensible (`Tagger`), protegiendo las rutas administrativas con token `X-Admin-Key`.

## Historias de usuario
- Como **administrador del sistema**, quiero cargar archivos `.txt` grandes por partes para que la carga sea tolerante a cortes de red y se pueda reanudar sin duplicar datos.
- Como **sistema de ingesta**, quiero validar que el hash SHA-256 del texto ensamblado coincida con el esperado antes de fragmentar, para garantizar integridad absoluta del contenido.
- Como **motor MCP y usuario**, quiero que los fragmentos respeten los límites de párrafos y títulos semánticos (~800 a 1500 caracteres) y tengan tags normalizados para que las consultas y cruces entre libros sean precisos y quepan en el contexto del modelo.
- Como **administrador de seguridad**, quiero que todas las operaciones bajo `/api/admin/*` requieran un token `X-Admin-Key` válido para evitar accesos o modificaciones no autorizadas.

## Criterios de aceptación (Sección 16.2)
- **B1.** Dado un `.txt` de 350 000 caracteres y un límite de 100 000, cuando el front lo divide, entonces genera 4 partes cortadas en límite de párrafo o de título, ninguna supera el límite y la concatenación es idéntica al original.
- **B2.** Dado que la parte 2 se envía dos veces, cuando finalizo, entonces el texto no tiene contenido duplicado (idempotencia por número de parte).
- **B3.** Dado un corte de red después de la parte 2 de 4, cuando reanudo, entonces solo se envían las partes 3 y 4 (consultando `GET /api/admin/cargas/{carga_id}`).
- **B4.** Dado que falta una parte o el hash no coincide, cuando finalizo (`POST /api/admin/cargas/{carga_id}/finalizar`), entonces el backend responde con error y no crea fragmentos.
- **B5.** Dada una parte que supera el tope del backend, entonces el backend responde 413 aunque el front no lo haya respetado.
- **B6.** Dado el texto ensamblado, cuando se fragmenta, entonces los fragmentos miden alrededor de 800 a 1 500 caracteres (salvo secciones más cortas), ninguno termina a mitad de frase y se respetan los títulos `#`.
- **B7.** Dado un `Tagger` que falla, cuando termina la carga, entonces los fragmentos quedan sin tags y con un aviso, y la carga no se cancela (el tagueo asiste y nunca bloquea).
- **B8.** Dada una petición a `/api/admin/*` sin token válido (`X-Admin-Key`), entonces el backend responde 401 o 403.

## Fuera de alcance
- Interfaz gráfica web del Backoffice en React (se implementa en la Spec 03).
- Búsqueda multi-libro cruzada y herramientas avanzadas en MCP (se implementa en la Spec 05).
- Reconocimiento OCR o lectura directa de archivos PDF (el taller solo procesa texto plano `.txt`).

## Preguntas abiertas y supuestos
- [x] **¿Qué hacer con un párrafo más largo que el límite de transporte?** — Supuesto: Si un solo párrafo excede el límite de transporte, se corta en límite de frase (`. ` seguido de espacio o salto) para no romper palabras ni oraciones.
- [x] **¿Cuál es el tamaño total máximo de un libro?** — Supuesto: Límite por parte en backend = 150.000 caracteres (un 50% por encima de los 100.000 del front); límite total máximo por libro = 20 MB (~20.000.000 caracteres), respondiendo 413 si se supera.
- [x] **¿Qué pasa si el slug ya existe o el hash ya está cargado?** — Supuesto: Se verifica antes de iniciar la carga. Si el hash o el slug ya existen, se devuelve error 409 Conflict con mensaje explícito informando duplicado.
- [x] **¿Dónde se almacenan las partes intermedias de una carga antes de finalizar?** — Supuesto: En memoria / repositorio de sesiones de carga (`CargaSessionRepository`), o colección temporal, evitando escrituras parciales en la colección definitiva `libros`.

## Contrato que usa o expone (Sección 17.2)
- `POST /api/admin/libros` (Headers: `X-Admin-Key`): Recibe metadata del libro `{titulo, autor, anio, fuente_tipo, resumen, temas, hash_esperado}`. Valida si el slug/hash ya existen. Crea el libro en estado `borrador` y devuelve `{carga_id, slug}`.
- `PUT /api/admin/cargas/{carga_id}/partes/{n}` (Headers: `X-Admin-Key`): Recibe `{total: int, texto: str}`. Idempotente por número de parte. Valida tope por parte (413).
- `GET /api/admin/cargas/{carga_id}` (Headers: `X-Admin-Key`): Devuelve `{carga_id, partes_recibidas: [1, 2, ...], total_partes: int, completado: bool}`.
- `POST /api/admin/cargas/{carga_id}/finalizar` (Headers: `X-Admin-Key`): Recibe `{hash_texto: str}` (SHA-256). Valida que estén todas las partes, calcula SHA-256 del texto concatenado. Si coincide, fragmenta semánticamente, ejecuta tagueo opcional, guarda los fragmentos en `BookRepository` y confirma creación.
- `GET /api/admin/libros`: Lista todos los libros (incluye borradores).
- `GET /api/admin/libros/{slug}` y `PATCH`: Lee y edita fragmentos y libro.
- `POST /api/admin/libros/{slug}/publicar` y `/despublicar`: Modifica estado y sube `meta.version`.
- `DELETE /api/admin/libros/{slug}`: Elimina libro y fragmentos en cascada.
