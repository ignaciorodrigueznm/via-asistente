"""
VÍA · Servidor web
Puente entre la interfaz, el servidor MCP (libro histórico) y el modelo LLM (Ollama).

Ejecutar:  python web_server.py   ->  http://localhost:8000
Variables opcionales: PORT, HOST, MODEL, OLLAMA_URL, OLLAMA_TAGS_URL, VIA_OPEN_BROWSER=0

AUDITORÍA SOLID (resumen de este archivo):
  - SRP: se extrajeron funciones que estaban repetidas o mezcladas dentro de los
    endpoints: `obtener_parametros_chat` (se repetía 3 veces), `llamar_herramienta_mcp`
    (se repetía 2 veces), `formatear_item_para_llm`, `filtro_desde_post` y
    `filtro_desde_query`. Los endpoints ahora solo coordinan.
  - OCP: el pipeline de chat (`generar_respuesta`) es compartido por SSE y
    WebSocket; agregar otro transporte no obliga a modificarlo.
  - LSP/ISP: los contratos públicos (rutas, JSON de entrada/salida, eventos SSE)
    son idénticos; los endpoints siguen siendo funciones pequeñas con una sola
    entrada (`request` / `websocket`).
  - DIP: el servidor depende de la herramienta MCP por su nombre
    (constante `HERRAMIENTA_LIBRO`) y no de la implementación de server.py,
    salvo el respaldo documentado en `fundacion_endpoint`.
  - NO se tocó (se documenta en la auditoría): el estado global del módulo y
    el acceso directo a Ollama/httpx. Cambiarlos implicaría reestructurar la
    app, y se pidió no alterar el funcionamiento.
"""
# Librería estándar: variables de entorno y rutas.
import os
# Librería estándar: acceso a stdout/stderr y al intérprete.
import sys

# Asegurar codificación UTF-8 en terminales Windows
# Si stdout permite reconfigurarse...
if hasattr(sys.stdout, "reconfigure"):
    # ...fuerza UTF-8 para imprimir tildes y emojis sin error.
    sys.stdout.reconfigure(encoding="utf-8")
# Si stderr permite reconfigurarse...
if hasattr(sys.stderr, "reconfigure"):
    # ...también lo fuerza a UTF-8.
    sys.stderr.reconfigure(encoding="utf-8")

# Librería estándar JSON.
import json
# Librería estándar asíncrona.
import asyncio
# Librería estándar para hilos (abrir el navegador con retardo).
import threading
# Librería estándar para abrir el navegador.
import webbrowser
# Utilidades para gestionar el ciclo de vida de recursos asíncronos.
from contextlib import asynccontextmanager, AsyncExitStack
# Cliente HTTP asíncrono (Ollama).
import httpx
# Aplicación web ASGI.
from starlette.applications import Starlette
# Tipos de respuesta HTTP.
from starlette.responses import JSONResponse, FileResponse, StreamingResponse
# Tipos de rutas.
from starlette.routing import Route, Mount, WebSocketRoute
# Servidor de archivos estáticos.
from starlette.staticfiles import StaticFiles
# Soporte de middleware.
from starlette.middleware import Middleware
# Middleware CORS.
from starlette.middleware.cors import CORSMiddleware
# Tipos de WebSocket.
from starlette.websockets import WebSocket, WebSocketDisconnect
# Cliente MCP por stdio.
from mcp.client.stdio import stdio_client, StdioServerParameters
# Sesión de cliente MCP.
from mcp import ClientSession

# Carpeta donde vive este archivo.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Si la carpeta no está en el path de importación...
if BASE_DIR not in sys.path:
    # ...se agrega al inicio (permite `from server import ...`).
    sys.path.insert(0, BASE_DIR)

# [OCP/DIP] Configuración por variables de entorno: se cambia el modelo/URL sin tocar código.
# URL del chat de Ollama.
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
# URL para listar modelos de Ollama.
OLLAMA_TAGS_URL = os.environ.get("OLLAMA_TAGS_URL", "http://localhost:11434/api/tags")
# Modelo por defecto.
MODEL = os.environ.get("MODEL", "llama3.2")

# Nombre de la herramienta MCP (antes escrito como texto suelto en 4 lugares).
HERRAMIENTA_LIBRO = "consultar_fundacion_las_varillas"

# Mensaje genérico cuando el modelo falla.
MSG_NO_DISPONIBLE = "No pude responder en este momento. Inténtalo de nuevo en unos segundos."

