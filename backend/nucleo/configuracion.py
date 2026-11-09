"""Configuración de la aplicación a partir de variables de entorno."""

import os
from pathlib import Path


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
RUTA_BASE_DATOS = RAIZ_PROYECTO / 'data' / 'agora.db'


def obtener_configuracion() -> dict[str, object]:
    """Devuelve la configuración de ejecución de ÁGORA."""
    return {
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-only-change-me'),
        'DATABASE_PATH': os.environ.get('DATABASE_PATH', str(RUTA_BASE_DATOS)),
        'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', '').lower()
        in {'1', 'true', 'yes'},
    }
