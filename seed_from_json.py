"""
seed_from_json.py · Script de siembra idempotente desde fundacion.json.
Carga el libro inicial 'Origen y Fundación de Las Varillas' y sus fragmentos
en MongoDB cumpliendo el Criterio A1 de specs/01-mongodb/spec.md.
"""
import os
import sys
import json
import hashlib
from datetime import datetime, timezone
from pymongo import MongoClient

from config import settings, sanitizar_mongodb_url
from repository import MongoBookRepository, normalizar_tags

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "fundacion.json")


def sembrar_datos(repo) -> dict:
    """
    Siembra el libro fundacional y sus fragmentos de manera idempotente.
    Retorna un diccionario con la cantidad de libros y fragmentos resultantes.
    """
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(f"No se encontró el archivo de datos: {DATA_FILE}")

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        fragmentos_raw = json.load(f)

    # Calcular hash de contenido completo para trazabilidad
    contenido_total = "".join(f.get("contenido", "") for f in fragmentos_raw)
    hash_texto = hashlib.sha256(contenido_total.encode("utf-8")).hexdigest()

    slug_libro = "fundacion-las-varillas"

    # Definición del libro según contrato de la sección 4.2 y 17.1
    libro = {
        "slug": slug_libro,
        "titulo": "Origen y Fundación de Las Varillas",
        "autor": "Comunidad Historiográfica de Las Varillas",
        "anio": 1900,
        "fuente_tipo": "secundaria",
        "estado": "publicado",
        "resumen": "Debates historiográficos y posturas sobre el origen de Las Varillas: la llegada del ferrocarril (1900), la donación y loteo de Medardo Álvarez Luque (1903) y el reconocimiento administrativo oficial (1904).",
        "temas": ["fundacion", "ferrocarril", "historia local", "origen"],
        "hash_texto": hash_texto,
        "creado": datetime.now(timezone.utc),
    }

    # Guardar el libro (actualiza o inserta de forma idempotente)
    repo.guardar_libro(libro)

    # Preparar fragmentos asegurando el contrato
    fragmentos_a_guardar = []
    for idx, item in enumerate(fragmentos_raw, start=1):
        frag = {
            "id": item["id"],
            "libro_slug": slug_libro,
            "orden": idx,
            "seccion": item.get("titulo", f"Sección {idx}"),
            "titulo": item.get("titulo", ""),
            "contenido": item.get("contenido", ""),
            "tags": normalizar_tags(item.get("tags", [])),
            "metadata": item.get("metadata", {}),
            "tagueo": {
                "origen": "manual",
                "revisado": True,
            },
        }
        fragmentos_a_guardar.append(frag)

    # Guardar fragmentos (reemplazo idempotente para este libro)
    repo.guardar_fragmentos(slug_libro, fragmentos_a_guardar)

    libros = repo.listar_libros(solo_publicados=False)
    fragmentos = repo.obtener_fragmentos(slug_libro)

    return {
        "libros_count": len(libros),
        "fragmentos_count": len(fragmentos),
    }


def main():
    try:
        settings.validar_mongo()
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    url_oculta = sanitizar_mongodb_url(settings.MONGODB_URL)
    print(f"[SIEMBRA] Conectando a MongoDB en {url_oculta} (Base de datos: {settings.MONGODB_DB})...")

    try:
        client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=4000)
        # Forzar chequeo de conexión
        client.admin.command("ping")
        db = client[settings.MONGODB_DB]
        repo = MongoBookRepository(db)
        
        resultado = sembrar_datos(repo)
        print(
            f"[SIEMBRA EXITOSA] Se sembró la base correctamente. "
            f"Libros: {resultado['libros_count']} | Fragmentos: {resultado['fragmentos_count']}"
        )
    except Exception as e:
        print(f"[ERROR SIEMBRA] No se pudo conectar a MongoDB o ejecutar la siembra: {e}", file=sys.stderr)
        print("Asegúrate de que el servicio de MongoDB esté iniciado o configura MONGODB_URL en .env", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