# Prompt del sistema que define la personalidad y reglas de VÍA.
SYSTEM_PROMPT = (
    # Presentación del asistente.
    "Eres VÍA, un asistente virtual experto en la historia y orígenes de Las Varillas (Córdoba, Argentina).\n"
    # Misión (primera parte).
    "Tu misión es responder a la pregunta del usuario utilizando de forma fidedigna y clara "
    # Misión (segunda parte).
    "los datos provistos en el fragmento histórico recuperado.\n"
    # Encabezado de reglas.
    "Reglas:\n"
    # Regla 1.
    "1. Si el contexto menciona al autor, historiador o teoría solicitada, explica su postura con los argumentos, fechas y detalles dados.\n"
    # Regla 2.
    "2. No digas que no tienes información si en los datos recuperados se encuentra la mención o investigación.\n"
    # Regla 3.
    "3. Responde en español, con tono cercano y claro. Sé conciso: prefiere respuestas breves y bien organizadas."
# Cierra el prompt.
)

# Estado global del backend (se maneja en silencio; la interfaz no lo muestra)
# Sesión MCP activa (None mientras no esté conectada).
mcp_session: ClientSession = None
# Índice del libro cargado al iniciar.
mcp_index_str: str = ""
# Candado para que las llamadas MCP no se pisen entre sí.
mcp_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# Utilidades MCP / contexto
# ---------------------------------------------------------------------------
# [SRP] Responsabilidad única: convertir una respuesta MCP en texto.
def extraer_texto_mcp(resultado):
    """Extrae el contenido textual de una respuesta MCP."""
    # Si no hay resultado o no tiene contenido, devuelve vacío.
    if not resultado or not hasattr(resultado, "content"):
        # Texto vacío.
        return ""
    # Une el texto de todos los bloques con saltos de línea.
    return "\n".join(bloque.text for bloque in resultado.content if hasattr(bloque, "text"))


# [SRP] Responsabilidad única: llamar a la herramienta MCP (antes repetido en 2 lugares).
# [DIP] El resto del módulo no conoce los detalles de la llamada (lock + sesión + extracción).
async def llamar_herramienta_mcp(tema: str) -> str:
    """Invoca la herramienta del libro histórico y devuelve su texto."""
    # Toma el candado para serializar las llamadas.
    async with mcp_lock:
        # Llama a la herramienta MCP con el tema indicado.
        resultado = await mcp_session.call_tool(
            # Nombre de la herramienta.
            HERRAMIENTA_LIBRO,
            # Argumentos de la herramienta.
            arguments={"tema": tema}
        # Cierra la llamada.
        )
    # Devuelve el texto de la respuesta.
    return extraer_texto_mcp(resultado)


# [SRP] Responsabilidad única: formatear UN fragmento histórico para el LLM
# (antes estaba incrustado dentro del bucle de `formatear_contexto_para_llm`).
def formatear_item_para_llm(item) -> str:
    """Convierte un fragmento histórico en texto estructurado."""
    # Título del fragmento.
    titulo = item.get("titulo", "")
    # Contenido del fragmento.
    contenido = item.get("contenido", "")
    # Metadatos del fragmento.
    meta = item.get("metadata", {})
    # Promotor o investigadores.
    promotor = meta.get("promotor", "")
    # Fecha clave.
    fecha = meta.get("fecha_clave", "")
    # Criterio fundacional.
    criterio = meta.get("criterio", "")

    # Encabezado del fragmento.
    texto_item = f"### {titulo}\n"
    # Agrega el detalle solo si existe.
    if contenido:
        # Línea de detalle.
        texto_item += f"- Detalle: {contenido}\n"
    # Agrega el promotor solo si existe.
    if promotor:
        # Línea de promotor.
        texto_item += f"- Promotor/Investigadores: {promotor}\n"
    # Agrega la fecha solo si existe.
    if fecha:
        # Línea de fecha.
        texto_item += f"- Fecha clave: {fecha}\n"
    # Agrega el criterio solo si existe.
    if criterio:
        # Línea de criterio.
        texto_item += f"- Criterio fundacional: {criterio}\n"
    # Devuelve el texto del fragmento.
    return texto_item


# [SRP] Responsabilidad única: preparar el contexto legible para el LLM.
def formatear_contexto_para_llm(contexto_raw: str) -> str:
    """Convierte el JSON devuelto por MCP en texto claro y estructurado para el LLM."""
    # Si el contexto está vacío, devuelve el mensaje estándar.
    if not contexto_raw or not contexto_raw.strip():
        # Mensaje estándar de "sin datos".
        return "No se encontraron datos históricos en la base de datos."

    # Intenta interpretar el contexto como JSON.
    try:
        # Convierte el texto en objetos Python.
        data = json.loads(contexto_raw)
        # Caso: lista de fragmentos.
        if isinstance(data, list):
            # Lista vacía = sin datos.
            if not data:
                # Mensaje estándar de "sin datos".
                return "No se encontraron datos históricos en la base de datos."
            # Formatea cada fragmento con la función dedicada.
            partes = [formatear_item_para_llm(item) for item in data]
            # Une todos los fragmentos separados por salto de línea.
            return "\n".join(partes)
        # Caso: diccionario simple.
        elif isinstance(data, dict):
            # Lo convierte en lista de "- clave: valor".
            return "\n".join(f"- {k}: {v}" for k, v in data.items())
    # Cualquier error de formato se ignora...
    except Exception:
        # ...y se continúa con el texto crudo.
        pass

    # Si no fue JSON válido, devuelve el texto original.
    return contexto_raw


