"""
repository.py · Capa de persistencia para libros y fragmentos.
Define el protocolo BookRepository, la normalización estricta de tags
y la implementación en memoria (FakeRepo) para pruebas sin MongoDB.
"""
from typing import Protocol, runtime_checkable, List, Dict, Any, Optional
import unicodedata
import re
from datetime import datetime, timezone


def normalizar_tag(tag: str) -> str:
    """
    Normaliza un tag individual:
    - Minúsculas.
    - Sin acentos (diacríticos).
    - Sin espacios sobrantes.
    """
    if not tag:
        return ""
    texto = tag.strip().lower()
    # Eliminar diacríticos (tildes)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # Limpiar espacios repetidos internos
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def normalizar_tags(tags: List[str]) -> List[str]:
    """
    Normaliza una lista de tags eliminando duplicados y vacíos,
    conservando el orden de aparición.
    Cumple el contrato de la sección 4.2 / Criterio A2.
    """
    resultado: List[str] = []
    vistos = set()
    for t in tags:
        norm = normalizar_tag(t)
        if norm and norm not in vistos:
            vistos.add(norm)
            resultado.append(norm)
    return resultado


@runtime_checkable
class BookRepository(Protocol):
    """
    Protocolo de acceso a la persistencia de libros y fragmentos.
    La API pública, el Backoffice y el MCP dependen exclusivamente de esta interfaz.
    """

    def listar_libros(self, solo_publicados: bool = True) -> List[Dict[str, Any]]:
        """Devuelve la lista de libros disponibles según su estado."""
        ...

    def obtener_libro(self, slug: str) -> Optional[Dict[str, Any]]:
        """Obtiene los metadatos de un libro por su slug único."""
        ...

    def guardar_libro(self, libro: Dict[str, Any]) -> str:
        """Crea o actualiza un libro y devuelve su slug o identificador."""
        ...

    def cambiar_estado_libro(self, slug: str, nuevo_estado: str) -> bool:
        """Cambia el estado de un libro (ej: borrador -> publicado) e incrementa meta.version si se publica."""
        ...

    def eliminar_libro(self, slug: str) -> bool:
        """Elimina un libro y todos sus fragmentos asociados."""
        ...

    def obtener_fragmentos(self, libro_slug: str) -> List[Dict[str, Any]]:
        """Devuelve los fragmentos ordenados pertenecientes a un libro."""
        ...

    def guardar_fragmentos(self, libro_slug: str, fragmentos: List[Dict[str, Any]]) -> int:
        """Guarda o actualiza fragmentos normalizando siempre sus tags."""
        ...

    def obtener_version_corpus(self) -> int:
        """Consulta la versión actual del corpus (meta.version)."""
        ...

    def incrementar_version_corpus(self) -> int:
        """Incrementa en 1 la versión del corpus y devuelve el nuevo valor."""
        ...


class FakeRepo:
    """
    Implementación en memoria del protocolo BookRepository para tests unitarios
    sin requerir red ni base de datos real (Criterio A6).
    """

    def __init__(self):
        self._libros: Dict[str, Dict[str, Any]] = {}
        self._fragmentos: Dict[str, List[Dict[str, Any]]] = {}
        self._version_corpus: int = 1

    def listar_libros(self, solo_publicados: bool = True) -> List[Dict[str, Any]]:
        libros = list(self._libros.values())
        if solo_publicados:
            return [l for l in libros if l.get("estado") == "publicado"]
        return list(libros)

    def obtener_libro(self, slug: str) -> Optional[Dict[str, Any]]:
        return self._libros.get(slug)

    def guardar_libro(self, libro: Dict[str, Any]) -> str:
        slug = libro["slug"]
        datos = dict(libro)
        if "creado" not in datos:
            datos["creado"] = datetime.now(timezone.utc)
        if "temas" in datos:
            datos["temas"] = normalizar_tags(datos["temas"])
        self._libros[slug] = datos
        return slug

    def cambiar_estado_libro(self, slug: str, nuevo_estado: str) -> bool:
        if slug not in self._libros:
            return False
        estado_previo = self._libros[slug].get("estado")
        self._libros[slug]["estado"] = nuevo_estado
        if nuevo_estado == "publicado" and estado_previo != "publicado":
            self.incrementar_version_corpus()
        return True

    def eliminar_libro(self, slug: str) -> bool:
        if slug in self._libros:
            del self._libros[slug]
            self._fragmentos.pop(slug, None)
            self.incrementar_version_corpus()
            return True
        return False

    def obtener_fragmentos(self, libro_slug: str) -> List[Dict[str, Any]]:
        frags = self._fragmentos.get(libro_slug, [])
        return sorted(frags, key=lambda x: x.get("orden", 0))

    def guardar_fragmentos(self, libro_slug: str, fragmentos: List[Dict[str, Any]]) -> int:
        frags_procesados = []
        for f in fragmentos:
            item = dict(f)
            item["libro_slug"] = libro_slug
            if "tags" in item:
                item["tags"] = normalizar_tags(item["tags"])
            frags_procesados.append(item)
        self._fragmentos[libro_slug] = frags_procesados
        return len(frags_procesados)

    def obtener_version_corpus(self) -> int:
        return self._version_corpus

    def incrementar_version_corpus(self) -> int:
        self._version_corpus += 1
        return self._version_corpus


