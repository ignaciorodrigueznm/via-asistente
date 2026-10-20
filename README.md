# VÍA – Asistente virtual de la historia de Las Varillas

## Inicio rápido (AntiGravity / cualquier equipo)

```bash
pip install -r requirements.txt
python web_server.py
```
Abre **http://localhost:8000**. También puedes usar `iniciar.bat` (Windows) o `./iniciar.sh` (Linux/macOS), que crean el entorno virtual solos.

- Si Ollama (modelo `llama3.2`) está activo, VÍA genera respuestas con IA. Si no lo está, responde igualmente con los fragmentos del libro histórico.
- Variables opcionales: `PORT`, `HOST`, `MODEL`, `OLLAMA_URL`, `VIA_OPEN_BROWSER=0` (no abrir el navegador).
- `requirements.txt` fija `mcp<2`: la versión 2 elimina `FastMCP` y rompe `server.py`.

## Personalización
- **Saludo y preguntas sugeridas:** `data/bienvenida.json`.
- **Libro histórico:** `fundacion.json` (se muestra en el panel "Libro histórico").
- **Logo:** reemplaza `assets/VIA LOGO (512 x 512 px).svg` y `assets/VIA LOGO (1024 x 1024 px).svg` (mismos nombres). El navegador elige la resolución según la pantalla. Si el nuevo logo tiene otro margen interno, ajusta `--zoom`, `--cx`, `--cy` en `css/via.css` (`.via-mark`).
- **Historial de conversaciones:** las sesiones se guardan automáticamente en localStorage (hasta 40 conversaciones). Botón Historial en la barra superior para acceder, retomar o eliminar cualquier conversación pasada.
- **Colores:** variables al inicio de `css/via.css` (paleta de la bandera: celeste `#00AFF0`, amarillo `#FFCC2A`, gris `#BEBFC1`; fondo celeste suave y superficies crema, sin blanco puro).
- **Libro histórico:** botón "Libro histórico" arriba a la derecha. Se abre como tarjeta flotante o, con el botón "Anclar", en pantalla dividida junto al chat. Queda abierto mientras chateas; el modo elegido se recuerda.
- **Logo animado:** el engranaje gira al pasar el cursor sobre el logo (el tren del centro queda quieto). Código en `js/via.js` (`logoSpin`) y `.via-mark__hub` en el CSS.

---

# Workshop MCP 1.2: Optimización de Estructuras y Búsqueda Inteligente
### Caso de Estudio: Historia y Debate Fundacional de Las Varillas (Córdoba, Argentina)

Este proyecto implementa una arquitectura inspirada en **RAG (Generación Aumentada por Recuperación)** y **NoSQL** utilizando el protocolo estándar **MCP (Model Context Protocol)**. 

A través de un servidor MCP inteligente y un cliente optimizado, el sistema recupera quirúrgicamente fragmentos de información histórica sobre la ciudad de **Las Varillas** (Departamento San Justo, Córdoba, Argentina), inyectando el índice de la biblioteca en el *System Prompt* de un modelo LLM (**Ollama / LLaMA 3.2**) para evitar timeouts y saturación de contexto.

---

## 📁 Estructura del Proyecto