# [SRP] Responsabilidad única: armar los mensajes para el modelo.
def construir_mensajes(pregunta: str, contexto: str) -> list:
    """Arma los mensajes que se envían al modelo."""
    # Convierte el contexto en texto legible.
    contexto_legible = formatear_contexto_para_llm(contexto)
    # Devuelve la lista de mensajes (sistema + usuario).
    return [
        # Mensaje de sistema con las reglas de VÍA.
        {"role": "system", "content": SYSTEM_PROMPT},
        # Mensaje del usuario.
        {
            # Rol "user".
            "role": "user",
            # Contenido: datos recuperados + pregunta.
            "content": (
                # Encabezado de datos.
                f"Datos históricos recuperados de la base de conocimiento:\n"
                # Separador superior.
                f"----------------------------------------\n"
                # Contexto legible.
                f"{contexto_legible}\n"
                # Separador inferior.
                f"----------------------------------------\n\n"
                # Pregunta del usuario.
                f"Pregunta del usuario:\n{pregunta}\n\n"
                # Instrucción final.
                f"Por favor responde a la pregunta basándote en los datos anteriores."
            # Cierra el contenido.
            )
        # Cierra el mensaje del usuario.
        }
    # Cierra la lista.
    ]


# [SRP] Responsabilidad única: consultar el libro y devolver (texto, datos).
async def consultar_mcp(pregunta: str, use_mcp: bool = True):
    """Busca contexto en el libro histórico. Devuelve (contexto_texto, mcp_data)."""
    # Contexto vacío por defecto.
    contexto = ""
    # Datos MCP por defecto (no se usó MCP).
    mcp_data = {"used": False, "context": "", "chunks": []}

    # Solo consulta si se pidió MCP y hay sesión activa.
    if use_mcp and mcp_session is not None:
        # Protege contra errores de la herramienta.
        try:
            # Llama a la herramienta MCP (lock incluido) y obtiene el texto.
            contexto = await llamar_herramienta_mcp(pregunta)
            # Lista de fragmentos (vacía por defecto).
            chunks = []
            # Intenta interpretar el contexto como JSON.
            try:
                # Convierte el texto en objetos.
                parsed = json.loads(contexto)
                # Solo acepta listas como fragmentos.
                if isinstance(parsed, list):
                    # Guarda los fragmentos.
                    chunks = parsed
            # Si no es JSON válido...
            except Exception:
                # ...se ignora.
                pass
            # Datos MCP para el frontend.
            mcp_data = {
                # Indica que se usó MCP.
                "used": True,
                # Nombre de la herramienta usada.
                "tool": HERRAMIENTA_LIBRO,
                # Texto crudo devuelto.
                "context": contexto,
                # Fragmentos estructurados.
                "chunks": chunks
            # Cierra el diccionario.
            }
        # Si algo falla...
        except Exception as e:
            # ...lo registra en consola...
            print(f"[MCP] Error al consultar el libro: {e}")
            # ...limpia el contexto...
            contexto = ""
            # ...y devuelve los datos de error.
            mcp_data = {"used": False, "error": str(e), "context": ""}

    # Devuelve el contexto y los datos MCP.
    return contexto, mcp_data


# [SRP] Responsabilidad única: respuesta de respaldo sin LLM.
def respuesta_desde_libro(chunks: list) -> str:
    """
    Respaldo cuando el modelo de lenguaje no está disponible: responde directamente
    con los fragmentos recuperados del libro, para que VÍA siga siendo útil.
    """
    # Sin fragmentos: mensaje de "no encontré".
    if not chunks:
        # Devuelve el mensaje amable.
        return (
            # Primera parte del mensaje.
            "No encontré información sobre eso en el libro histórico. "
            # Segunda parte con sugerencias.
            "Prueba preguntando por el origen de Las Varillas, por la teoría de 1900, 1903 o 1904."
        # Cierra el mensaje.
        )
    # Lista de líneas de la respuesta (empieza con el encabezado).
    partes = ["Esto es lo que dice el libro histórico sobre tu consulta:\n"]
    # Recorre cada fragmento.
    for c in chunks:
        # Metadatos del fragmento (o diccionario vacío).
        meta = c.get("metadata", {}) or {}
        # Título en formato de encabezado.
        partes.append(f"### {c.get('titulo', '')}")
        # Contenido, si existe.
        if c.get("contenido"):
            # Agrega el contenido.
            partes.append(c["contenido"])
        # Fecha clave, si existe.
        if meta.get("fecha_clave"):
            # Agrega la fecha en negrita.
            partes.append(f"- **Fecha clave:** {meta['fecha_clave']}")
        # Promotor, si existe.
        if meta.get("promotor"):
            # Agrega el promotor en negrita.
            partes.append(f"- **Impulsada por:** {meta['promotor']}")
        # Línea en blanco entre fragmentos.
        partes.append("")
    # Une las líneas y quita espacios sobrantes.
    return "\n".join(partes).strip()


