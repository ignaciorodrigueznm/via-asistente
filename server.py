# =============================================================================
# server.py · Servidor MCP del libro histórico de Las Varillas
# -----------------------------------------------------------------------------
# AUDITORÍA SOLID (resumen de este archivo):
#   - ANTES: una sola función (`consultar_fundacion_las_varillas`) hacía TODO:
#     cargar datos, armar el índice, normalizar la consulta, detectar el
#     "resumen global", puntuar documentos, filtrar por relevancia y
#     serializar a JSON.  -> violaba SRP (y dificultaba OCP).
#   - AHORA: cada responsabilidad vive en su propia función pequeña. La
#     herramienta MCP queda como "orquestador" y devuelve EXACTAMENTE lo mismo
#     que antes (mismas salidas, mismos textos, mismo orden).
#   - Nada cambia hacia afuera: el nombre de la herramienta, sus parámetros y
#     su resultado son idénticos (LSP/ISP: el contrato público no se rompe).
# =============================================================================

# [DIP] Se depende de la abstracción FastMCP (framework), no de un servidor concreto.
from mcp.server.fastmcp import FastMCP
# Librería estándar para leer/escribir JSON.
import json
# Librería estándar para construir rutas de archivos.
import os
# Librería estándar de expresiones regulares (limpieza de texto).
import re
# Librería estándar para quitar tildes (normalización Unicode).
import unicodedata

# Crea la instancia del servidor MCP con el nombre público "HistoriaVarillas".
mcp = FastMCP("HistoriaVarillas")

# Carpeta donde vive este archivo (base para encontrar los datos).
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ruta completa del archivo JSON con los fragmentos históricos.
DATA_FILE = os.path.join(BASE_DIR, "fundacion.json")

# Palabras vacías comunes en español que no aportan especificidad en la búsqueda
# [OCP] Se pueden agregar/quitar palabras acá sin tocar la lógica de búsqueda.
STOPWORDS = {
    # Artículos y preposiciones básicas.
    "a", "al", "de", "del", "el", "la", "los", "las", "un", "una", "unos", "unas",
    # Preposiciones, conjunciones y pronombres frecuentes.
    "en", "por", "para", "con", "y", "o", "u", "que", "se", "su", "sus", "es", "son",
    # Demostrativos y palabras típicas de las preguntas del chat.
    "como", "esta", "este", "estos", "estas", "dice", "postura", "sobre", "dame",
    # Pronombres interrogativos/posesivos.
    "me", "mi", "cual", "cuales", "quien", "quienes"
# Cierra el conjunto de stopwords.
}


# [SRP] Responsabilidad única: normalizar texto (nada más).
def normalizar(texto: str) -> str:
    """Convierte a minúsculas, elimina tildes y signos de puntuación."""
    # Si el texto es vacío/None, devuelve cadena vacía para evitar errores.
    if not texto:
        # Resultado para entrada vacía.
        return ""
    # Pasa todo a minúsculas.
    texto = texto.lower()
    # Eliminar tildes
    # Descompone los acentos (NFKD), descarta lo no-ASCII y vuelve a texto.
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    # Reemplazar signos de puntuación por espacios
    # Todo lo que no sea letra/número/espacio se convierte en espacio.
    texto = re.sub(r"[^\w\s]", " ", texto)
    # Devuelve el texto ya normalizado.
    return texto


# [DIP] Punto único de acceso a datos: consulta MongoBookRepository y vigila meta.version.
# Si Mongo no está disponible, mantiene fallback a fundacion.json (Criterio A4 / 1.1).
_repo_cache_version: int = -1
_cached_data: list = []
_book_repo = None


def obtener_repo_mcp():
    """Obtiene o inicializa el repositorio para el servidor MCP con conexión síncrona PyMongo."""
    global _book_repo
    if _book_repo is not None:
        return _book_repo
    try:
        from pymongo import MongoClient
        from config import settings
        from repository import MongoBookRepository
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=1500)
        client.admin.command("ping")
        db = client[settings.MONGODB_DB]
        _book_repo = MongoBookRepository(db)
        return _book_repo
    except Exception:
        return None


