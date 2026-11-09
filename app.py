"""Punto de entrada compatible para ejecutar ÁGORA."""

import sys

from backend import aplicacion


if __name__ == '__main__':
    aplicacion.socketio.run(
        aplicacion.app,
        host='0.0.0.0',
        port=5000,
        debug=aplicacion.CONFIGURACION['FLASK_DEBUG'],
    )


sys.modules[__name__] = aplicacion