# [SRP] Responsabilidad única: generar la respuesta (modelo + respaldo) como flujo de eventos.
# [OCP] Lo comparten SSE y WebSocket: un nuevo transporte lo reutiliza sin modificarlo.
async def generar_respuesta(pregunta: str, contexto: str, chunks: list, model: str, timeout: float = 240.0):
    """
    Generador asíncrono compartido por SSE y WebSocket.
    Emite tuplas ("token", texto) o ("error", mensaje).
    Si el modelo no responde y no se emitió nada, usa el respaldo con el libro.
    """
    # Cantidad de tokens enviados hasta ahora.
    emitidos = 0

    # Generador interno que "teclea" el respaldo de a 3 palabras.
    async def respaldo():
        # Texto completo del respaldo.
        texto = respuesta_desde_libro(chunks)
        # Separa en palabras.
        palabras = texto.split(" ")
        # Avanza de a 3 palabras.
        for i in range(0, len(palabras), 3):
            # Emite 3 palabras (con espacio final salvo en el último grupo).
            yield " ".join(palabras[i:i + 3]) + (" " if i + 3 < len(palabras) else "")
            # Pausa mínima para simular escritura.
            await asyncio.sleep(0.012)

    # Protege contra fallos de red o del modelo.
    try:
        # Abre un cliente HTTP con el timeout indicado.
        async with httpx.AsyncClient(timeout=timeout) as client:
            # Abre la petición en modo streaming hacia Ollama.
            async with client.stream(
                # Método HTTP.
                "POST",
                # Dirección de Ollama.
                OLLAMA_URL,
                # Cuerpo: modelo, mensajes y streaming activado.
                json={"model": model, "messages": construir_mensajes(pregunta, contexto), "stream": True}
            # Nombra la respuesta como `resp`.
            ) as resp:
                # Si Ollama no responde 200...
                if resp.status_code != 200:
                    # ...lo registra...
                    print(f"[LLM] Respuesta HTTP {resp.status_code} del modelo")
                    # ...y emite el respaldo del libro.
                    async for t in respaldo():
                        # Emite cada fragmento como token.
                        yield ("token", t)
                    # Termina el generador.
                    return

                # Lee la respuesta línea por línea.
                async for line in resp.aiter_lines():
                    # Ignora líneas vacías.
                    if not line:
                        # Pasa a la siguiente línea.
                        continue
                    # Intenta interpretar la línea como JSON.
                    try:
                        # Convierte la línea en diccionario.
                        data = json.loads(line)
                    # Si la línea es inválida...
                    except Exception:
                        # ...la salta.
                        continue
                    # Extrae el texto del token.
                    token = data.get("message", {}).get("content", "")
                    # Si hay texto...
                    if token:
                        # ...cuenta el token emitido...
                        emitidos += 1
                        # ...y lo envía.
                        yield ("token", token)
                    # Si Ollama indica que terminó...
                    if data.get("done", False):
                        # ...corta el bucle.
                        break
    # Si ocurre cualquier error...
    except Exception as e:
        # ...lo registra...
        print(f"[LLM] No se pudo generar con el modelo: {e!r}")
        # Si todavía no se emitió nada...
        if emitidos == 0:
            # ...usa el respaldo del libro.
            async for t in respaldo():
                # Emite cada fragmento como token.
                yield ("token", t)
        # Si ya se había emitido algo...
        else:
            # ...informa el error al cliente.
            yield ("error", MSG_NO_DISPONIBLE)


