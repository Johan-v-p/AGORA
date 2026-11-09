"""Configuración de la aplicación a partir de variables de entorno."""

import os


def obtener_configuracion() -> dict[str, object]:
    """Devuelve la configuración de ejecución de ÁGORA."""
    return {
        'SECRET_KEY': os.environ.get('SECRET_KEY', 'dev-only-change-me'),
        'DATABASE_PATH': os.environ.get('DATABASE_PATH', 'agora.db'),
        'FLASK_DEBUG': os.environ.get('FLASK_DEBUG', '').lower()
        in {'1', 'true', 'yes'},
    }
