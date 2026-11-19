# Plan 02 — Carga por partes e Ingesta

## Enfoque
Implementar el pipeline de ingesta modular y desacoplado, probado como funciones y clases puras sin red ni Mongo (Sección 5.1 y 16.2):
1. **Seguridad Admin**: Middleware / Dependency para autenticar cabecera `X-Admin-Key` contra `settings.ADMIN_KEY` en todas las rutas `/api/admin/*`.
2. **Sesiones de Carga**: Manejo en memoria / repositorio temporal de cargas activas (`CargaSessionManager`) con almacenamiento por parte indexado en diccionario `{part_num: texto}` para garantizar idempotencia y control de faltantes.
3. **Fragmentador Semántico (`ingesta.py`)**: Función pura que recibe texto completo, detecta títulos Markdown (`#` o `##`), agrupa párrafos hasta la ventana óptima de ~800–1500 caracteres sin cortar frases, uniendo fragmentos cortos con sus vecinos y generando IDs semánticos `{slug}_{orden:02d}`.
4. **Protocolo Tagger (`tagger.py`)**: Interfaz `Tagger` con método `sugerir(fragmento, libro)` y su implementación por defecto `ManualTagger` (asiste sin bloquear la carga si falla).
5. **Endpoints `/api/admin/*` en `web_server.py`**: Integración de los endpoints del contrato de la sección 17.2 conectando `CargaSessionManager`, `ingesta.py` y `BookRepository`.

## Piezas
| Pieza (archivo/módulo) | Responsabilidad | Criterios que cubre |
|---|---|---|
| `ingesta.py` | Lógica pura de fragmentación de texto respetando títulos `#`, límite de ~800-1500 caracteres y cortes de frase. | B6 |
| `tagger.py` | Protocolo `Tagger`, `ManualTagger` y ejecución segura tolerante a fallos. | B7 |
| `carga_session.py` | Gestión de estado de cargas temporales (partes, idempotencia, verificación de hash SHA-256). | B2, B3, B4, B5 |
| `web_server.py` | Endpoints REST bajo `/api/admin/*` con validación de `X-Admin-Key` y orquestación del pipeline. | B2, B3, B4, B5, B8 |
| `tests/test_ingesta.py` | Batería de pruebas unitarias para el fragmentador puro y tagueo. | B6, B7 |
| `tests/test_admin_cargas.py` | Batería de pruebas para endpoints de carga por partes, idempotencia, hash y seguridad. | B2, B3, B4, B5, B8 |

## Decisiones y alternativas descartadas
- **Almacenamiento de partes intermedias**: Se usa un gestor en memoria (`CargaSessionManager`) con expiración y diccionario de partes. *Alternativa descartada*: escribir archivos temporales en disco o crear colecciones volátiles en MongoDB para cada chunk recibido, lo cual aumentaría I/O y acoplamiento innecesariamente para transporte de borradores.
- **Fragmentación en backend vs frontend**: El front solo parte el texto para transporte por red (~100.000 chars); el backend ensambla y realiza la fragmentación semántica (~800-1500 chars) sobre el texto completo asegurando que ningún párrafo ni sección quede cortada a la mitad por la división del transporte (Decisión 3.2 y 5.1).

## Riesgos
- **Riesgo**: Que una parte recibida exceda el límite de memoria permitido.
  - *Mitigación*: Validación de tope por parte (150.000 caracteres) retornando 413 Payload Too Large inmediatamente (Criterio B5).
- **Riesgo**: Que un error en el tagger aborte la carga de un libro.
  - *Mitigación*: Bloque `try/except` en la etapa de tagueo que degrada a fragmentos sin tags pero con advertencia, sin cancelar la creación del borrador (Criterio B7).