# ---------------------------------------------------------------------------
# Ciclo de vida: conexión silenciosa con el servidor MCP
# ---------------------------------------------------------------------------
# [SRP] Responsabilidad única: abrir y cerrar la conexión con el servidor MCP.
# Gestor de ciclo de vida de la aplicación.
@asynccontextmanager
async def lifespan(app: Starlette):
    # Permite modificar el estado global.
    global mcp_session, mcp_index_str
    # Mensaje de inicio.
    print("\n[VÍA] Iniciando servidor del libro histórico...")

    # Pila que cerrará los recursos al terminar.
    exit_stack = AsyncExitStack()
    # Parámetros para lanzar server.py como subproceso MCP.
    server_params = StdioServerParameters(
        # Mismo intérprete Python actual.
        command=sys.executable,
        # Ruta de server.py.
        args=[os.path.join(BASE_DIR, "server.py")]
    # Cierra los parámetros.
    )

    # Protege el arranque del servidor MCP.
    try:
        # Abre la conexión stdio y la registra en la pila.
        read, write = await exit_stack.enter_async_context(stdio_client(server_params))
        # Abre la sesión MCP y la registra en la pila.
        session = await exit_stack.enter_async_context(ClientSession(read, write))
        # Handshake inicial.
        await session.initialize()

        # Pide el índice del libro (tema vacío).
        res_indice = await session.call_tool(HERRAMIENTA_LIBRO, arguments={"tema": ""})
        # Guarda el índice como texto.
        mcp_index_str = extraer_texto_mcp(res_indice)
        # Publica la sesión como disponible.
        mcp_session = session
        # Informa que todo está listo.
        print("[VÍA] Libro histórico listo.")
    # Si algo falla...
    except Exception as e:
        # ...lo informa...
        print(f"[VÍA] No se pudo iniciar el servidor MCP: {e}")
        # ...y deja la sesión como no disponible.
        mcp_session = None

    # Punto donde la aplicación queda en ejecución.
    yield

    # Al apagar, cierra todos los recursos.
    await exit_stack.aclose()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
# Sirve la página principal.
async def serve_index(request):
    # Devuelve index.html.
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


# Endpoint de diagnóstico: estado de MCP y Ollama.
async def get_status(request):
    """Estado interno (solo para diagnóstico; la interfaz no lo muestra)."""
    # Estado de MCP según haya sesión o no.
    mcp_status = "online" if mcp_session is not None else "offline"

    # Estado de Ollama (pesimista por defecto).
    ollama_status = "offline"
    # Lista de modelos disponibles.
    available_models = []
    # Protege la consulta a Ollama.
    try:
        # Cliente HTTP con timeout corto.
        async with httpx.AsyncClient(timeout=3.0) as client:
            # Pide la lista de modelos.
            resp = await client.get(OLLAMA_TAGS_URL)
            # Si respondió bien...
            if resp.status_code == 200:
                # ...extrae los nombres de los modelos...
                available_models = [m.get("name", "") for m in resp.json().get("models", [])]
                # ...y marca Ollama como online.
                ollama_status = "online"
    # Si falla...
    except Exception:
        # ...se deja como offline.
        pass

    # Devuelve el estado como JSON.
    return JSONResponse({
        # Estado general.
        "status": "ok",
        # Información de MCP.
        "mcp": {
            # Estado online/offline.
            "status": mcp_status,
            # Nombre del servidor MCP.
            "server": "HistoriaVarillas",
            # Herramientas disponibles.
            "tools": [HERRAMIENTA_LIBRO] if mcp_session is not None else [],
            # Si se cargó el índice.
            "has_index": bool(mcp_index_str)
        # Cierra "mcp".
        },
        # Información de Ollama.
        "ollama": {
            # Estado online/offline.
            "status": ollama_status,
            # Modelo por defecto.
            "default_model": MODEL,
            # Modelos instalados.
            "available_models": available_models
        # Cierra "ollama".
        }
    # Cierra la respuesta.
    })


# [SRP] Responsabilidad única: leer el filtro desde el cuerpo de un POST.
def filtro_desde_post(body) -> str:
    """Obtiene el filtro (tema/q/buscar/id) y detecta 'todas' desde un cuerpo JSON."""
    # Toma el primer valor presente entre tema, q, buscar o id.
    filtro = (body.get("tema") or body.get("q") or body.get("buscar") or body.get("id") or "").strip()
    # Si piden todo (all/full/completo)...
    if body.get("all") or body.get("full") or body.get("completo"):
        # ...usa la palabra especial "todas".
        filtro = "todas"
    # Devuelve el filtro final.
    return filtro


# [SRP] Responsabilidad única: leer el filtro desde la query string de un GET.
def filtro_desde_query(qp) -> str:
    """Obtiene el filtro desde los parámetros de la URL (id, all, tema, q, buscar)."""
    # Filtro vacío por defecto (= índice).
    filtro = ""
    # Parámetro "all" en cualquiera de sus alias.
    all_param = qp.get("all") or qp.get("full") or qp.get("completo")
    # Prioridad 1: id explícito.
    if qp.get("id"):
        # Usa el id.
        filtro = qp.get("id").strip()
    # Prioridad 2: all verdadero.
    elif all_param and all_param.lower() in ("true", "1", "si", "yes"):
        # Usa la palabra especial "todas".
        filtro = "todas"
    # Prioridad 3: tema.
    elif qp.get("tema") is not None:
        # Usa el tema.
        filtro = qp.get("tema").strip()
    # Prioridad 4: q.
    elif qp.get("q") is not None:
        # Usa q.
        filtro = qp.get("q").strip()
    # Prioridad 5: buscar.
    elif qp.get("buscar") is not None:
        # Usa buscar.
        filtro = qp.get("buscar").strip()
    # Devuelve el filtro final.
    return filtro


