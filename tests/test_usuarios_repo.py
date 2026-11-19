"""
tests/test_usuarios_repo.py · Pruebas unitarias para persistencia de usuarios y conversaciones.
Cubre la tarea T3 de specs/06-auth-perfil-personalizacion/tasks.md con FakeRepo y MongoBookRepository.
"""
import pytest
import mongomock
from repository import FakeRepo, MongoBookRepository, BookRepository


@pytest.fixture(params=["fake", "mongo"])
def repo(request):
    if request.param == "fake":
        return FakeRepo()
    else:
        client = mongomock.MongoClient()
        db = client["test_usuarios_db"]
        return MongoBookRepository(db)


def test_repo_cumple_protocolo(repo):
    assert isinstance(repo, BookRepository)


def test_crud_usuario_y_preferencias_ai(repo):
    usuario_datos = {
        "username": "nacho_varillas",
        "email": "nacho@varillas.gob.ar",
        "password_hash": "$2b$12$hash_simulado",
        "nombre": "Ignacio Rodríguez",
        "foto_perfil": "https://example.com/avatar.png",
        "rol": "usuario",
        "preferencias_ai": {
            "tono": "formal",
            "nombre_usuario_preferido": "Licenciado Ignacio",
            "directivas_extra": "Citar documentos del archivo histórico",
            "modelo_preferido": "llama3.2"
        }
    }
    user_id = repo.crear_usuario(usuario_datos)
    assert user_id is not None

    # Búsqueda por username (case-insensitive)
    u_username = repo.obtener_usuario_por_username("NACHO_VARILLAS")
    assert u_username is not None
    assert u_username["id"] == user_id
    assert u_username["nombre"] == "Ignacio Rodríguez"

    # Búsqueda por email
    u_email = repo.obtener_usuario_por_email("nacho@varillas.gob.ar")
    assert u_email is not None
    assert u_email["id"] == user_id

    # Actualizar perfil (foto y nombre)
    actualizado = repo.actualizar_perfil_usuario(user_id, {
        "nombre": "Ignacio M. Rodríguez",
        "foto_perfil": "data:image/png;base64,nueva_foto"
    })
    assert actualizado is True
    u_modificado = repo.obtener_usuario_por_id(user_id)
    assert u_modificado["nombre"] == "Ignacio M. Rodríguez"
    assert u_modificado["foto_perfil"] == "data:image/png;base64,nueva_foto"

    # Actualizar "Personalizar AI"
    actualizado_ai = repo.actualizar_preferencias_ai(user_id, {
        "tono": "academico",
        "directivas_extra": "Enfocarse en decretos de 1904"
    })
    assert actualizado_ai is True
    u_ai = repo.obtener_usuario_por_id(user_id)
    assert u_ai["preferencias_ai"]["tono"] == "academico"
    assert u_ai["preferencias_ai"]["directivas_extra"] == "Enfocarse en decretos de 1904"


def test_crud_conversaciones_por_usuario(repo):
    user_1 = repo.crear_usuario({"username": "user1", "email": "u1@test.com"})
    user_2 = repo.crear_usuario({"username": "user2", "email": "u2@test.com"})

    # Crear conversación para user_1
    conv_1 = {
        "id": "conv_001",
        "user_id": user_1,
        "titulo": "Preguntas sobre 1900",
        "libro_slug": "fundacion-las-varillas",
        "mensajes": [
            {"rol": "user", "contenido": "¿Llegó el tren en 1900?"},
            {"rol": "assistant", "contenido": "Sí, el 24 de diciembre de 1900."}
        ]
    }
    repo.guardar_conversacion(conv_1)

    # user_1 puede ver su conversación
    convs_u1 = repo.listar_conversaciones_usuario(user_1)
    assert len(convs_u1) == 1
    assert convs_u1[0]["id"] == "conv_001"

    # user_2 NO puede ver la conversación de user_1 (aislamiento seguro)
    convs_u2 = repo.listar_conversaciones_usuario(user_2)
    assert len(convs_u2) == 0
    assert repo.obtener_conversacion("conv_001", user_2) is None

    # Obtener detalle completo
    detalle = repo.obtener_conversacion("conv_001", user_1)
    assert detalle is not None
    assert len(detalle["mensajes"]) == 2

    # Eliminar conversación
    eliminado = repo.eliminar_conversacion("conv_001", user_1)
    assert eliminado is True
    assert repo.obtener_conversacion("conv_001", user_1) is None
    assert len(repo.listar_conversaciones_usuario(user_1)) == 0
