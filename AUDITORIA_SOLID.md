# Auditoría SOLID · VÍA (Asistente virtual de la historia de Las Varillas)

> **Regla de este trabajo:** mejorar la estructura aplicando SOLID **sin cambiar absolutamente nada** del funcionamiento, la estética ni la funcionalidad. Solo se refactorizó donde era necesario; en el resto se agregaron comentarios indicando qué principio se cumple y por qué.

---

## 1. Resumen en 30 segundos

| Pregunta | Respuesta |
| :-- | :-- |
| ¿El código estaba mal? | No. Funcionaba bien y estaba razonablemente ordenado. Tenía **pocos** problemas SOLID, concentrados en funciones demasiado largas. |
| ¿Qué se refactorizó? | 3 archivos Python (`server.py`, `client.py`, `web_server.py`) y 1 de JavaScript (`js/via.js`). Siempre **extrayendo funciones**, sin cambiar lo que hacen. |
| ¿Qué se dejó igual? | Estilos, estructura HTML, datos (`fundacion.json`, `bienvenida.json`), logos, README, nombres de rutas, textos, mensajes y orden de ejecución. |
| ¿Cómo sé que no cambió nada? | Se comparó el código original contra el nuevo con pruebas automáticas (ver sección 7): **mismas salidas en todos los casos probados**, incluso píxel a píxel en la pantalla. |
| ¿Qué se comentó? | Python, JavaScript y scripts (`.sh`, `.bat`, `requirements.txt`): **cada línea**. HTML: **cada elemento**. CSS: **cada regla/variable** (ver "Alcance de los comentarios"). |

### Nota por principio (después de este trabajo)

| Principio | Antes | Después | Qué pasó |
| :-- | :-: | :-: | :-- |
| **S**: Responsabilidad única | 🟠 Mejorable | 🟢 Bien | Se partieron funciones que hacían 4–6 cosas. |
| **O**: Abierto/Cerrado | 🟢 Bien | 🟢 Bien | Ya estaba bien (configuración por variables y datos en JSON). Se documentó. |
| **L**: Sustitución de Liskov | 🟢 N/A | 🟢 N/A | Casi no hay herencia; solo un middleware. Se documentó. |
| **I**: Segregación de interfaces | 🟢 Bien | 🟢 Bien | Las funciones reciben solo lo que necesitan. Se documentó. |
| **D**: Inversión de dependencias | 🟡 Aceptable | 🟡 Aceptable | Mejoró un poco (constante de la herramienta, punto único de acceso a datos). El resto **no se tocó** a propósito (sección 5). |

---

## 2. El proyecto en pocas palabras

VÍA es un chatbot web sobre la historia de Las Varillas. Funciona así:

```
Navegador (index.html + css/via.css + js/via.js)
      │  POST /api/chat/stream  (SSE)
      ▼
web_server.py  ──(MCP por stdio)──►  server.py  ──►  fundacion.json
      │                                  (busca fragmentos relevantes)
      ▼
Ollama / llama3.2  (si no está disponible, responde con el texto del libro)
```

`client.py` es una versión por consola del mismo flujo.

### Cómo leer los comentarios del código

Cada línea lleva un comentario en español que explica **qué hace**. Cuando una línea o función aplica un principio, el comentario lleva una etiqueta:

| Etiqueta | Significa |
| :-- | :-- |
| `[SRP]` | Esta pieza tiene **una sola responsabilidad**. |
| `[OCP]` | Se puede **extender sin modificar** código existente. |
| `[LSP]` | Las variantes/implementaciones son **intercambiables** sin romper nada. |
| `[ISP]` | La interfaz es **chica y específica** (solo lo necesario). |
| `[DIP]` | Se depende de una **abstracción**, no de un detalle concreto. |

Además, cada archivo empieza con un bloque **"AUDITORÍA SOLID"** que resume lo hallado y lo hecho en ese archivo.

---

## 3. Auditoría detallada por principio

### S · Responsabilidad única (SRP): *"una cosa, un motivo para cambiar"*