# Endpoint del libro histórico (GET/POST).
async def fundacion_endpoint(request):
    """
    GET/POST /api/fundacion — consulta el libro histórico.
      - sin parámetros: índice de secciones (id, título, etiquetas)
      - ?id=<id>: una sección completa
      - ?tema=/q=/buscar=: búsqueda por palabras clave
      - ?all=true: todas las secciones completas
    """
    # Filtro vacío por defecto.
    filtro = ""
    # Si es POST...
    if request.method == "POST":
        # ...intenta leer el JSON.
        try:
            # Lee el cuerpo JSON.
            body = await request.json()
            # Extrae el filtro con la función dedicada.
            filtro = filtro_desde_post(body)
        # Si falla algo...
        except Exception:
            # ...usa filtro vacío.
            filtro = ""
    # Si es GET...
    else:
        # ...extrae el filtro de la URL con la función dedicada.
        filtro = filtro_desde_query(request.query_params)

    # Contexto vacío por defecto.
    contexto = ""
    # Si hay sesión MCP...
    if mcp_session is not None:
        # ...intenta consultar.
        try:
            # Llama a la herramienta MCP.
            contexto = await llamar_herramienta_mcp(filtro)
        # Si falla...
        except Exception as e:
            # ...lo registra...
            print(f"[MCP] Error en /api/fundacion: {e}")
            # ...y deja el contexto vacío.
            contexto = ""

    # Respaldo directo si la sesión MCP no está disponible
    # Si no hay contexto...
    if not contexto:
        # ...intenta usar la función de server.py directamente.
        try:
            # Importa la herramienta localmente.
            from server import consultar_fundacion_las_varillas
            # Ejecuta la consulta sin pasar por MCP.
            contexto = consultar_fundacion_las_varillas(filtro)
        # Si falla...
        except Exception as e:
            # ...responde error 500.
            return JSONResponse({"error": f"Error al consultar la base histórica: {e}"}, status_code=500)

    # Intenta responder con el JSON del contexto.
    try:
        # Respuesta 200 con el JSON interpretado.
        return JSONResponse(json.loads(contexto), status_code=200)
    # Si el contexto es solo un mensaje de texto...
    except Exception:
        # ...lo envuelve en un objeto JSON.
        return JSONResponse({"mensaje": contexto, "resultados": []}, status_code=200)


# [SRP] Responsabilidad única: leer los parámetros de chat (antes repetido 3 veces:
# chat_endpoint, chat_stream_endpoint y websocket_chat_endpoint).
def obtener_parametros_chat(body):
    """Devuelve (pregunta, use_mcp, model) a partir del cuerpo recibido."""
    # Pregunta sin espacios sobrantes.
    pregunta = body.get("message", "").strip()
    # Si usar MCP (por defecto sí).
    use_mcp = body.get("use_mcp", True)
    # Modelo pedido (por defecto el configurado).
    model = body.get("model", MODEL)
    # Devuelve los tres valores.
    return pregunta, use_mcp, model


# Endpoint de chat sin streaming.
async def chat_endpoint(request):
    """Consulta HTTP directa, sin streaming (compatible con pruebas de carga)."""
    # Intenta leer el JSON.
    try:
        # Lee el cuerpo.
        body = await request.json()
    # Si no es JSON válido...
    except Exception:
        # ...responde 400.
        return JSONResponse({"error": "Formato JSON inválido"}, status_code=400)

    # Extrae los parámetros con la función dedicada.
    pregunta, use_mcp, model = obtener_parametros_chat(body)

    # Si la pregunta está vacía...
    if not pregunta:
        # ...responde 400.
        return JSONResponse({"error": "El mensaje no puede estar vacío"}, status_code=400)

    # Busca contexto en el libro.
    contexto, mcp_info = await consultar_mcp(pregunta, use_mcp)

    # Protege la llamada al modelo.
    try:
        # Cliente HTTP con timeout largo.
        async with httpx.AsyncClient(timeout=600.0) as client:
            # Envía la pregunta a Ollama (sin streaming).
            resp = await client.post(
                # Dirección de Ollama.
                OLLAMA_URL,
                # Cuerpo de la petición.
                json={"model": model, "messages": construir_mensajes(pregunta, contexto), "stream": False}
            # Cierra la llamada.
            )
            # Lanza excepción si hubo error HTTP.
            resp.raise_for_status()
            # Extrae el texto de la respuesta.
            reply = resp.json().get("message", {}).get("content", "")
            # Devuelve la respuesta y los datos MCP.
            return JSONResponse({"reply": reply, "mcp": mcp_info}, status_code=200)
    # Si el modelo tarda demasiado...
    except httpx.TimeoutException:
        # ...responde con aviso controlado.
        return JSONResponse({
            # Mensaje de demora.
            "reply": "La respuesta está tardando más de lo habitual. Inténtalo de nuevo en unos segundos.",
            # Datos MCP.
            "mcp": mcp_info,
            # Estado especial.
            "status": "overload_controlled"
        # Cierra la respuesta.
        }, status_code=200)
    # Cualquier otro error del modelo...
    except Exception as e:
        # ...se registra...
        print(f"[LLM] Error en /api/chat: {e!r}")
        # ...y se responde con el respaldo del libro.
        return JSONResponse({
            # Respuesta construida desde el libro.
            "reply": respuesta_desde_libro(mcp_info.get("chunks", [])),
            # Marca de error.
            "error": "modelo_no_disponible",
            # Datos MCP.
            "mcp": mcp_info
        # Cierra la respuesta.
        }, status_code=200)


