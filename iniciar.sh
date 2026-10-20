#!/usr/bin/env bash
# AUDITORIA SOLID (script): su unica responsabilidad es preparar el entorno y lanzar la app (SRP).
# La logica de la aplicacion NO esta aca: delega todo en web_server.py (DIP).
# Se movio al directorio donde esta este script, asi funciona desde cualquier carpeta.
cd "$(dirname "$0")"
# Si no existe la carpeta "venv", crea el entorno virtual de Python.
[ -d venv ] || python3 -m venv venv
# Activa el entorno virtual (usa sus paquetes y su Python).
source venv/bin/activate
# Instala las dependencias de requirements.txt en silencio (-q).
pip install -q -r requirements.txt
# Inicia el servidor web de VIA.
python web_server.py
