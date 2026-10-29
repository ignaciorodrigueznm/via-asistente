"""
tests/conftest.py · Configuración global de pytest y resolución del PYTHONPATH.
Asegura que la raíz del proyecto esté en sys.path al ejecutar 'pytest'.
"""
import sys
import os

# Agregar la raíz del proyecto a sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

