@echo off
REM AUDITORIA SOLID (script): su unica responsabilidad es preparar el entorno y lanzar la app (SRP).
REM La logica de la aplicacion NO esta aca: delega todo en web_server.py (DIP).
REM Usa codificacion UTF-8 en la consola (nul oculta el mensaje).
chcp 65001 >nul
REM Se mueve a la carpeta donde esta este archivo (%~dp0).
cd /d "%~dp0"
REM Si no existe la carpeta venv...
if not exist venv (
  REM ...avisa que va a crear el entorno virtual...
  echo Creando entorno virtual...
  REM ...y lo crea.
  python -m venv venv
)
REM Activa el entorno virtual.
call venv\Scripts\activate.bat
REM Instala las dependencias en silencio (-q).
pip install -q -r requirements.txt
REM Inicia el servidor web de VIA.
python web_server.py
REM Deja la ventana abierta para ver mensajes o errores.
pause
