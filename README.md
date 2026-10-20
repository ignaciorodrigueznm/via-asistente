# VÃA Â· Asistente virtual de la historia de Las Varillas

## Inicio rÃ¡pido (AntiGravity / cualquier equipo)

```bash
pip install -r requirements.txt
python web_server.py
```
Abre **http://localhost:8000**. TambiÃ©n puedes usar `iniciar.bat` (Windows) o `./iniciar.sh` (Linux/macOS), que crean el entorno virtual solos.

- Si Ollama (modelo `llama3.2`) estÃ¡ activo, VÃA genera respuestas con IA. Si no lo estÃ¡, responde igualmente con los fragmentos del libro histÃ³rico.
- Variables opcionales: `PORT`, `HOST`, `MODEL`, `OLLAMA_URL`, `VIA_OPEN_BROWSER=0` (no abrir el navegador).
- `requirements.txt` fija `mcp<2`: la versiÃ³n 2 elimina `FastMCP` y rompe `server.py`.

## PersonalizaciÃ³n
- **Saludo y preguntas sugeridas:** `data/bienvenida.json`.
- **Libro histÃ³rico:** `fundacion.json` (se muestra en el panel "Libro histÃ³rico").
- **Logo:** reemplaza `assets/VIA LOGO (512 x 512 px).svg` y `assets/VIA LOGO (1024 x 1024 px).svg` (mismos nombres). El navegador elige la resoluciÃ³n segÃºn la pantalla. Si el nuevo logo tiene otro margen interno, ajusta `--zoom`, `--cx`, `--cy` en `css/via.css` (`.via-mark`).
- **Historial de conversaciones:** las sesiones se guardan automáticamente en localStorage (hasta 40 conversaciones). Botón Historial en la barra superior para acceder, retomar o eliminar cualquier conversación pasada.
- **Colores:** variables al inicio de `css/via.css` (paleta de la bandera: celeste `#00AFF0`, amarillo `#FFCC2A`, gris `#BEBFC1`; fondo celeste suave y superficies crema, sin blanco puro).
- **Libro histÃ³rico:** botÃ³n "Libro histÃ³rico" arriba a la derecha. Se abre como tarjeta flotante o, con el botÃ³n "Anclar", en pantalla dividida junto al chat. Queda abierto mientras chateas; el modo elegido se recuerda.
- **Logo animado:** el engranaje gira al pasar el cursor sobre el logo (el tren del centro queda quieto). CÃ³digo en `js/via.js` (`logoSpin`) y `.via-mark__hub` en el CSS.

---

# Workshop MCP 1.2: OptimizaciÃ³n de Estructuras y BÃºsqueda Inteligente
### Caso de Estudio: Historia y Debate Fundacional de Las Varillas (CÃ³rdoba, Argentina)

Este proyecto implementa una arquitectura inspirada en **RAG (GeneraciÃ³n Aumentada por RecuperaciÃ³n)** y **NoSQL** utilizando el protocolo estÃ¡ndar **MCP (Model Context Protocol)**. 

A travÃ©s de un servidor MCP inteligente y un cliente optimizado, el sistema recupera quirÃºrgicamente fragmentos de informaciÃ³n histÃ³rica sobre la ciudad de **Las Varillas** (Departamento San Justo, CÃ³rdoba, Argentina), inyectando el Ã­ndice de la biblioteca en el *System Prompt* de un modelo LLM (**Ollama / LLaMA 3.2**) para evitar timeouts y saturaciÃ³n de contexto.

---

## ðŸ“ Estructura del Proyecto

