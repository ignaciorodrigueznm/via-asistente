# CLAUDE.md

## Idioma
Código, comentarios, docstrings y mensajes de commit en español.

## Comandos
- **Backend**:
  - Arrancar: `python web_server.py` (ejecuta Starlette/Uvicorn en puerto 8000).
  - MCP independiente: `python server.py` (stdio).
  - Cliente CLI MCP: `python client.py`.
  - Pruebas unitarias: `pytest`
- **Frontend actual**: Servido como archivos estáticos por el backend en `/` (`index.html`, `js/via.js`, `css/`).
- **Backoffice (nuevo, Vite + React en 5174)**:
  - Instalar: `npm install` (en carpeta `backoffice/`)
  - Desarrollo: `npm run dev -- --port 5174`
  - Build: `npm run build`

## Arquitectura
- **Capa Presentación / Web (`web_server.py`, `js/via.js`, `index.html`)**: Servidor ASGI (Starlette) que expone endpoints REST (`/api/*`), WebSocket (`/ws/chat`) y archivos estáticos. No debe contener lógica directa de base de datos ni acceso a Mongo en crudo.
- **Capa Agente / Orquestación (`web_server.py:generar_respuesta`, `client.py`)**: Coordina el LLM (Ollama / modelo configurado) y herramientas MCP mediante llamadas stdio.
- **Capa Servidor MCP (`server.py`)**: Subproceso independiente que implementa FastMCP (`HistoriaVarillas`). Consulta datos y expone herramientas del protocolo MCP. No conoce HTTP.
- **Capa Datos / Repositorio (`repository.py` - nuevo)**: Abstracción única a MongoDB mediante `BookRepository`. No conoce HTTP ni detalles del protocolo MCP.
- **Capa Ingesta / Pipeline (`ingesta.py` - nuevo)**: Valida hash, limpia texto y fragmenta libros en unidades semánticas.

```
Navegador (Usuario :5173 / Backoffice :5174)
    │
    ▼ (HTTP / WebSocket)
web_server.py (Starlette / Router público y admin)
    ├── /ws/chat ──► Agente (Ollama/LLM) ──► Cliente MCP (stdio)
    │                                              │
    │                                              ▼
    │                                         server.py (FastMCP)
    │                                              │
    ▼                                              ▼
BookRepository (MongoBookRepository / FakeRepo en memoria)
    │
    ▼
MongoDB (libros, fragmentos, meta)
```

## Decisiones que no son obvias
- **MCP como subproceso**: El servidor MCP se inicia como subproceso con stdio desde el cliente o web_server. Al tener su propia conexión a Mongo, consulta `meta.version` para invalidar su caché en memoria cuando el backoffice publica un libro nuevo sin requerir reinicio del subproceso.
- **Subdivisión en memoria para búsqueda**: Mongo es la fuente de verdad persistente. En cada llamada, si `meta.version` no cambió, se conservan los fragmentos de libros publicados en memoria para mantener el buscador por tokens rápido y sin perder tolerancia a acentos.
- **Transporte por partes en Frontend vs Fragmentación semántica en Backend**: El cliente divide el `.txt` en bloques de transporte (~100.000 caracteres) sin cortar oraciones para evitar peticiones HTTP excesivas; el backend recibe, valida hash SHA-256 acumulado y hace la fragmentación semántica (~800-1500 caracteres) una vez ensamblado.

## Reglas del taller
- El contrato de la sección 17 es literal: los nombres de endpoints, campos y herramientas MCP no se modifican.
- Ningún secreto en el repositorio: credenciales, claves admin y URLs de Mongo van en `.env`. Existe siempre `.env.example`.
- Configuración obligatoria inválida: el backend no arranca y avisa con claridad sin imprimir contraseñas en logs ni terminal.
- Pruebas unitarias sin red ni Mongo real: se utiliza `FakeRepo` en memoria para tests automatizados.
- Cada cambio de comportamiento actualiza su respectiva especificación en `specs/`.

## Datos (Schema común sección 4.2 / 17.1)
- **libros**: `_id`, `slug` (único), `titulo`, `autor`, `anio`, `fuente_tipo`, `estado` ("borrador" | "publicado"), `resumen`, `temas` (lista de str normalizados), `hash_texto`, `creado` (ISODate).
- **fragmentos**: `_id`, `id` (slug_orden:02d, clave DOM y ancla), `libro_id` (ObjectId), `libro_slug`, `orden`, `seccion`, `titulo`, `contenido`, `tags` (normalizados: minúsculas, sin tildes, sin duplicados), `metadata` (dict libre), `tagueo` (`{origen: str, revisado: bool}`).
- **meta**: `_id: "corpus"`, `version: int` (contador que sube con cada publicación).
