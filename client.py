# =============================================================================
# client.py · Cliente MCP interactivo por consola (MCP + Ollama)
# -----------------------------------------------------------------------------
# AUDITORÍA SOLID (resumen de este archivo):
#   - ANTES: `main()` mezclaba 5 responsabilidades: conectar al servidor MCP,
#     leer la consola, armar el prompt, llamar a Ollama e imprimir errores.
#   - AHORA: el armado del prompt y la llamada a Ollama viven en funciones
#     propias (SRP). `main()` queda como orquestador del flujo.
#   - Los textos de los prompts, los mensajes por consola y el orden de las
#     operaciones son BYTE A BYTE los mismos que antes.
#   - NO se cambió (y se documenta en la auditoría): `requests.post` es
#     bloqueante dentro de código async, y `extraer_texto_mcp` / constantes de
#     Ollama están duplicados con web_server.py. Corregirlo cambiaría el
#     comportamiento o la estructura de archivos, y se pidió no tocarlos.
# =============================================================================

# Librería estándar para el bucle de eventos asíncrono.
import asyncio
# Librería estándar para rutas de archivos.
import os
# Librería estándar para obtener el intérprete Python actual.
import sys
# Cliente HTTP síncrono usado para hablar con Ollama.
import requests
# Librería estándar JSON (se conserva el import original).
import json
# [DIP] Se usa el cliente MCP estándar (abstracción del protocolo), no sockets propios.
from mcp.client.stdio import stdio_client, StdioServerParameters
# Sesión de cliente MCP.
from mcp import ClientSession


# [SRP] Responsabilidad única: convertir una respuesta MCP en texto plano.
def extraer_texto_mcp(resultado):
    """Extrae el contenido textual de una respuesta MCP."""
    # Si no hay resultado o no tiene "content", devuelve cadena vacía.
    if not resultado or not hasattr(resultado, "content"):
        # Entrada inválida -> texto vacío.
        return ""
    # Une con saltos de línea el texto de cada bloque que tenga atributo "text".
    return "\n".join(bloque.text for bloque in resultado.content if hasattr(bloque, "text"))

# URL del endpoint de chat de Ollama (local).
OLLAMA_URL = "http://localhost:11434/api/chat"
# Modelo de lenguaje a utilizar.
MODEL = "llama3.2"


# [SRP] Responsabilidad única: construir el prompt del sistema.
def construir_system_prompt(indice_str):
    """System Prompt dinámico con el índice inyectado."""
    # Devuelve el texto del prompt (cada línea del literal se conserva idéntica).
    return (
        # Rol del asistente.
        "Eres un historiador experto en la ciudad de Las Varillas (Córdoba, Argentina). "
        # Inyecta el índice de la biblioteca.
        f"Aquí tienes el índice de tu biblioteca de conocimientos históricos:\n{indice_str}\n\n"
        # Encabezado de reglas.
        "INSTRUCCIONES CRÍTICAS:\n"
        # Regla 1: usar solo la base de datos.
        "- Respondé SOLAMENTE utilizando la información verídica recuperada de la base de datos adjunta.\n"
        # Regla 2: qué responder si no hay datos.
        "- Si el contexto dice 'No se encontraron datos históricos', indicá amablemente que no contás con esa información.\n"
        # Regla 3: precisión en nombres y fechas.
        "- Sé preciso con fechas, nombres de historiadores (ej. Valter Dabbene), instituciones (ej. Centro de Estudios Parada KM 81) y fundadores (ej. José Medardo Álvarez)."
    # Cierra el paréntesis del prompt.
    )


# [SRP] Responsabilidad única: armar la lista de mensajes para el modelo.
def construir_mensajes(pregunta, contexto, system_prompt):
    """Arma los mensajes (sistema + usuario) que se envían a Ollama."""
    # Devuelve la lista de mensajes.
    return [
        # Mensaje de sistema.
        {
            # Rol "system".
            "role": "system",
            # Contenido del prompt del sistema.
            "content": system_prompt
        # Cierra el mensaje de sistema.
        },
        # Mensaje del usuario.
        {
            # Rol "user".
            "role": "user",
            # Texto con la pregunta y el contexto (el literal conserva su formato exacto).
            "content": f"""
Pregunta del usuario:
{pregunta}

Información recuperada de la base de datos histórica:
{contexto}

Generá una respuesta clara, precisa y fidedigna basada únicamente en la información recuperada.
"""
        # Cierra el mensaje del usuario.
        }
    # Cierra la lista.
    ]


# [SRP] Responsabilidad única: comunicarse con Ollama.
# [DIP] Si se cambia de proveedor de LLM, solo se toca esta función.
def consultar_ollama(mensajes):
    """Llama a Ollama (timeout ampliado a 240s) y devuelve el JSON de respuesta."""
    # 5. Llamada a Ollama con timeout ampliado a 240s
    # Envía la petición POST al modelo.
    response = requests.post(
        # Dirección de Ollama.
        OLLAMA_URL,
        # Cuerpo JSON de la petición.
        json={
            # Modelo a usar.
            "model": MODEL,
            # Mensajes de la conversación.
            "messages": mensajes,
            # Respuesta completa (sin streaming).
            "stream": False
        # Cierra el cuerpo JSON.
        },
        # Espera máxima de 240 segundos.
        timeout=240
    # Cierra la llamada.
    )

    # Lanza excepción si Ollama respondió con error HTTP.
    response.raise_for_status()

    # Devuelve el JSON de la respuesta.
    return response.json()