# Endpoint de chat con streaming (SSE).
async def chat_stream_endpoint(request):
    """Consulta con streaming en tiempo real (Server-Sent Events)."""
    # Intenta leer el JSON.
    try:
        # Lee el cuerpo.
        body = await request.json()
    # Si no es JSON válido...
    except Exception:
        # ...responde 400.
        return JSONResponse({"error": "Formato JSON inválido"}, status_code=400)

    # Extrae los parámetros con la función dedicada.
    pregunta, use_mcp, model = obtener_parametros_chat(body)

    # Si la pregunta está vacía...
    if not pregunta:
        # ...responde 400.
        return JSONResponse({"error": "El mensaje no puede estar vacío"}, status_code=400)

    # [SRP] Función mínima que da formato SSE a un evento.
    def sse(payload: dict) -> str:
        # Formato "data: <json>" terminado en línea en blanco.
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    # Generador de eventos que se envía al navegador.
    async def event_generator():
        # Busca contexto en el libro.
        contexto, mcp_data = await consultar_mcp(pregunta, use_mcp)
        # Primer evento: contexto MCP (fuentes).
        yield sse({"type": "mcp_context", "mcp": mcp_data})

        # Recorre los eventos generados por el modelo/respaldo.
        async for kind, value in generar_respuesta(pregunta, contexto, mcp_data.get("chunks", []), model):
            # Si es un token...
            if kind == "token":
                # ...lo envía.
                yield sse({"type": "token", "token": value})
            # Si es un error...
            else:
                # ...lo envía...
                yield sse({"type": "error", "error": value})
                # ...y termina.
                return
        # Evento final: respuesta completa.
        yield sse({"type": "done"})

    # Devuelve la respuesta en streaming.
    return StreamingResponse(
        # Generador de eventos.
        event_generator(),
        # Tipo de contenido SSE.
        media_type="text/event-stream",
        # Cabeceras para evitar caché y buffering.
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    # Cierra la respuesta.
    )


# Endpoint de chat por WebSocket.
async def websocket_chat_endpoint(websocket: WebSocket):
    """Chat bidireccional por WebSocket en /ws/chat (se mantiene por compatibilidad)."""
    # Acepta la conexión.
    await websocket.accept()
    # Protege todo el ciclo de la conexión.
    try:
        # Atiende mensajes mientras la conexión siga abierta.
        while True:
            # Espera un mensaje de texto.
            raw_data = await websocket.receive_text()
            # Intenta interpretarlo como JSON.
            try:
                # Convierte el texto en diccionario.
                body = json.loads(raw_data)
            # Si no es JSON válido...
            except Exception:
                # ...avisa al cliente...
                await websocket.send_json({"type": "error", "error": "Formato JSON inválido"})
                # ...y espera el siguiente mensaje.
                continue

            # Extrae los parámetros con la función dedicada.
            pregunta, use_mcp, model = obtener_parametros_chat(body)

            # Si la pregunta está vacía...
            if not pregunta:
                # ...avisa al cliente...
                await websocket.send_json({"type": "error", "error": "El mensaje no puede estar vacío"})
                # ...y espera el siguiente mensaje.
                continue

            # Busca contexto en el libro.
            contexto, mcp_data = await consultar_mcp(pregunta, use_mcp)
            # Envía el contexto MCP.
            await websocket.send_json({"type": "mcp_context", "mcp": mcp_data})

            # Bandera: la respuesta terminó bien.
            ok = True
            # Recorre los eventos generados.
            async for kind, value in generar_respuesta(pregunta, contexto, mcp_data.get("chunks", []), model):
                # Si es un token...
                if kind == "token":
                    # ...lo envía.
                    await websocket.send_json({"type": "token", "token": value})
                # Si es un error...
                else:
                    # ...lo envía...
                    await websocket.send_json({"type": "error", "error": value})
                    # ...marca que no terminó bien...
                    ok = False
                    # ...y corta.
                    break
            # Si terminó bien...
            if ok:
                # ...envía el evento final.
                await websocket.send_json({"type": "done"})

    # Si el cliente se desconecta...
    except (WebSocketDisconnect, RuntimeError):
        # ...se ignora (es normal).
        pass
    # Cualquier otro error...
    except Exception as e:
        # ...se registra.
        print(f"[WebSocket] {e}")


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
# [SRP] Responsabilidad única: crear el montaje de una carpeta estática.
def _static(name: str) -> Mount:
    # Ruta de la carpeta en disco.
    path = os.path.join(BASE_DIR, name)
    # La crea si no existe.
    os.makedirs(path, exist_ok=True)
    # Devuelve el montaje en /<nombre>.
    return Mount(f"/{name}", app=StaticFiles(directory=path), name=name)