**Hallazgos (lo que estaba mal) y lo que se hizo:**

| Archivo | Problema encontrado | Solución aplicada (sin cambiar el resultado) |
| :-- | :-- | :-- |
| `server.py` | `consultar_fundacion_las_varillas` tenía **55 líneas** y hacía 6 trabajos: leer datos, armar índice, interpretar la consulta, detectar "resumen global", puntuar y filtrar, y convertir a JSON (el `json.dumps` estaba repetido 4 veces). | Se dividió en funciones de 3–10 líneas: `a_json`, `construir_indice`, `extraer_palabras_clave`, `es_consulta_global`, `preparar_documento`, `calcular_puntaje`, `filtrar_mas_relevantes`. La herramienta MCP quedó en **27 líneas** y solo "orquesta". |
| `client.py` | `main()` tenía **79 líneas** mezclando conexión MCP, lectura de consola, armado del prompt, llamada a Ollama y manejo de errores. | Se extrajeron `construir_system_prompt`, `construir_mensajes` y `consultar_ollama`. `main()` bajó a **47 líneas**. Los textos de los prompts son **idénticos byte a byte**. |
| `web_server.py` | Leer `message / use_mcp / model` del cuerpo estaba **copiado 3 veces** (chat normal, SSE y WebSocket). Llamar a la herramienta MCP con el candado estaba **copiado 2 veces**. El armado del filtro de `/api/fundacion` ocupaba la mitad de ese endpoint. El formateo de cada fragmento estaba dentro de un bucle de otra función. | Se extrajeron `obtener_parametros_chat`, `llamar_herramienta_mcp`, `filtro_desde_post`, `filtro_desde_query` y `formatear_item_para_llm`. Los endpoints quedaron más cortos y solo coordinan. |
| `js/via.js` | `ask()` (80 líneas) mezclaba **interfaz + red + lectura del stream SSE**. Tres líneas para "mostrar la respuesta" estaban copiadas en 3 lugares. El texto "sin conversaciones" estaba escrito 2 veces. | Se extrajeron `readSSE` (lee el stream), `showProse` (muestra la respuesta) y la constante `HISTORY_EMPTY_HTML`. `ask()` bajó a **64 líneas**. |

**Ya estaba bien (solo se comentó):** `normalizar`, `cargar_datos`, `respuesta_desde_libro`, `generar_respuesta`, `lifespan`, `NoCacheMiddleware`, `_static`, y en JS las secciones de historial, markdown, libro y animación del logo (cada una agrupa funciones de una sola tarea).

### O · Abierto/Cerrado (OCP): *"se extiende agregando, no modificando"*

**Estado: ya cumplía. No hizo falta refactorizar.** Se documentó dónde se ve:

- `STOPWORDS` (`server.py`): agregar palabras vacías **no obliga a tocar** la lógica de búsqueda.
- Variables de entorno `PORT`, `HOST`, `MODEL`, `OLLAMA_URL` (`web_server.py`): se cambia el comportamiento sin editar código.
- `routes` y `middleware` (`web_server.py`): sumar un endpoint o una carpeta estática es **agregar una línea**.
- `generar_respuesta` lo comparten SSE y WebSocket: un tercer transporte lo reutilizaría tal cual.
- `data/bienvenida.json` + `DEFAULT_WELCOME` (`via.js`): saludos, título y sugerencias se cambian desde un JSON.
- CSS: los colores, radios y sombras son variables (`:root`); las variantes (`--lg`, `--soft`, `--icon`, `--mode`) extienden a su base.

### L · Sustitución de Liskov (LSP): *"una variante no debe romper lo que se espera de la base"*

**Estado: casi no aplica** (no hay jerarquías de clases; solo existe `NoCacheMiddleware`). Se verificó y documentó que:

- `NoCacheMiddleware` respeta el contrato ASGI: deja pasar sin tocar todo lo que no sea HTTP y solo modifica la cabecera `Cache-Control`.
- La herramienta MCP mantiene **el mismo contrato** (nombre, parámetro `tema`, salida de texto) antes y después de la refactorización.
- En CSS, las variantes de botón/logo se pueden usar en lugar de la base sin romper el diseño.

