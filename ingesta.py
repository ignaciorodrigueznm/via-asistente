"""
ingesta.py · Funciones puras de limpieza y fragmentación semántica para el pipeline de ingesta.
Cumple el criterio de aceptación B6 de specs/02-carga-por-partes/spec.md y secciones 3.1, 5.1 del Taller MCP 3.
"""
import re
from typing import List, Dict, Any


def limpiar_texto(texto: str) -> str:
    """
    Limpia el texto inicial:
    - Remueve el Byte Order Mark (BOM) UTF-8 (\ufeff) si estuviera presente.
    - Normaliza los saltos de línea Windows/Mac a formato estándar Unix (\n).
    - Remueve espacios en blanco sobrantes al inicio y final.
    """
    if not texto:
        return ""
    if texto.startswith("\ufeff"):
        texto = texto[1:]
    # Normalizar saltos de línea
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    return texto.strip()


def _es_titulo(linea: str) -> bool:
    """Detecta si una línea es un título Markdown (# o ##)."""
    return bool(re.match(r"^#{1,3}\s+", linea.strip()))


def _extraer_titulo_limpio(linea: str) -> str:
    """Quita los prefijos '#' y devuelve el texto limpio del título."""
    return re.sub(r"^#{1,3}\s+", "", linea.strip()).strip()


def fragmentar_texto(
    slug: str,
    texto: str,
    min_chars: int = 800,
    max_chars: int = 1500
) -> List[Dict[str, Any]]:
    """
    Fragmenta semánticamente un texto completo en bloques equilibrados (~800-1500 caracteres).
    Reglas del contrato (sección 5.1 y Criterio B6):
    - Respeta títulos (# o ##) como cortes de sección.
    - Dentro de una sección agrupa párrafos sin superar max_chars.
    - Si un párrafo o fragmento es menor a min_chars, se une con su vecino.
    - Nunca corta una frase a la mitad.
    - Genera el id en formato {slug}_{orden:02d}.
    """
    texto = limpiar_texto(texto)
    if not texto:
        return []

    # Dividir el texto en bloques delimitados por saltos de línea dobles o títulos
    lineas = texto.split("\n")
    secciones_raw = []
    
    seccion_actual = "General"
    titulo_actual = "Inicio"
    parrafos_acumulados: List[str] = []

    for linea in lineas:
        linea_str = linea.strip()
        if not linea_str:
            continue

        if _es_titulo(linea_str):
            # Guardar el bloque previo si tiene párrafos
            if parrafos_acumulados:
                secciones_raw.append({
                    "seccion": seccion_actual,
                    "titulo": titulo_actual,
                    "texto": "\n\n".join(parrafos_acumulados)
                })
                parrafos_acumulados = []
            
            titulo_limpio = _extraer_titulo_limpio(linea_str)
            seccion_actual = titulo_limpio
            titulo_actual = titulo_limpio
        else:
            parrafos_acumulados.append(linea_str)

    if parrafos_acumulados:
        secciones_raw.append({
            "seccion": seccion_actual,
            "titulo": titulo_actual,
            "texto": "\n\n".join(parrafos_acumulados)
        })

    # Ahora procesamos cada sección agrupando párrafos respetando [min_chars, max_chars]
    bloques_finales: List[Dict[str, str]] = []

    for sec in secciones_raw:
        parrafos = sec["texto"].split("\n\n")
        buffer_parrafos: List[str] = []
        chars_buffer = 0

        for p in parrafos:
            p_len = len(p)
            # Si agregar este párrafo excede max_chars y ya tenemos contenido en buffer
            if chars_buffer + p_len > max_chars and buffer_parrafos:
                bloques_finales.append({
                    "seccion": sec["seccion"],
                    "titulo": sec["titulo"],
                    "contenido": "\n\n".join(buffer_parrafos).strip()
                })
                buffer_parrafos = [p]
                chars_buffer = p_len
            else:
                buffer_parrafos.append(p)
                chars_buffer += p_len + 2

        if buffer_parrafos:
            contenido_resto = "\n\n".join(buffer_parrafos).strip()
            # Si el último bloque de la sección es muy corto y hay un bloque anterior, unirlo
            if len(contenido_resto) < min_chars and bloques_finales:
                ultimo = bloques_finales[-1]
                # Si pertenecen a la misma sección o no supera un tamaño prudente al unir
                if len(ultimo["contenido"]) + len(contenido_resto) <= (max_chars + 300):
                    ultimo["contenido"] += "\n\n" + contenido_resto
                else:
                    bloques_finales.append({
                        "seccion": sec["seccion"],
                        "titulo": sec["titulo"],
                        "contenido": contenido_resto
                    })
            else:
                bloques_finales.append({
                    "seccion": sec["seccion"],
                    "titulo": sec["titulo"],
                    "contenido": contenido_resto
                })

    # Si algún bloque quedó demasiado corto al final, unificar con el anterior
    if len(bloques_finales) > 1 and len(bloques_finales[-1]["contenido"]) < min_chars:
        ultimo = bloques_finales.pop()
        bloques_finales[-1]["contenido"] += "\n\n" + ultimo["contenido"]

    # Generar salida con el contrato {id, libro_slug, orden, seccion, titulo, contenido, tags, metadata, tagueo}
    resultado: List[Dict[str, Any]] = []
    for idx, b in enumerate(bloques_finales, start=1):
        frag_id = f"{slug}_{idx:02d}"
        resultado.append({
            "id": frag_id,
            "libro_slug": slug,
            "orden": idx,
            "seccion": b["seccion"],
            "titulo": b["titulo"],
            "contenido": b["contenido"],
            "tags": [],
            "metadata": {},
            "tagueo": {
                "origen": "manual",
                "revisado": False
            }
        })

    return resultado