# [OCP] Para agregar un endpoint o carpeta estática se agrega una línea acá, sin tocar el resto.
# Tabla de rutas de la aplicación.
routes = [
    # Página principal.
    Route("/", endpoint=serve_index),
    # Estado del sistema.
    Route("/api/status", endpoint=get_status, methods=["GET"]),
    # Libro histórico.
    Route("/api/fundacion", endpoint=fundacion_endpoint, methods=["GET", "POST"]),
    # Chat sin streaming.
    Route("/api/chat", endpoint=chat_endpoint, methods=["POST"]),
    # Chat con streaming.
    Route("/api/chat/stream", endpoint=chat_stream_endpoint, methods=["POST"]),
    # Chat por WebSocket.
    WebSocketRoute("/ws/chat", endpoint=websocket_chat_endpoint),
    # Archivos CSS.
    _static("css"),
    # Archivos JS.
    _static("js"),
    # Imágenes/logos.
    _static("assets"),
    # Datos (bienvenida.json).
    _static("data"),
# Cierra la tabla de rutas.
]

# Lista de middlewares.
middleware = [
    # Permite peticiones desde cualquier origen (CORS abierto).
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
# Cierra la lista.
]

# [SRP] Responsabilidad única: controlar la caché del navegador.
# [OCP] Es un middleware aparte: se agrega a la app sin modificar ningún endpoint.
class NoCacheMiddleware:
    """Evita que el navegador reutilice archivos viejos (HTML, CSS, JS, datos)."""
    # Constructor: guarda la app a envolver.
    def __init__(self, app):
        # Guarda la aplicación interna.
        self.app = app

    # Se ejecuta en cada petición.
    async def __call__(self, scope, receive, send):
        # Solo actúa sobre peticiones HTTP (no WebSocket/lifespan).
        if scope["type"] != "http":
            # Las demás pasan sin cambios.
            return await self.app(scope, receive, send)

        # Envoltorio del envío de respuesta.
        async def send_wrapper(message):
            # Solo modifica el inicio de la respuesta.
            if message["type"] == "http.response.start":
                # Quita cualquier cabecera Cache-Control existente.
                headers = [h for h in message.get("headers", []) if h[0].lower() != b"cache-control"]
                # Agrega Cache-Control: no-cache.
                headers.append((b"cache-control", b"no-cache, must-revalidate"))
                # Reemplaza las cabeceras del mensaje.
                message["headers"] = headers
            # Envía el mensaje (modificado o no).
            await send(message)

        # Continúa con la app usando el envoltorio.
        await self.app(scope, receive, send_wrapper)


# Crea la aplicación Starlette con ciclo de vida, rutas y middleware.
app = Starlette(lifespan=lifespan, routes=routes, middleware=middleware)
# Agrega el middleware de no-caché.
app.add_middleware(NoCacheMiddleware)


# Solo se ejecuta si el archivo se lanza directamente.
if __name__ == "__main__":
    # Importa el servidor ASGI.
    import uvicorn

    # Host configurable (por defecto todas las interfaces).
    host = os.environ.get("HOST", "0.0.0.0")
    # Puerto configurable (por defecto 8000).
    port = int(os.environ.get("PORT", "8000"))
    # URL local para mostrar/abrir.
    url = f"http://localhost:{port}"

    # Línea decorativa superior.
    print("\n========================================================")
    # Mensaje de listo.
    print(f"  VÍA está lista en {url}")
    # Línea decorativa inferior.
    print("========================================================\n")

    # Si no se desactivó la apertura automática...
    if os.environ.get("VIA_OPEN_BROWSER", "1") != "0":
        # ...abre el navegador a los 1,5 segundos.
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    # Inicia el servidor web.
    uvicorn.run(app, host=host, port=port, reload=False)