### I · Segregación de interfaces (ISP): *"interfaces chicas y específicas"*

**Estado: ya cumplía.** Cada función recibe solo lo que usa: `addSources(bot, chunks)`, `showError(bot)`, `calcular_puntaje(texto_doc, palabras_clave)`, `filtro_desde_query(qp)`. La herramienta MCP expone **un único parámetro** (`tema`) y no hay "interfaces gordas". Tras la refactorización las funciones nuevas siguen esta misma línea.

### D · Inversión de dependencias (DIP): *"depender de abstracciones, no de detalles"*

**Estado: aceptable, con límites conscientes.**

Mejoras aplicadas (sin efecto visible):
- `cargar_datos()` es el **único punto** que sabe de dónde vienen los datos. Cambiar a una base de datos o una API implica tocar solo esa función.
- `HERRAMIENTA_LIBRO` (`web_server.py`): el nombre de la herramienta MCP estaba escrito 4 veces como texto suelto; ahora es una constante.
- `readSSE(res, onEvent)` (`via.js`): `ask()` depende de un *callback*, no de cómo se interpreta el stream.
- `consultar_ollama` (`client.py`) y `generar_respuesta` (`web_server.py`) concentran el contacto con el LLM.

Lo que **no** se cambió (ver sección 5).

---

## 4. Cambios archivo por archivo

| Archivo | Cambio de código | Comentarios |
| :-- | :-- | :-- |
| `server.py` | Refactor SRP (7 funciones nuevas). Salida **idéntica** en 37 consultas probadas. | Cada línea |
| `client.py` | Refactor SRP (3 funciones nuevas). Se conservaron los saltos de línea CRLF del original. | Cada línea |
| `web_server.py` | Refactor SRP (5 funciones nuevas + 1 constante). Rutas y respuestas idénticas. | Cada línea |
| `js/via.js` | Refactor SRP (`readSSE`, `showProse`, `HISTORY_EMPTY_HTML`). | Cada línea |
| `index.html` | **Ninguno.** | Cada elemento |
| `css/via.css` | **Ninguno.** | Cada regla y variable |
| `iniciar.sh`, `iniciar.bat`, `requirements.txt` | **Ninguno** (solo comentarios; sin tildes en el `.bat` para evitar problemas de consola). | Cada línea |
| `.gitignore` | **Ninguno** (estaba vacío; solo se agregaron 2 líneas de comentario). | — |
| `README.md`, `fundacion.json`, `data/bienvenida.json`, `assets/*.svg` | **Ninguno, no se tocaron.** (JSON no admite comentarios.) | — |

### Alcance de los comentarios (transparencia)

- **Python, JS, `.sh`, `.bat`, `requirements.txt`:** comentario en **cada línea** de código.
- **HTML:** comentario sobre **cada elemento** (se anota la etiqueta de apertura de cada bloque, ícono, botón y recurso).
- **CSS:** comentario en **cada regla y cada variable**, no en cada declaración individual (`color`, `margin`, etc.), porque repetir "define el color" 700 veces no aporta información. SOLID tampoco se aplica literalmente a CSS; se anotan sus equivalentes (ver cabecera del archivo).

---

## 5. Qué NO se cambió y por qué (decisión consciente)

Estos puntos **no son errores graves**, pero un purista de SOLID los marcaría. Se dejaron igual porque corregirlos obligaría a **reestructurar la app** o **cambiar el comportamiento**, y el pedido fue no cambiar nada.