* **[fundacion.json](file:///fundacion.json)**: Base de datos estructurada en *chunks* (fragmentos) que documenta las tres posturas historiogrÃ¡ficas sobre el origen de Las Varillas (1900, 1903 y 1904). Cada elemento cuenta con `id`, `titulo`, `contenido`, `tags` y `metadata`.
* **[server.py](file:///server.py)**: Servidor FastMCP que expone la herramienta `consultar_fundacion_las_varillas`. Admite:
  * **Modo Ãndice** (`tema=""`): Devuelve Ãºnicamente IDs, tÃ­tulos y etiquetas para no sobrecargar el modelo.
  * **BÃºsqueda QuirÃºrgica / Fuzzy** (`tema="..."`): Normaliza texto (tildes, mayÃºsculas y puntuaciÃ³n), filtra *stopwords* y clasifica los resultados por relevancia.
* **[client.py](file:///client.py)**: Cliente MCP interactivo. Conecta con el servidor usando el intÃ©rprete virtual, inyecta el Ã­ndice en el prompt del sistema y consulta al modelo local en Ollama.
* **[web_server.py](file:///web_server.py)**: Servidor web Starlette con puente FastMCP, cliente SSE para streaming con Ollama y endpoints REST:
  * `GET /`: Interfaz de usuario (Chatbot Web).
  * `GET /api/status`: Estado de FastMCP y Ollama.
  * `GET /api/fundacion`: Consulta directa a la base de datos histÃ³rica mediante FastMCP (`?tema=...`, `?id=...`, `?all=true`).
  * `POST /api/chat` y `POST /api/chat/stream`: Endpoints de conversaciÃ³n con RAG asistido por MCP.
* **[requirements.txt](file:///requirements.txt)**: Lista de dependencias de Python requeridas para ejecutar la soluciÃ³n.

---

## ðŸ›ï¸ Contexto HistÃ³rico: Las Tres Posturas Fundacionales

| AÃ±o | DenominaciÃ³n | Actores / Promotores | Criterio HistoriogrÃ¡fico |
| :---: | :--- | :--- | :--- |
| **1900** | *Llegada del Ferrocarril y Parada KM 81* | **Centro de Estudios HistÃ³ricos Parada KM 81** | Llegada de la primera locomotora a la estaciÃ³n el 24 de diciembre de 1900, considerÃ¡ndolo el inicio efectivo del asentamiento comunitario. |
| **1903** | *Trazado Urbano y DonaciÃ³n de Tierras* | **Arq. Valter Dabbene**, **Ing. Omar Rubiolo** y don **JosÃ© Medardo Ãlvarez Luque** | DonaciÃ³n documentada de tierras con fin explÃ­cito de fundar un pueblo (febrero/marzo de 1903) y confecciÃ³n/aprobaciÃ³n de los planos de trazado y loteo urbano. |
| **1904** | *HabilitaciÃ³n del Servicio y Reconocimiento Comunal* | **Gobierno de la Provincia de CÃ³rdoba** | HabilitaciÃ³n regular del servicio ferroviario comercial (15 de julio de 1904) y reconocimiento institucional y administrativo de la pedanÃ­a y autoridades comunales. |

---

## âš™ï¸ Requisitos Previos

1. **Python 3.10 o superior** (probado y compatible con Python 3.14).
2. *(Opcional para generaciÃ³n con IA)*: **[Ollama](https://ollama.com/)** instalado y ejecutÃ¡ndose en el equipo con el modelo `llama3.2`.

---

## ðŸš€ InstalaciÃ³n y ConfiguraciÃ³n

1. **Clonar o abrir el directorio del proyecto:**
   ```powershell
   cd "mcp6toa-o"
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

## ðŸ–¥ï¸ EjecuciÃ³n

Para iniciar el cliente en modo interactivo:

```powershell
.\venv\Scripts\python.exe client.py
```

Al iniciar, observarÃ¡s en consola:
```text
Cliente MCP conectado correctamente
[MCP] Recuperando Ã­ndice de la biblioteca...
[MCP] Ãndice cargado e inyectado con Ã©xito.

Pregunta (o escribir 'salir'):
```

---

## ðŸ§ª Pruebas de ValidaciÃ³n (Paso 4 del Workshop)

El sistema estÃ¡ optimizado para responder de forma quirÃºrgica a las consultas clave:

1. **Consulta 1:** `Â¿A quÃ© postura suscribe Valter Dabbene?`
   * **Comportamiento esperado:** Identifica y recupera de inmediato el fragmento de **1903** (Trazado y donaciÃ³n de Ãlvarez Luque).
2. **Consulta 2:** `Â¿QuÃ© dice el Centro de Estudios Parada KM 81?`
   * **Comportamiento esperado:** Vincula la consulta de forma exclusiva con la teorÃ­a de **1900** (Locomotora inaugural y parada ferroviaria).
3. **Consulta 3:** `Dame un resumen de las tres teorÃ­as.`
   * **Comportamiento esperado:** Recupera la totalidad de los tres fragmentos histÃ³ricos (**1900, 1903 y 1904**) para que el modelo elabore la sÃ­ntesis comparativa.
4. **Salir:** Escribir `salir` para desconectar la sesiÃ³n MCP y finalizar el proceso.