* **[fundacion.json](file:///fundacion.json)**: Base de datos estructurada en *chunks* (fragmentos) que documenta las tres posturas historiográficas sobre el origen de Las Varillas (1900, 1903 y 1904). Cada elemento cuenta con `id`, `titulo`, `contenido`, `tags` y `metadata`.
* **[server.py](file:///server.py)**: Servidor FastMCP que expone la herramienta `consultar_fundacion_las_varillas`. Admite:
  * **Modo Índice** (`tema=""`): Devuelve únicamente IDs, títulos y etiquetas para no sobrecargar el modelo.
  * **Búsqueda Quirúrgica / Fuzzy** (`tema="..."`): Normaliza texto (tildes, mayúsculas y puntuación), filtra *stopwords* y clasifica los resultados por relevancia.
* **[client.py](file:///client.py)**: Cliente MCP interactivo. Conecta con el servidor usando el intérprete virtual, inyecta el índice en el prompt del sistema y consulta al modelo local en Ollama.
* **[web_server.py](file:///web_server.py)**: Servidor web Starlette con puente FastMCP, cliente SSE para streaming con Ollama y endpoints REST:
  * `GET /`: Interfaz de usuario (Chatbot Web).
  * `GET /api/status`: Estado de FastMCP y Ollama.
  * `GET /api/fundacion`: Consulta directa a la base de datos histórica mediante FastMCP (`?tema=...`, `?id=...`, `?all=true`).
  * `POST /api/chat` y `POST /api/chat/stream`: Endpoints de conversación con RAG asistido por MCP.
* **[requirements.txt](file:///requirements.txt)**: Lista de dependencias de Python requeridas para ejecutar la solución.

---

## 🏛️ Contexto Histórico: Las Tres Posturas Fundacionales

| Año | Denominación | Actores / Promotores | Criterio Historiográfico |
| :---: | :--- | :--- | :--- |
| **1900** | *Llegada del Ferrocarril y Parada KM 81* | **Centro de Estudios Históricos Parada KM 81** | Llegada de la primera locomotora a la estación el 24 de diciembre de 1900, considerándolo el inicio efectivo del asentamiento comunitario. |
| **1903** | *Trazado Urbano y Donación de Tierras* | **Arq. Valter Dabbene**, **Ing. Omar Rubiolo** y don **José Medardo Álvarez Luque** | Donación documentada de tierras con fin explícito de fundar un pueblo (febrero/marzo de 1903) y confección/aprobación de los planos de trazado y loteo urbano. |
| **1904** | *Habilitación del Servicio y Reconocimiento Comunal* | **Gobierno de la Provincia de Córdoba** | Habilitación regular del servicio ferroviario comercial (15 de julio de 1904) y reconocimiento institucional y administrativo de la pedanía y autoridades comunales. |

---

## ⚙️ Requisitos Previos

1. **Python 3.10 o superior** (probado y compatible con Python 3.14).
2. *(Opcional para generación con IA)*: **[Ollama](https://ollama.com/)** instalado y ejecutándose en el equipo con el modelo `llama3.2`.

---

## 🚀 Instalación y Configuración

1. **Clonar o abrir el directorio del proyecto:**
   ```powershell
   cd via-asistente
   ```

2. **Crear y activar un entorno virtual (si no existe):**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias:**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Descargar el modelo en Ollama (si se va a utilizar el LLM):**
   ```powershell
   ollama run llama3.2
   ```

---

## 💻 Ejecución

Para iniciar el cliente en modo interactivo:

```powershell
.\venv\Scripts\python.exe client.py
```

Al iniciar, observarás en consola:
```text
Cliente MCP conectado correctamente
[MCP] Recuperando índice de la biblioteca...
[MCP] Índice cargado e inyectado con éxito.

Pregunta (o escribir 'salir'):
```

---

## 🧪 Pruebas de Validación (Paso 4 del Workshop)

El sistema está optimizado para responder de forma quirúrgica a las consultas clave:

1. **Consulta 1:** `¿A qué postura suscribe Valter Dabbene?`
   * **Comportamiento esperado:** Identifica y recupera de inmediato el fragmento de **1903** (Trazado y donación de Álvarez Luque).
2. **Consulta 2:** `¿Qué dice el Centro de Estudios Parada KM 81?`
   * **Comportamiento esperado:** Vincula la consulta de forma exclusiva con la teoría de **1900** (Locomotora inaugural y parada ferroviaria).
3. **Consulta 3:** `Dame un resumen de las tres teorías.`
   * **Comportamiento esperado:** Recupera la totalidad de los tres fragmentos históricos (**1900, 1903 y 1904**) para que el modelo elabore la síntesis comparativa.
4. **Salir:** Escribir `salir` para desconectar la sesión MCP y finalizar el proceso.