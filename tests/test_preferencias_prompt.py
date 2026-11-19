"""
Pruebas de inyección de preferencias del usuario en el prompt del asistente (Spec 06).
"""
import pytest

import web_server
from auth_service import crear_token_jwt
from repository import FakeRepo


@pytest.fixture()
def repo_con_usuario():
    fake = FakeRepo()
    user_id = fake.crear_usuario({
        "username": "nacho_ai",
        "email": "nacho@ai.com",
        "password_hash": "x",
        "nombre": "Ignacio",
        "preferencias_ai": {
            "tono": "academico",
            "nombre_asistente": "VÍA",
            "nombre_usuario_preferido": "Lil Bro",
            "directivas_extra": "Citar fuentes primarias de 1900",
            "modelo_preferido": "llama3.2"
        }
    })
    web_server.book_repo = fake
    yield fake, user_id
    web_server.book_repo = None


def test_system_prompt_incluye_preferencias(repo_con_usuario):
    _fake, user_id = repo_con_usuario
    prefs = web_server._preferencias_desde_token(
        crear_token_jwt({"user_id": user_id, "username": "nacho_ai"})
    )

    prompt = web_server.construir_system_prompt(prefs)

    assert "Lil Bro" in prompt
    assert "académico" in prompt
    assert "Citar fuentes primarias de 1900" in prompt


def test_mensajes_inyectan_preferencias_en_el_sistema(repo_con_usuario):
    _fake, user_id = repo_con_usuario
    prefs = web_server._preferencias_desde_token(
        crear_token_jwt({"user_id": user_id, "username": "nacho_ai"})
    )

    mensajes = web_server.construir_mensajes("¿Cuál es mi apodo?", "contexto", prefs)

    assert mensajes[0]["role"] == "system"
    assert "Lil Bro" in mensajes[0]["content"]


def test_sin_token_no_hay_preferencias():
    assert web_server._preferencias_desde_token("") is None
    assert web_server._preferencias_desde_token("token_invalido") is None


def test_modelo_preferido_se_usa_si_no_se_pide_otro():
    prefs = {"modelo_preferido": "llama3.2"}
    _, _, modelo = web_server.obtener_parametros_chat({"message": "hola"}, prefs)
    assert modelo == "llama3.2"

    _, _, modelo_pedido = web_server.obtener_parametros_chat(
        {"message": "hola", "model": "otro-modelo"}, prefs
    )
    assert modelo_pedido == "otro-modelo"
