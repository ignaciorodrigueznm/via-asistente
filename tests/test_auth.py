"""
tests/test_auth.py · Pruebas unitarias para auth_service y validaciones de Pydantic de usuarios.
Cubre las tareas T1 y T2 de specs/06-auth-perfil-personalizacion/tasks.md.
"""
import pytest
from auth_service import hashear_password, verificar_password, crear_token_jwt, decodificar_token_jwt
from models import UsuarioRegisterModel, UsuarioLoginModel, PerfilUpdateModel, PreferenciasAIModel


def test_hashing_y_verificacion_password():
    password_plana = "mi_secreto_seguro_123"
    hash_generado = hashear_password(password_plana)
    
    # El hash no debe contener la contraseña plana
    assert password_plana not in hash_generado
    assert hash_generado.startswith("$2b$")
    
    # Verificación correcta
    assert verificar_password(password_plana, hash_generado) is True
    # Verificación incorrecta
    assert verificar_password("otra_password_erronea", hash_generado) is False


def test_token_jwt_creacion_y_decodificacion():
    user_data = {"user_id": "user_123", "username": "nacho", "rol": "usuario"}
    token = crear_token_jwt(user_data)
    assert isinstance(token, str)
    assert len(token) > 20
    
    payload = decodificar_token_jwt(token)
    assert payload is not None
    assert payload["user_id"] == "user_123"
    assert payload["username"] == "nacho"
    assert "exp" in payload


def test_token_jwt_invalido():
    payload = decodificar_token_jwt("token_totalmente_invalido.123.456")
    assert payload is None


def test_validacion_registro_pydantic():
    # Caso válido
    valido = UsuarioRegisterModel(
        username="nacho_dev",
        email="nacho@test.com",
        password="password123",
        nombre="Ignacio"
    )
    assert valido.username == "nacho_dev"
    assert valido.email == "nacho@test.com"

    # Username muy corto
    with pytest.raises(Exception):
        UsuarioRegisterModel(username="ab", email="nacho@test.com", password="password123")

    # Email inválido
    with pytest.raises(Exception):
        UsuarioRegisterModel(username="nacho_dev", email="no_es_un_email", password="password123")

    # Contraseña muy corta
    with pytest.raises(Exception):
        UsuarioRegisterModel(username="nacho_dev", email="nacho@test.com", password="123")


def test_validacion_preferencias_ai_pydantic():
    prefs = PreferenciasAIModel(
        tono="academico",
        nombre_usuario_preferido="Profesor Nacho",
        directivas_extra="Citar fuentes y años de forma rigurosa."
    )
    assert prefs.tono == "academico"
    assert prefs.nombre_usuario_preferido == "Profesor Nacho"

    # Tono no permitido
    with pytest.raises(Exception):
        PreferenciasAIModel(tono="tono_inventado")
