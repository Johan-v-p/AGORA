"""Crea la aplicación de ÁGORA y registra sus módulos."""

import sqlite3
import sys
import threading

from flask import Flask, flash, redirect, request, session, url_for
from flask_socketio import SocketIO

from backend.nucleo import imagenes
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
from backend.servicios import cuentas
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
# Tope de la petición completa: una imagen (2 MB) más 1 MB para el resto del formulario.
app.config['MAX_CONTENT_LENGTH'] = imagenes.MAX_BYTES + 1024 * 1024

DB = CONFIGURACION['DATABASE_PATH']
_migraciones_tema = set()
_bloqueo_migraciones = threading.Lock()


def _asegurar_columna_tema(conn):
    """Agrega la preferencia de tema una sola vez por base de datos."""
    ruta_db = str(DB)
    if ruta_db in _migraciones_tema:
        return

    with _bloqueo_migraciones:
        if ruta_db in _migraciones_tema:
            return
        columnas = conn.execute("PRAGMA table_info(usuarios)").fetchall()
        if not columnas:
            return
        if not any(columna['name'] == 'tema' for columna in columnas):
            try:
                conn.execute(
                    "ALTER TABLE usuarios ADD COLUMN tema TEXT NOT NULL DEFAULT 'system'"
                )
                conn.commit()
            except sqlite3.OperationalError as error:
                if 'duplicate column name' not in str(error).lower():
                    raise
        _migraciones_tema.add(ruta_db)


def get_db():
    """Abre una conexión SQLite y devuelve filas como diccionarios."""
    conn = abrir_conexion(DB)
    _asegurar_columna_tema(conn)
    return conn


def obtener_cuenta(user_id):
    """Devuelve el estado actual (activo, rol) de una cuenta, o None si no existe."""
    conn = get_db()
    cuenta = cuentas.obtener_estado(conn, user_id)
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


@app.template_filter('media')
def filtro_media(ruta, miniatura=False):
    """Convierte la ruta guardada en la BD en una URL usable en <img src>.

    Las rutas 'uploads/...' se sirven desde static; cualquier otro valor
    (por ejemplo una URL externa antigua) se devuelve igual.
    """
    if not ruta:
        return ''
    if ruta.startswith('uploads/'):
        if miniatura:
            ruta = imagenes.ruta_miniatura(ruta)
        return url_for('static', filename=ruta)
    return ruta


@app.errorhandler(413)
def archivo_demasiado_grande(_error):
    """Avisa al usuario en lugar de mostrar la página de error cruda."""
    flash('El archivo es demasiado grande. El máximo es 2 MB.', 'error')
    destino = request.referrer
    if not destino or not destino.startswith(request.host_url):
        destino = '/'
    return redirect(destino)


@app.context_processor
def inyectar_avatar():
    """Deja la foto del usuario en sesión disponible como `mi_avatar` en todas las plantillas."""
    user_id = session.get('user_id')
    if not user_id:
        return {}
    conn = get_db()
    usuario = cuentas.obtener_por_id(conn, user_id)
    conn.close()
    tema = usuario['tema'] if usuario and 'tema' in usuario.keys() else 'system'
    if tema not in {'light', 'dark', 'system'}:
        tema = 'system'
    return {
        'mi_avatar': usuario['avatar_url'] if usuario else None,
        'tema_usuario': tema,
        'usuario_autenticado': bool(usuario),
    }


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
