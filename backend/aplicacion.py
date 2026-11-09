"""Crea la aplicación de ÁGORA y registra sus módulos."""

import sys

from flask import Flask, flash, redirect, request, session, url_for
from flask_socketio import SocketIO

from backend.nucleo.base_datos import abrir_conexion
from backend.nucleo.configuracion import obtener_configuracion
from backend.rutas.ajustes import crear_blueprint as crear_blueprint_ajustes
from backend.rutas.autenticacion import crear_blueprint as crear_blueprint_autenticacion
from backend.rutas.eventos import crear_blueprint as crear_blueprint_eventos
from backend.rutas.foros import crear_blueprint as crear_blueprint_foros
from backend.rutas.mensajes import crear_blueprint as crear_blueprint_mensajes
from backend.rutas.moderacion import crear_blueprint as crear_blueprint_moderacion
from backend.rutas.portafolio import crear_blueprint as crear_blueprint_portafolio
from backend.rutas.publicaciones import crear_blueprint as crear_blueprint_publicaciones
from backend.rutas.social import crear_blueprint as crear_blueprint_social
from backend.tiempo_real import registrar_eventos

# ── FIX: Python 3.14 redujo el límite de recursión por defecto.
# Jinja2 usa recursión interna al procesar extends + include anidados.
sys.setrecursionlimit(5000)

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static',
)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
CONFIGURACION = obtener_configuracion()
app.config['SECRET_KEY'] = CONFIGURACION['SECRET_KEY']

DB = CONFIGURACION['DATABASE_PATH']


def get_db():
    """Abre una conexión SQLite y devuelve filas como diccionarios."""
    return abrir_conexion(DB)


def obtener_cuenta(user_id):
    """Devuelve el estado actual (activo, rol) de una cuenta, o None si no existe."""
    conn = get_db()
    cuenta = conn.execute("SELECT activo, rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return cuenta


@app.before_request
def validar_sesion():
    """Expulsa las sesiones de cuentas suspendidas o borradas y mantiene el rol al día."""
    user_id = session.get('user_id')
    if not user_id or request.endpoint == 'static':
        return None

    cuenta = obtener_cuenta(user_id)
    if not cuenta or not cuenta['activo']:
        session.clear()
        flash('Tu cuenta está suspendida. Contacta a un administrador.', 'error')
        return redirect(url_for('autenticacion.login'))

    session['rol'] = cuenta['rol']
    return None


app.register_blueprint(crear_blueprint_autenticacion(get_db))
app.register_blueprint(crear_blueprint_publicaciones(get_db))
app.register_blueprint(crear_blueprint_social(get_db, socketio))
app.register_blueprint(crear_blueprint_foros(get_db))
app.register_blueprint(crear_blueprint_portafolio(get_db))
app.register_blueprint(crear_blueprint_eventos(get_db))
app.register_blueprint(crear_blueprint_ajustes(get_db))
app.register_blueprint(crear_blueprint_moderacion(get_db))
app.register_blueprint(crear_blueprint_mensajes(get_db, socketio))
registrar_eventos(socketio, get_db, obtener_cuenta)
