"""
carga_session.py · Gestor de sesiones para la carga por partes e ingesta de libros.
Cumple los criterios B2, B3, B4 y B5 de specs/02-carga-por-partes/spec.md.
"""
import uuid
import hashlib
from typing import Dict, Any, List, Optional


class CargaError(Exception):
    """Excepción para errores de validación de carga con código HTTP asociado."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class CargaSessionManager:
    """
    Gestiona el ciclo de vida de una carga por partes:
    - Creación de sesión con carga_id único.
    - Almacenamiento idempotente de partes en memoria.
    - Validación de topes de tamaño por parte (413).
    - Reporte de partes recibidas para reanudar cortes.
    - Verificación estricta de hash SHA-256 del texto ensamblado al finalizar.
    """

    def __init__(self, max_chars_por_parte: int = 150_000):
        self.max_chars_por_parte = max_chars_por_parte
        self._sesiones: Dict[str, Dict[str, Any]] = {}

    def crear_sesion(self, metadata: Dict[str, Any]) -> str:
        """Crea una nueva sesión de carga y devuelve su carga_id único."""
        carga_id = f"carga_{uuid.uuid4().hex[:12]}"
        self._sesiones[carga_id] = {
            "carga_id": carga_id,
            "metadata": dict(metadata),
            "total_partes": None,
            "partes": {},  # Dict[int, str]: {numero_de_parte: texto}
            "completado": False
        }
        return carga_id

    def obtener_sesion(self, carga_id: str) -> Dict[str, Any]:
        """Obtiene los datos de la sesión o lanza CargaError 404."""
        if carga_id not in self._sesiones:
            raise CargaError(f"Sesión de carga '{carga_id}' no encontrada", status_code=404)
        return self._sesiones[carga_id]

    def recibir_parte(self, carga_id: str, n: int, total: int, texto: str) -> None:
        """
        Recibe una parte de forma idempotente (Criterio B2).
        Valida que el texto no supere el tope permitido (Criterio B5).
        """
        sesion = self.obtener_sesion(carga_id)
        if sesion["completado"]:
            raise CargaError("La sesión de carga ya ha sido finalizada", status_code=400)

        if len(texto) > self.max_chars_por_parte:
            raise CargaError(
                f"La parte {n} excede el límite permitido por el servidor ({self.max_chars_por_parte} caracteres)",
                status_code=413
            )

        if n < 1 or n > total:
            raise CargaError(f"Número de parte inválido: {n} (debe estar entre 1 y {total})", status_code=400)

        sesion["total_partes"] = total
        # Guardar en diccionario indexado por n asegura idempotencia: reenviar no duplica contenido
        sesion["partes"][n] = texto

    def obtener_info(self, carga_id: str) -> Dict[str, Any]:
        """Informa qué partes llegaron para poder reanudar tras un corte (Criterio B3)."""
        sesion = self.obtener_sesion(carga_id)
        partes_recibidas = sorted(list(sesion["partes"].keys()))
        return {
            "carga_id": carga_id,
            "metadata": sesion["metadata"],
            "partes_recibidas": partes_recibidas,
            "total_partes": sesion["total_partes"],
            "completado": sesion["completado"]
        }

    def ensamblar_texto(self, carga_id: str) -> str:
        """Concatena todas las partes recibidas ordenadas por número."""
        sesion = self.obtener_sesion(carga_id)
        partes = sesion["partes"]
        partes_ordenadas = sorted(partes.keys())
        return "".join(partes[k] for k in partes_ordenadas)

    def verificar_y_ensamblar(self, carga_id: str, hash_esperado: str) -> str:
        """
        Verifica que todas las partes estén completas y que el hash SHA-256 coincida (Criterio B4).
        Retorna el texto ensamblado completo.
        """
        sesion = self.obtener_sesion(carga_id)
        total = sesion["total_partes"]

        if total is None or len(sesion["partes"]) < total:
            partes_actuales = set(sesion["partes"].keys())
            faltantes = [i for i in range(1, (total or 0) + 1) if i not in partes_actuales]
            raise CargaError(
                f"Faltan partes por recibir. Faltantes: {faltantes}",
                status_code=400
            )

        texto_ensamblado = self.ensamblar_texto(carga_id)
        hash_calculado = hashlib.sha256(texto_ensamblado.encode("utf-8")).hexdigest()

        if hash_esperado and hash_calculado.lower() != hash_esperado.lower():
            raise CargaError(
                f"Hash no coincide: esperado '{hash_esperado}', calculado '{hash_calculado}'",
                status_code=400
            )

        sesion["completado"] = True
        return texto_ensamblado


# Instancia singleton global del gestor de cargas
carga_manager = CargaSessionManager()