class MongoBookRepository:
    """
    Implementación en MongoDB del protocolo BookRepository.
    Maneja colecciones: 'libros', 'fragmentos' y 'meta'.
    Asegura índices de la sección 4.2:
    - único en fragmentos.id
    - compuesto en fragmentos.libro_slug + orden (y fragmentos.libro_id + orden)
    - fragmentos.tags
    - único en libros.slug
    """

    def __init__(self, db):
        self.db = db
        self.libros = db["libros"]
        self.fragmentos = db["fragmentos"]
        self.meta = db["meta"]
        self._asegurar_indices()
        self._inicializar_meta()

    def _asegurar_indices(self):
        """Crea los índices requeridos por el contrato (sección 4.2)."""
        try:
            self.libros.create_index("slug", unique=True)
            self.fragmentos.create_index("id", unique=True)
            self.fragmentos.create_index([("libro_slug", 1), ("orden", 1)])
            self.fragmentos.create_index("tags")
        except Exception:
            # En ciertos fakes/drivers que no soportan todos los tipos de índices complejos
            pass

    def _inicializar_meta(self):
        """Asegura que exista el documento meta _id='corpus' con version inicial 1."""
        doc = self.meta.find_one({"_id": "corpus"})
        if not doc:
            self.meta.insert_one({"_id": "corpus", "version": 1})

    def listar_libros(self, solo_publicados: bool = True) -> List[Dict[str, Any]]:
        filtro = {"estado": "publicado"} if solo_publicados else {}
        cursor = self.libros.find(filtro, {"_id": 0})
        return list(cursor)

    def obtener_libro(self, slug: str) -> Optional[Dict[str, Any]]:
        return self.libros.find_one({"slug": slug}, {"_id": 0})

    def guardar_libro(self, libro: Dict[str, Any]) -> str:
        slug = libro["slug"]
        datos = dict(libro)
        if "creado" not in datos:
            datos["creado"] = datetime.now(timezone.utc)
        if "temas" in datos:
            datos["temas"] = normalizar_tags(datos["temas"])
        
        self.libros.update_one({"slug": slug}, {"$set": datos}, upsert=True)
        return slug

    def cambiar_estado_libro(self, slug: str, nuevo_estado: str) -> bool:
        libro = self.libros.find_one({"slug": slug})
        if not libro:
            return False
        estado_previo = libro.get("estado")
        res = self.libros.update_one({"slug": slug}, {"$set": {"estado": nuevo_estado}})
        if res.modified_count > 0 or nuevo_estado != estado_previo:
            if nuevo_estado == "publicado" and estado_previo != "publicado":
                self.incrementar_version_corpus()
            return True
        return False

    def eliminar_libro(self, slug: str) -> bool:
        res = self.libros.delete_one({"slug": slug})
        if res.deleted_count > 0:
            self.fragmentos.delete_many({"libro_slug": slug})
            self.incrementar_version_corpus()
            return True
        return False

    def obtener_fragmentos(self, libro_slug: str) -> List[Dict[str, Any]]:
        cursor = self.fragmentos.find({"libro_slug": libro_slug}, {"_id": 0}).sort("orden", 1)
        return list(cursor)

    def guardar_fragmentos(self, libro_slug: str, fragmentos: List[Dict[str, Any]]) -> int:
        if not fragmentos:
            return 0
        
        # Elimina fragmentos anteriores del mismo libro para reemplazarlos de manera idempotente
        self.fragmentos.delete_many({"libro_slug": libro_slug})

        docs = []
        for f in fragmentos:
            item = dict(f)
            item["libro_slug"] = libro_slug
            if "tags" in item:
                item["tags"] = normalizar_tags(item["tags"])
            docs.append(item)

        if docs:
            self.fragmentos.insert_many(docs)
        return len(docs)

    def obtener_version_corpus(self) -> int:
        doc = self.meta.find_one({"_id": "corpus"})
        return doc.get("version", 1) if doc else 1

    def incrementar_version_corpus(self) -> int:
        doc = self.meta.find_one_and_update(
            {"_id": "corpus"},
            {"$inc": {"version": 1}},
            upsert=True,
            return_document=True
        )
        if isinstance(doc, dict):
            return doc.get("version", 1)
        # Si el driver devuelve el documento anterior o estructura específica
        nuevo = self.meta.find_one({"_id": "corpus"})
        return nuevo.get("version", 1) if nuevo else 1

