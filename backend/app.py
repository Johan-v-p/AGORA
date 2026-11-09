"""Punto de entrada para ejecutar ÁGORA."""

import sys
from pathlib import Path

# Permite ejecutar este archivo directamente: python backend/app.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import aplicacion  # noqa: E402

app = aplicacion.app


if __name__ == '__main__':
    aplicacion.socketio.run(
        aplicacion.app,
        host='0.0.0.0',
        port=5000,
        debug=aplicacion.CONFIGURACION['FLASK_DEBUG'],
    )
