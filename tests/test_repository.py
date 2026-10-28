"""
tests/test_repository.py · Pruebas del contrato BookRepository con dobles en memoria (FakeRepo).
Cumple los criterios de aceptación A2, A3 y A6 de specs/01-mongodb/spec.md.
"""
import pytest
from repository import normalizar_tag, normalizar_tags, FakeRepo, MongoBookRepository, BookRepository
import mongomock


@pytest.fixture(params=["fake", "mongo"])
def repo(request):
    """
    Criterio A6: La misma batería de tests debe pasar con FakeRepo
    y con MongoBookRepository.
    """
    if request.param == "fake":
        return FakeRepo()
    else:
        client = mongomock.MongoClient()
        db = client["test_corpus_db"]
        return MongoBookRepository(db)


def test_normalizar_tag_individual():
    """Verifica que un tag individual pase a minúsculas, sin tildes ni espacios extras."""
    assert normalizar_tag("  Ferrocarril  ") == "ferrocarril"
    assert normalizar_tag("Estación") == "estacion"
    assert normalizar_tag("ORÍGENES") == "origenes"
    assert normalizar_tag("") == ""


def test_criterio_a2_normalizacion_de_tags():
    """
    Criterio A2: Dado un fragmento con tags ["Ferrocarril", "  ferrocarril ", "Estación"],
    cuando se guarda/normaliza, entonces quedan ["ferrocarril", "estacion"].
    """
    tags_originales = ["Ferrocarril", "  ferrocarril ", "Estación"]
    tags_resultado = normalizar_tags(tags_originales)
    assert tags_resultado == ["ferrocarril", "estacion"]


def test_repositorios_cumplen_protocolo(repo):
    """Verifica que ambos repositorios implementan formalmente el protocolo BookRepository."""
    assert isinstance(repo, BookRepository)


def test_criterio_a3_libros_borrador_vs_publicado(repo):
    """
    Criterio A3: Dado un libro en borrador, cuando se consulta el catálogo,
    no aparece; al publicarlo aparece y meta.version aumenta en 1.
    """
    version_inicial = repo.obtener_version_corpus()

    # Guardar un libro en estado 'borrador'
    libro_borrador = {
        "slug": "libro-test",
        "titulo": "Libro de Prueba",
        "autor": "Autor Test",
        "anio": 2024,
        "fuente_tipo": "primaria",
        "estado": "borrador",
        "resumen": "Resumen de prueba",
        "temas": ["historia"],
        "hash_texto": "hash123",
    }
    repo.guardar_libro(libro_borrador)

    # El catálogo público solo debe mostrar publicados
    publicados = repo.listar_libros(solo_publicados=True)
    assert len(publicados) == 0

    # Todos los libros (para backoffice/admin) sí lo muestran
    todos = repo.listar_libros(solo_publicados=False)
    assert len(todos) == 1
    assert todos[0]["slug"] == "libro-test"

    # Al publicarlo, meta.version aumenta en 1 y se ve en el catálogo público
    repo.cambiar_estado_libro("libro-test", "publicado")
    publicados_post = repo.listar_libros(solo_publicados=True)
    assert len(publicados_post) == 1
    assert publicados_post[0]["slug"] == "libro-test"
    assert repo.obtener_version_corpus() == version_inicial + 1


def test_guardar_fragmentos_normaliza_tags(repo):
    """Verifica que al guardar fragmentos en el repositorio los tags se guarden normalizados."""
    fragmentos = [
        {
            "id": "libro-test_01",
            "libro_slug": "libro-test",
            "orden": 1,
            "seccion": "Introducción",
            "titulo": "Inicio",
            "contenido": "Texto de prueba",
            "tags": ["Ferrocarril", "  ferrocarril ", "Estación"],
            "metadata": {},
            "tagueo": {"origen": "manual", "revisado": True},
        }
    ]
    repo.guardar_fragmentos("libro-test", fragmentos)
    recuperados = repo.obtener_fragmentos("libro-test")
    assert len(recuperados) == 1
    assert recuperados[0]["tags"] == ["ferrocarril", "estacion"]


def test_eliminar_libro_y_fragmentos(repo):
    """Verifica que al eliminar un libro se eliminen también sus fragmentos y se incremente la versión."""
    v_inicial = repo.obtener_version_corpus()
    repo.guardar_libro({"slug": "a-borrar", "titulo": "A Borrar", "estado": "publicado"})
    repo.guardar_fragmentos("a-borrar", [{"id": "ab_01", "orden": 1, "contenido": "c"}])
    
    assert len(repo.obtener_fragmentos("a-borrar")) == 1
    eliminado = repo.eliminar_libro("a-borrar")
    assert eliminado is True
    assert repo.obtener_libro("a-borrar") is None
    assert len(repo.obtener_fragmentos("a-borrar")) == 0
    assert repo.obtener_version_corpus() > v_inicial


def test_criterio_a1_siembra_idempotente(repo):
    """
    Criterio A1: Dado Mongo vacío, cuando ejecuto la siembra, entonces hay 1 libro y 6 (o 3) fragmentos;
    si la ejecuto otra vez, siguen siendo 1 y la misma cantidad de fragmentos (idempotencia).
    """
    from seed_from_json import sembrar_datos

    # Primera ejecución de siembra
    r1 = sembrar_datos(repo)
    assert r1["libros_count"] == 1
    assert r1["fragmentos_count"] == 3

    # Segunda ejecución de siembra (no debe duplicar)
    r2 = sembrar_datos(repo)
    assert r2["libros_count"] == 1
    assert r2["fragmentos_count"] == 3


def test_criterio_a5_validacion_config_y_sanitizacion():
    """
    Criterio A5: Dado MONGODB_URL inválida o Mongo apagado, cuando arranca el backend,
    entonces falla con un mensaje que indica qué variable revisar y sin imprimir la contraseña.
    """
    from config import Settings, sanitizar_mongodb_url

    url_con_secreto = "mongodb://usuario:super_password_secreto@cluster.mongodb.net:27017/db"
    sanitizada = sanitizar_mongodb_url(url_con_secreto)
    assert "super_password_secreto" not in sanitizada
    assert ":***@" in sanitizada

    # Prueba de validación de formato
    s = Settings()
    s.MONGODB_URL = "postgres://user:password@localhost:5432/db"
    with pytest.raises(ValueError) as excinfo:
        s.validar_mongo()

    mensaje = str(excinfo.value)
    assert "MONGODB_URL" in mensaje
    assert "password" not in mensaje