def cargar_datos():
    """
    Lee fragmentos desde MongoDB si está disponible y vigila meta.version (Criterio A4).
    Si meta.version no cambió, devuelve la caché en memoria.
    Si Mongo no está disponible, lee fundacion.json (comportamiento previo asegurado).
    """
    global _repo_cache_version, _cached_data
    repo = obtener_repo_mcp()

    if repo is not None:
        try:
            version_actual = repo.obtener_version_corpus()
            # Si la versión no cambió y ya tenemos datos cacheados, retornar caché
            if version_actual == _repo_cache_version and _cached_data:
                return _cached_data

            # Carga fragmentos de todos los libros publicados
            libros_pub = repo.listar_libros(solo_publicados=True)
            todos_frags = []
            for l in libros_pub:
                frags = repo.obtener_fragmentos(l["slug"])
                todos_frags.extend(frags)

            if todos_frags:
                _repo_cache_version = version_actual
                _cached_data = todos_frags
                return _cached_data
        except Exception as e:
            # En caso de error de red puntual, continuar con fallback
            pass

    # Fallback transparente a fundacion.json
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)



# [SRP] Responsabilidad única: serializar resultados a JSON.
# Antes este mismo json.dumps estaba repetido 4 veces en la función principal.
def a_json(objeto) -> str:
    """Serializa con el mismo formato de siempre (UTF-8 legible, sangría 2)."""
    # Convierte a texto JSON sin escapar tildes y con sangría de 2 espacios.
    return json.dumps(objeto, ensure_ascii=False, indent=2)


# [SRP] Responsabilidad única: construir el "Modo Índice" (id, título, tags).
def construir_indice(datos) -> str:
    """MODO 1: devuelve solo id, título y tags de cada documento."""
    # Lista donde se acumulan los elementos del índice.
    indice = []
    # Recorre cada documento de la base.
    for doc in datos:
        # Agrega una versión liviana del documento (sin el contenido largo).
        indice.append({
            # Identificador único del fragmento.
            "id": doc.get("id"),
            # Título del fragmento.
            "titulo": doc.get("titulo"),
            # Etiquetas; lista vacía si no existen.
            "tags": doc.get("tags", [])
        # Cierra el diccionario y el append.
        })
    # Devuelve el índice como JSON.
    return a_json(indice)


# [SRP] Responsabilidad única: interpretar la consulta del usuario.
def extraer_palabras_clave(tema_norm: str):
    """Separa la consulta en palabras útiles (sin stopwords)."""
    # Parte la consulta en palabras y descarta las de 1 letra.
    palabras = [p for p in tema_norm.split() if len(p) > 1]
    # Quita las stopwords (palabras vacías).
    palabras_clave = [p for p in palabras if p not in STOPWORDS]

    # Si todas las palabras eran stopwords, usamos las palabras originales
    if not palabras_clave:
        # Plan B: usar todas las palabras para no quedar sin criterio.
        palabras_clave = palabras

    # Devuelve las palabras con las que se va a buscar.
    return palabras_clave


# [SRP] Responsabilidad única: decidir si el usuario pide "todo / resumen".
# [OCP] Si se agregan nuevas formas de pedir "todo", se extiende acá.
def es_consulta_global(palabras_clave) -> bool:
    """Detecta si el usuario pide un resumen global de las tres teorías."""
    # Devuelve True si aparece "tres", "resumen" o "todas",
    # o si pregunta solo por "teorías" (máx. 2 palabras clave).
    return (
        # Alguna palabra de resumen global presente.
        any(w in palabras_clave for w in ["tres", "resumen", "todas"]) or
        # O la palabra "teorias" en una consulta corta.
        ("teorias" in palabras_clave and len(palabras_clave) <= 2)
    # Cierra la expresión booleana.
    )


# [SRP] Responsabilidad única: preparar el texto de un documento para buscar.
def preparar_documento(doc):
    """Devuelve (id normalizado, texto completo normalizado) de un documento."""
    # Normaliza el id.
    id_norm = normalizar(doc.get("id", ""))
    # Normaliza el título.
    titulo_norm = normalizar(doc.get("titulo", ""))
    # Normaliza el contenido.
    contenido_norm = normalizar(doc.get("contenido", ""))
    # Normaliza las etiquetas unidas en un solo texto.
    tags_norm = normalizar(" ".join(doc.get("tags", [])))
    # Normaliza los valores de metadata unidos en un solo texto.
    meta_norm = normalizar(" ".join(str(v) for v in doc.get("metadata", {}).values()))

    # Une todos los campos en un único texto buscable.
    texto_doc = f"{id_norm} {titulo_norm} {contenido_norm} {tags_norm} {meta_norm}"
    # Devuelve el id (para coincidencia exacta) y el texto completo.
    return id_norm, texto_doc