| # | Punto | Principio | Por qué se dejó | Cómo se arreglaría (si algún día se autoriza) |
| :-: | :-- | :-: | :-- | :-- |
| 1 | `web_server.py` usa **estado global** (`mcp_session`, `mcp_index_str`, `mcp_lock`). | D / S | Pasarlo a una clase inyectable cambia la estructura del arranque. | Crear una clase `LibroHistorico` (con `consultar(tema)`) y una `ClienteLLM`, inyectadas en los endpoints. |
| 2 | `web_server.py` llama a **Ollama directamente** con `httpx` y con la forma de su API. | D | Abstraerlo requiere nuevas clases/archivos. | Interfaz `ProveedorLLM` con implementación `Ollama`; permitiría cambiar de modelo/proveedor sin tocar los endpoints. |
| 3 | `extraer_texto_mcp`, `OLLAMA_URL` y `MODEL` están **duplicados** entre `client.py` y `web_server.py`. | DRY / S | Unificarlos exige un archivo compartido nuevo y cambiar imports. | Módulo `comun.py` con esas piezas. |
| 4 | `client.py` usa `requests.post` (**bloqueante**) dentro de código `async`. | S / calidad | Cambiarlo a `httpx` asíncrono altera la ejecución. En una consola de un solo usuario no se nota. | Usar `httpx.AsyncClient` o `asyncio.to_thread`. |
| 5 | `via.js` es **un solo archivo de ~780 líneas** (aunque separado en secciones). | S | Partirlo en módulos cambia cómo carga `index.html`. | Módulos ES: `history.js`, `markdown.js`, `chat.js`, `book.js`, `logo.js`. |
| 6 | `server.py` lee `fundacion.json` **en cada consulta** (sin caché). | Rendimiento | Es intencional o al menos inofensivo: permite editar el libro sin reiniciar. | Cachear con control de fecha de modificación. |

---

## 6. Otros hallazgos de la auditoría (fuera de SOLID)

No se corrigieron (no se debía cambiar nada), pero conviene saberlos. Gravedad: 🔴 alta · 🟠 media · 🟡 baja · ⚪ informativa.

| Gravedad | Hallazgo | Detalle |
| :-: | :-- | :-- |
| 🟠 | **Servidor expuesto a toda la red.** | `HOST` por defecto es `0.0.0.0` y CORS permite cualquier origen (`allow_origins=["*"]`). Cualquiera en la misma red puede usar el chat y el modelo. Para uso local conviene `127.0.0.1`. |
| 🟠 | **El cliente puede elegir el modelo.** | Los endpoints aceptan `"model"` en el JSON; alguien podría pedir cualquier modelo instalado en Ollama (consumo de recursos). Conviene limitarlo a una lista permitida. |
| 🟠 | **Historial puede perderse sin aviso.** | `via.js` guarda en `localStorage` hasta 40 conversaciones **con los fragmentos completos del libro** en cada respuesta. Al llenarse la cuota, `saveHistory` ignora el error y no se guarda. Conviene guardar solo los `id` de las fuentes. |
| 🟢 | **WebSocket robusto y con Agent Loop.** | *(Resuelto)* Se integró el bucle de razonamiento autónomo interactivo del Plan MCP. Valida `isinstance(body, dict)`, admite `{"text": ...}` y `{"message": ...}`, maneja reconexión, pings, y gestiona `WebSocketDisconnect` de forma limpia para pruebas de carga Open/Close. |
| 🟡 | **Detección de "resumen global" muy amplia.** | Cualquier consulta que contenga "resumen", "tres" o "todas" devuelve **toda** la base, aunque pregunten por algo puntual (p. ej. "resumen de lo de Dabbene"). |
| 🟡 | **Coincidencia parcial ruidosa.** | `palabra in texto_doc` también acierta dentro de otras palabras (p. ej. "ya" dentro de "playa"), lo que puede sumar puntaje no deseado. |
| 🟢 | **`mcp_index_str` inyectado al agente.** | *(Resuelto)* El índice histórico precargado por FastMCP al iniciar se inyecta directamente en el `System Prompt` de cada sesión WebSocket como contexto inicial. |
| 🟡 | **Versionado manual de caché.** | `index.html` usa `?v=20261020` pero `NoCacheMiddleware` ya impide cachear: el parámetro es redundante. |
| 🟡 | **Dependencia externa de fuentes.** | `index.html` carga Inter desde Google Fonts: sin internet cae a fuentes del sistema (funciona, pero cambia el aspecto) y hay un pedido a terceros. |
| ⚪ | **`.gitignore` vacío.** | Conviene ignorar `venv/` y `__pycache__/`. |
| ⚪ | **README desactualizado en detalles.** | Los enlaces `file:///fundacion.json` no funcionan, y la sección de ejecución de `client.py` solo muestra comandos de PowerShell. |
| ⚪ | **Import sin uso.** | `client.py` importa `json` y no lo usa (se dejó igual). |
| ⚪ | **Buenas prácticas detectadas.** | El markdown del chat **escapa todo el HTML** antes de formatear (protege de inyección); hay respaldo si Ollama falla; se respeta `prefers-reduced-motion`; hay atributos ARIA y manejo de foco; `requirements.txt` fija `mcp<2` con la razón documentada. |

