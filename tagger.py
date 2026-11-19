"""
tagger.py · Protocolo Tagger y estrategia por defecto ManualTagger.
Cumple el criterio de aceptación B7 y la sección 5.2 del Taller MCP 3.
"""
from typing import Protocol, runtime_checkable, Dict, Any, List, Tuple
from repository import normalizar_tags


@runtime_checkable
class Tagger(Protocol):
    """
    Protocolo Tagger (sección 5.2):
    Punto de extensión para sugerir título, tags y metadata opcionalmente.
    """
    def sugerir(self, fragmento: Dict[str, Any], libro: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retorna un diccionario con {titulo?, tags[], metadata?}.
        """
        ...


class ManualTagger:
    """
    Implementación por defecto (sección 5.2):
    No sugiere nada y deja el fragmento con tags vacíos para completar a mano en el backoffice.
    """
    def sugerir(self, fragmento: Dict[str, Any], libro: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "tags": [],
            "metadata": {},
            "tagueo": {
                "origen": "manual",
                "revisado": True
            }
        }


def aplicar_tagger_seguro(
    tagger: Tagger,
    fragmentos: List[Dict[str, Any]],
    libro: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Aplica el Tagger a una lista de fragmentos de forma segura y no bloqueante (Criterio B7).
    Si el tagger falla o lanza excepción, el fragmento queda sin tags con un aviso,
    y el proceso de carga continúa sin cancelarse.
    """
    fragmentos_actualizados = []
    avisos: List[str] = []

    for f in fragmentos:
        frag_copia = dict(f)
        try:
            sugerencia = tagger.sugerir(frag_copia, libro)
            if sugerencia:
                if "titulo" in sugerencia and sugerencia["titulo"]:
                    frag_copia["titulo"] = sugerencia["titulo"]
                if "tags" in sugerencia and sugerencia["tags"]:
                    frag_copia["tags"] = normalizar_tags(sugerencia["tags"])
                if "metadata" in sugerencia and sugerencia["metadata"]:
                    frag_copia.setdefault("metadata", {}).update(sugerencia["metadata"])
                
                frag_copia["tagueo"] = {
                    "origen": getattr(tagger, "nombre", type(tagger).__name__),
                    "revisado": False
                }
        except Exception as e:
            aviso = f"El tagger falló para el fragmento {frag_copia.get('id')}: {e}"
            avisos.append(aviso)
            frag_copia["tags"] = []
            frag_copia["tagueo"] = {
                "origen": "error_tagger",
                "revisado": False,
                "error": str(e)
            }

        fragmentos_actualizados.append(frag_copia)

    return fragmentos_actualizados, avisos
