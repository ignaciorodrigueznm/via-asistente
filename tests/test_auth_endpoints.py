"""
tests/test_auth_endpoints.py · Pruebas de integración para endpoints de Auth, Perfil y Conversaciones.
Cubre las tareas T4 y T5 de specs/06-auth-perfil-personalizacion/tasks.md.
"""
import pytest
from starlette.testclient import TestClient
import web_server
from repository import FakeRepo


@pytest.fixture
def app_client():
    fake = FakeRepo()
    web_server.book_repo = fake
    client = TestClient(web_server.app)
    return client


def test_registro_y_login_flujo_completo(app_client):
    # 1. Registro exitoso
    res_reg = app_client.post("/api/auth/register", json={
        "username": "nacho_test",
        "email": "nacho@varillas.com",
        "password": "clave_segura_123",
        "nombre": "Ignacio"
    })
    assert res_reg.status_code == 201
    datos_reg = res_reg.json()
    assert "token" in datos_reg
    assert datos_reg["usuario"]["username"] == "nacho_test"
    assert "password_hash" not in datos_reg["usuario"]
    token = datos_reg["token"]

    # 2. Intento de registro duplicado (debe fallar 409)
    res_dup = app_client.post("/api/auth/register", json={
        "username": "nacho_test",
        "email": "otro@varillas.com",
        "password": "clave_segura_123"
    })
    assert res_dup.status_code == 409

    # 3. Login exitoso con username
    res_login = app_client.post("/api/auth/login", json={
        "identificador": "nacho_test",
        "password": "clave_segura_123"
    })
    assert res_login.status_code == 200
    assert "token" in res_login.json()

    # 4. Login con password errónea (debe dar 401)
    res_login_malo = app_client.post("/api/auth/login", json={
        "identificador": "nacho_test",
        "password": "clave_incorrecta"
    })
    assert res_login_malo.status_code == 401

    # 5. Consultar /api/auth/me con token
    res_me = app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "nacho@varillas.com"

    # 6. Consultar /api/auth/me sin token (401)
    res_me_anon = app_client.get("/api/auth/me")
    assert res_me_anon.status_code == 401


def test_actualizar_perfil_y_personalizar_ai(app_client):
    # Registrar usuario
    res_reg = app_client.post("/api/auth/register", json={
        "username": "usuario_perfil",
        "email": "perfil@varillas.com",
        "password": "password123"
    })
    token = res_reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Cambiar nombre y foto de perfil
    res_perfil = app_client.put("/api/usuario/perfil", headers=headers, json={
        "nombre": "Nacho Modificado",
        "foto_perfil": "data:image/jpeg;base64,/9j/4AAQSkZJRg..."
    })
    assert res_perfil.status_code == 200
    assert res_perfil.json()["usuario"]["nombre"] == "Nacho Modificado"
    assert "data:image/jpeg" in res_perfil.json()["usuario"]["foto_perfil"]

    # Personalizar AI
    res_ai = app_client.put("/api/usuario/preferencias-ai", headers=headers, json={
        "tono": "formal",
        "nombre_usuario_preferido": "Don Ignacio",
        "directivas_extra": "Citar siempre el tomo y folio histórico"
    })
    assert res_ai.status_code == 200
    assert res_ai.json()["preferencias_ai"]["tono"] == "formal"
    assert res_ai.json()["preferencias_ai"]["nombre_usuario_preferido"] == "Don Ignacio"


def test_historial_conversaciones_usuario(app_client):
    # Registrar usuario
    res_reg = app_client.post("/api/auth/register", json={
        "username": "chat_user",
        "email": "chat@varillas.com",
        "password": "password123"
    })
    token = res_reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Guardar nueva conversación
    res_guardar = app_client.post("/api/conversaciones", headers=headers, json={
        "id": "chat_sesion_1",
        "titulo": "Consulta sobre Medardo Álvarez",
        "libro_slug": "fundacion-las-varillas",
        "mensajes": [
            {"rol": "user", "contenido": "¿Quién fue Álvarez?"},
            {"rol": "assistant", "contenido": "Donó las tierras para el loteo en 1903."}
        ]
    })
    assert res_guardar.status_code == 200
    assert res_guardar.json()["id"] == "chat_sesion_1"

    # Listar conversaciones del usuario
    res_lista = app_client.get("/api/conversaciones", headers=headers)
    assert res_lista.status_code == 200
    lista = res_lista.json()
    assert len(lista) == 1
    assert lista[0]["id"] == "chat_sesion_1"
    assert lista[0]["total_mensajes"] == 2

    # Obtener el detalle de la conversación
    res_detalle = app_client.get("/api/conversaciones/chat_sesion_1", headers=headers)
    assert res_detalle.status_code == 200
    assert len(res_detalle.json()["mensajes"]) == 2

    # Eliminar conversación
    res_del = app_client.delete("/api/conversaciones/chat_sesion_1", headers=headers)
    assert res_del.status_code == 200
    assert len(app_client.get("/api/conversaciones", headers=headers).json()) == 0