# [SRP] Responsabilidad única: calcular el puntaje de relevancia.
# [OCP] Para cambiar el criterio de ranking se modifica solo esta función.
def calcular_puntaje(texto_doc: str, palabras_clave) -> int:
    """Suma 2 puntos por palabra exacta y 1 por coincidencia parcial."""
    # Conjunto de palabras exactas del documento (búsqueda rápida).
    tokens_doc = set(texto_doc.split())
    # Puntaje inicial en cero.
    score = 0
    # Revisa cada palabra clave de la consulta.
    for palabra in palabras_clave:
        # Coincidencia de palabra completa = 2 puntos.
        if palabra in tokens_doc:
            # Suma 2 puntos.
            score += 2
        # Coincidencia parcial (dentro de otra palabra) = 1 punto.
        elif palabra in texto_doc:
            # Suma 1 punto.
            score += 1
    # Devuelve el puntaje total.
    return score


# [SRP] Responsabilidad única: quedarse con los resultados más relevantes.
def filtrar_mas_relevantes(resultados_con_score):
    """Ordena por puntaje y conserva los que llegan al 70% del mejor."""
    # Ordenar por relevancia descendente
    resultados_con_score.sort(key=lambda x: x[0], reverse=True)
    # El mejor puntaje es el primero tras ordenar.
    max_score = resultados_con_score[0][0]

    # Filtrar quirúrgicamente los que tengan relevancia suficiente
    # Conserva solo documentos con puntaje >= 70% del máximo.
    return [doc for score, doc in resultados_con_score if score >= max_score * 0.7]


# [SRP] Esta función ahora SOLO orquesta: coordina las piezas de arriba.
# [LSP/ISP] El contrato público (nombre, parámetro `tema`, salida str) no cambió.
# Registra la función como herramienta MCP.
@mcp.tool()
# Herramienta pública del servidor (misma firma que antes).
def consultar_fundacion_las_varillas(tema: str = "") -> str:
    """
    Consulta la base de datos histórica de Las Varillas (Córdoba, Argentina).
    - Si 'tema' está vacío (""), devuelve un índice de todos los temas disponibles.
    - Si 'tema' tiene texto, busca de forma inteligente por palabras clave en
      identificadores, títulos, contenidos, etiquetas y metadatos.
    """
    # Lee los datos (única dependencia de datos).
    datos = cargar_datos()

    # Si no hay datos, avisa con el mismo mensaje de siempre.
    if not datos:
        # Mensaje original sin cambios.
        return "No se encontraron datos históricos cargados."

    # MODO 1: Devolver solo el Índice si 'tema' está vacío
    # Tema vacío o solo espacios -> índice.
    if not tema or not tema.strip():
        # Devuelve el índice.
        return construir_indice(datos)

    # MODO 2: Búsqueda inteligente por palabras clave
    # Normaliza la consulta del usuario.
    tema_norm = normalizar(tema)
    # Obtiene las palabras relevantes de la consulta.
    palabras_clave = extraer_palabras_clave(tema_norm)

    # Detectar si el usuario pide un resumen global de las tres teorías
    # Si pide un resumen global, devuelve todos los documentos completos.
    if es_consulta_global(palabras_clave):
        # Devuelve toda la base.
        return a_json(datos)

    # Evaluar relevancia de cada documento
    # Acumulador de pares (puntaje, documento).
    resultados_con_score = []
    # Recorre todos los documentos.
    for doc in datos:
        # Prepara el id y el texto buscable del documento.
        id_norm, texto_doc = preparar_documento(doc)

        # Búsqueda por ID exacto o año explícito
        # Si la consulta es exactamente el id del documento, lo devuelve solo.
        if tema_norm.strip() == id_norm:
            # Devuelve únicamente ese documento.
            return a_json([doc])

        # Calcular coincidencias de palabras clave
        # Calcula la relevancia del documento para la consulta.
        score = calcular_puntaje(texto_doc, palabras_clave)

        # Solo guarda documentos con alguna coincidencia.
        if score > 0:
            # Agrega el par (puntaje, documento).
            resultados_con_score.append((score, doc))

    # Si ningún documento coincidió, devuelve el mensaje original.
    if not resultados_con_score:
        # Mensaje original sin cambios.
        return f"No se encontraron datos históricos relacionados con '{tema}'."

    # Se queda con los más relevantes y los serializa.
    return a_json(filtrar_mas_relevantes(resultados_con_score))


# Solo se ejecuta si el archivo se lanza directamente (no al importarlo).
if __name__ == "__main__":
    # Inicia el servidor MCP (transporte stdio por defecto).
    mcp.run()
