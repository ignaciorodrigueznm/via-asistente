"""
tests/test_carga_session.py · Pruebas unitarias para el gestor de sesiones de carga por partes.
Cumple los criterios de aceptación B2, B3, B4 y B5 de specs/02-carga-por-partes/spec.md.
"""
import hashlib
import pytest
from carga_session import CargaSessionManager, CargaError


def test_crear_sesion_carga():
    manager = CargaSessionManager()
    metadata = {
        "slug": "historia-local",
        "titulo": "Historia Local",
        "hash_texto": "hash_esperado_123"
    }
    carga_id = manager.crear_sesion(metadata)
    assert carga_id is not None
    info = manager.obtener_info(carga_id)
    assert info["carga_id"] == carga_id
    assert info["metadata"]["slug"] == "historia-local"
    assert info["partes_recibidas"] == []


def test_criterio_b2_recepcion_idempotente_por_numero_de_parte():
    """
    Criterio B2: Dado que la parte 2 se envía dos veces, cuando finalizo,
    entonces el texto no tiene contenido duplicado.
    """
    manager = CargaSessionManager()
    metadata = {"slug": "libro-test", "titulo": "Test"}
    carga_id = manager.crear_sesion(metadata)

    manager.recibir_parte(carga_id, 1, 2, "Parte 1 de contenido. ")
    # Enviar la parte 2 dos veces exactamente
    manager.recibir_parte(carga_id, 2, 2, "Parte 2 de contenido.")
    manager.recibir_parte(carga_id, 2, 2, "Parte 2 de contenido.")

    texto_ensamblado = manager.ensamblar_texto(carga_id)
    assert texto_ensamblado == "Parte 1 de contenido. Parte 2 de contenido."
    # Asegurar que "Parte 2 de contenido." aparece solo una vez
    assert texto_ensamblado.count("Parte 2 de contenido.") == 1


def test_criterio_b3_informar_partes_recibidas_para_reanudar():
    """
    Criterio B3: Dado un corte de red después de la parte 2 de 4, cuando reanudo,
    entonces solo se envían las partes 3 y 4.
    """
    manager = CargaSessionManager()
    metadata = {"slug": "libro-corte", "titulo": "Corte"}
    carga_id = manager.crear_sesion(metadata)

    manager.recibir_parte(carga_id, 1, 4, "Texto 1")
    manager.recibir_parte(carga_id, 2, 4, "Texto 2")

    info = manager.obtener_info(carga_id)
    assert info["partes_recibidas"] == [1, 2]
    assert info["total_partes"] == 4
    assert info["completado"] is False


def test_criterio_b4_finalizar_rechaza_si_falta_parte_o_hash_no_coincide():
    """
    Criterio B4: Dado que falta una parte o el hash no coincide, cuando finalizo,
    entonces el backend responde con error y no crea fragmentos.
    """
    manager = CargaSessionManager()
    metadata = {"slug": "libro-incompleto", "titulo": "Incompleto"}
    carga_id = manager.crear_sesion(metadata)

    # Total 3 partes, pero solo se envía la 1 y la 2
    manager.recibir_parte(carga_id, 1, 3, "Uno ")
    manager.recibir_parte(carga_id, 2, 3, "Dos ")

    with pytest.raises(CargaError) as exc_faltante:
        manager.verificar_y_ensamblar(carga_id, hash_esperado="cualquiera")
    assert "Faltan partes" in str(exc_faltante.value)

    # Ahora se envía la 3 pero se pasa un hash incorrecto
    manager.recibir_parte(carga_id, 3, 3, "Tres")
    hash_falso = "abcdef1234567890"

    with pytest.raises(CargaError) as exc_hash:
        manager.verificar_y_ensamblar(carga_id, hash_esperado=hash_falso)
    assert "Hash no coincide" in str(exc_hash.value)


def test_criterio_b5_superar_tope_por_parte_genera_error_413():
    """
    Criterio B5: Dada una parte que supera el tope del backend,
    entonces el backend responde con error de tamaño excedido (413).
    """
    manager = CargaSessionManager(max_chars_por_parte=100)
    carga_id = manager.crear_sesion({"slug": "libro-grande"})

    texto_muy_largo = "A" * 101
    with pytest.raises(CargaError) as exc:
        manager.recibir_parte(carga_id, 1, 1, texto_muy_largo)
    assert exc.value.status_code == 413


def test_finalizar_exitoso_con_hash_sha256():
    manager = CargaSessionManager()
    carga_id = manager.crear_sesion({"slug": "libro-ok"})
    p1 = "Primera sección importante. "
    p2 = "Segunda sección de cierre."
    manager.recibir_parte(carga_id, 1, 2, p1)
    manager.recibir_parte(carga_id, 2, 2, p2)

    texto_completo = p1 + p2
    hash_real = hashlib.sha256(texto_completo.encode("utf-8")).hexdigest()

    ensamblado = manager.verificar_y_ensamblar(carga_id, hash_esperado=hash_real)
    assert ensamblado == texto_completo