# [SRP] `main` ahora orquesta el flujo: conectar -> preguntar -> mostrar.
# Función principal asíncrona del cliente.
async def main():

    # Configuración del servidor MCP usando el mismo interprete Python del entorno virtual
    # Ruta absoluta de server.py (junto a este archivo).
    server_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    # Parámetros para lanzar el servidor MCP como subproceso.
    server_params = StdioServerParameters(
        # Usa el mismo intérprete Python que ejecuta este script.
        command=sys.executable,
        # Argumento: la ruta de server.py.
        args=[server_path]
    # Cierra los parámetros.
    )

    # Conexión con el servidor MCP
    # Abre la conexión stdio con el servidor (se cierra sola al salir).
    async with stdio_client(server_params) as (read, write):

        # Abre la sesión MCP sobre esa conexión.
        async with ClientSession(read, write) as session:

            # 1. Inicializar sesión MCP
            # Handshake inicial del protocolo MCP.
            await session.initialize()
            # Informa la conexión exitosa.
            print("\nCliente MCP conectado correctamente")

            # 2. Carga Automática e Inyección de Índice
            # Informa que se recupera el índice.
            print("[MCP] Recuperando índice de la biblioteca...")
            # Pide el índice (tema vacío).
            res_indice = await session.call_tool(
                # Nombre de la herramienta MCP.
                "consultar_fundacion_las_varillas",
                # Tema vacío = modo índice.
                arguments={"tema": ""}
            # Cierra la llamada.
            )
            # Convierte la respuesta en texto.
            indice_str = extraer_texto_mcp(res_indice)
            # Informa que el índice quedó cargado.
            print("[MCP] Índice cargado e inyectado con éxito.")

            # Bucle de preguntas hasta que el usuario escriba "salir".
            while True:

                # Lee la pregunta desde la consola.
                pregunta = input("\nPregunta (o escribir 'salir'): ")

                # Si el usuario escribe "salir" (sin importar mayúsculas)...
                if pregunta.lower() == "salir":
                    # ...muestra el mensaje de cierre...
                    print("\nCerrando cliente...")
                    # ...y sale del bucle.
                    break

                # Bloque protegido: cualquier error se informa sin cerrar el programa.
                try:

                    # Informa qué se está buscando.
                    print(f"\n[MCP] Buscando información sobre '{pregunta}'...")

                    # 3. Búsqueda inteligente filtrando por el tema preguntado
                    # Consulta la herramienta MCP con la pregunta como tema.
                    resultado = await session.call_tool(
                        # Nombre de la herramienta.
                        "consultar_fundacion_las_varillas",
                        # Argumentos de la herramienta.
                        arguments={
                            # La pregunta completa se usa como tema.
                            "tema": pregunta
                        # Cierra los argumentos.
                        }
                    # Cierra la llamada.
                    )

                    # Convierte la respuesta MCP en texto (contexto histórico).
                    contexto = extraer_texto_mcp(resultado)

                    # Encabezado de la información recuperada.
                    print("\n[MCP] Información obtenida:")
                    # Muestra el contexto recuperado.
                    print(contexto)

                    # 4. System Prompt Dinámico con el Índice inyectado
                    # Construye el prompt del sistema con el índice.
                    system_prompt = construir_system_prompt(indice_str)

                    # Construye los mensajes que se enviarán al modelo.
                    mensajes = construir_mensajes(pregunta, contexto, system_prompt)

                    # 5. Llamada a Ollama con timeout ampliado a 240s
                    # Consulta al modelo y obtiene su respuesta JSON.
                    data = consultar_ollama(mensajes)

                    # Encabezado de la respuesta final.
                    print("\nRespuesta final:\n")
                    # Imprime el texto generado por el modelo.
                    print(data["message"]["content"])

                # Error: Ollama no está accesible.
                except requests.exceptions.ConnectionError:
                    # Informa que no se pudo conectar.
                    print(f"\n[Error de conexión con Ollama]: No se pudo conectar a {OLLAMA_URL}.")
                    # Sugiere verificar que Ollama esté abierto.
                    print("Verificá que Ollama esté instalado y abierto en tu computadora.")
                # Error HTTP devuelto por Ollama.
                except requests.exceptions.HTTPError as e:
                    # Informa el código de estado HTTP.
                    print(f"\n[Error de Ollama ({e.response.status_code})]:")
                    # Probable causa: el modelo no está descargado.
                    print(f"Es probable que el modelo '{MODEL}' no esté descargado.")
                    # Indica cómo descargarlo.
                    print(f"Probá ejecutar en una terminal: ollama run {MODEL}")
                # Cualquier otro error inesperado.
                except Exception as e:
                    # Muestra el error.
                    print(f"\nError durante la consulta: {e}")


# Solo se ejecuta si el archivo se lanza directamente.
if __name__ == "__main__":
    # Intenta correr el programa asíncrono.
    try:
        # Ejecuta la función principal.
        asyncio.run(main())
    # Si el usuario presiona Ctrl+C...
    except KeyboardInterrupt:
        # ...se despide con el mensaje original.
        print("\nPrograma finalizado")
