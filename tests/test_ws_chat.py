"""
tests/test_ws_chat.py · Pruebas unitarias y de integración para WebSocket (/ws/chat).
Cubre la suite de 5 pruebas WS según el plan de testing del proyecto:
  1. WS 1 (Handshake & Conexión): Conexión exitosa y protocolo 101 Switching Protocols.
  2. WS 2 (Ping / Pong & Healthcheck): Mensaje de verificación rápida {"type": "ping"}.
  3. WS 3 (Validación de mensaje vacío): Respuesta de error cuando se envía mensaje en blanco.
  4. WS 4 (Bucle de razonamiento & Respuesta): Recepción de status y respuesta simulando LLM/MCP.
  5. WS 5 (Desconexión limpia / Close): Cierre de conexión con código de estado normal (1000).
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.testclient import TestClient
import web_server
from repository import FakeRepo


@pytest.fixture
def test_client():
    fake = FakeRepo()
    web_server.book_repo = fake
    client = TestClient(web_server.app)
    return client


# --- WS 1: Handshake & Conexión ---
def test_ws_1_conexion_handshake(test_client):
    """WS 1: Verifica conexión exitosa a /ws/chat sin caídas inmediatas."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        assert websocket is not None


# --- WS 2: Ping / Pong ---
def test_ws_2_ping_pong_control(test_client):
    """WS 2: Verifica que el WebSocket responda a peticiones de ping con 'connected'."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"type": "ping"})
        data = websocket.receive_json()
        assert data.get("type") == "pong"
        assert data.get("status") == "connected"


# --- WS 3: Validación de mensaje vacío ---
def test_ws_3_mensaje_vacio_retorna_error(test_client):
    """WS 3: Verifica manejo de mensajes vacíos devolviendo error sin romper el socket."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.send_json({"text": "   "})
        data = websocket.receive_json()
        assert data.get("type") == "error"
        assert "no puede estar vacío" in data.get("message", "")


# --- WS 4: Bucle de razonamiento y respuesta mockeada ---
def test_ws_4_flujo_respuesta_chat(test_client):
    """WS 4: Simula una respuesta directa del modelo y verifica los eventos emitidos."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "message": {
            "role": "assistant",
            "content": "Las Varillas fue fundada en relación al ferrocarril."
        }
    }

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_resp)):
        with test_client.websocket_connect("/ws/chat") as websocket:
            websocket.send_json({"text": "¿Cuándo se fundó?", "use_mcp": False})
            
            # Recibir evento 'status' ("Pensando...")
            ev_status = websocket.receive_json()
            assert ev_status.get("type") == "status"
            
            # Recibir evento 'response'
            ev_resp = websocket.receive_json()
            assert ev_resp.get("type") == "response"
            assert "ferrocarril" in ev_resp.get("content", "").lower()
            
            # Recibir evento 'token'
            ev_token = websocket.receive_json()
            assert ev_token.get("type") == "token"

            # Recibir evento 'done'
            ev_done = websocket.receive_json()
            assert ev_done.get("type") == "done"


# --- WS 5: Cierre limpio ---
def test_ws_5_cierre_limpio_conexion(test_client):
    """WS 5: Verifica que el cierre de la conexión por parte del cliente se complete limpiamente."""
    with test_client.websocket_connect("/ws/chat") as websocket:
        websocket.close(code=1000)