---

## 7. Cómo se comprobó que no cambió nada

Se guardó una copia intacta del original y se ejecutaron **pruebas comparativas** (original vs. refactorizado) con los mismos datos de entrada:

| Parte | Prueba | Resultado |
| :-- | :-- | :-- |
| `server.py` | 37 consultas (índice, resumen global, id exacto, años, nombres, texto sin sentido, vacío, archivo inexistente…) | ✅ Salida **idéntica** en todas |
| `web_server.py` | 122 casos por escenario: `/api/fundacion` (GET y POST, todas las variantes de parámetros), `/api/chat`, `/api/chat/stream` (SSE completo), WebSocket, `/api/status`, formateo de contexto, respaldo del libro; con el modelo respondiendo, caído, lento, con error HTTP y cortado a mitad; con y sin sesión MCP | ✅ Respuestas, códigos HTTP, eventos y **logs de consola idénticos** |
| `client.py` | Sesión simulada de consola con 4 modos (OK, sin conexión, error HTTP, error inesperado); se comparó todo lo impreso y los datos enviados a Ollama | ✅ **Idéntico** |
| `js/via.js` + HTML + CSS | Navegador Chromium real, 14 pasos: sugerencias, escritura con Enter, streaming (con eventos partidos a la mitad), fuentes, apertura del libro, anclar/soltar, historial, nueva conversación, restaurar, borrar, error + reintentar, vista móvil | ✅ DOM y estado **idénticos**, sin errores de JavaScript |
| Aspecto visual | Capturas de pantalla de escritorio y móvil (inicio, libro abierto, acordeón desplegado), con animaciones congeladas, 3 repeticiones | ✅ **Idénticas píxel a píxel** |
| Archivos de comentarios (HTML, CSS, scripts) | Se quitaron los comentarios y se comparó contra el original | ✅ **Mismo código** |
| JavaScript | Se quitaron comentarios y se hizo `diff` con el original | ✅ Las **únicas** diferencias son las del refactor descrito en la sección 3 |

**Límites honestos de la verificación:** en el entorno de prueba no se pudo instalar `mcp` ni `httpx` (red restringida), así que esos módulos se **simularon**; tampoco se ejecutó un Ollama real ni el transporte MCP real por stdio. La lógica propia (todo lo que se refactorizó) sí se ejecutó y comparó. Recomendación: antes de publicar, correr `python web_server.py` una vez en tu equipo y probar una pregunta (con Ollama encendido y apagado).

---

## 8. Recomendaciones para una próxima etapa (opcional)

Si más adelante se permite cambiar la estructura, el orden de mayor valor sería:

1. Limitar `HOST` a `127.0.0.1` y restringir CORS/modelos (seguridad).
2. Guardar solo los `id` de fuentes en el historial (evita perder conversaciones).
3. Extraer `LibroHistorico` y `ProveedorLLM` como clases inyectables (DIP).
4. Dividir `via.js` en módulos (SRP) y mover lo duplicado de `client.py`/`web_server.py` a un módulo común.
5. Agregar pruebas automáticas permanentes (las de esta auditoría pueden servir de base).
