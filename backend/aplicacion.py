"""
app.py — Servidor principal de ÁGORA
Corre en LAN: python app.py  →  http://0.0.0.0:5000
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room
from datetime import datetime
import json
import sqlite3
import sys
from werkzeug.security import check_password_hash, generate_password_hash
from backend.nucleo.base_datos import abrir_conexion
from backend.nucleo.configuracion import obtener_configuracion
from backend.nucleo.utilidades import (
    parsear_tecnologias,
    procesar_evento,
    tiempo_relativo,
)
from backend.servicios.moderacion import (
    ACCIONES_REPORTE,
    ESTADOS_ABIERTOS,
    SQL_REPORTE_ABIERTO,
    TIPOS_REPORTE,
    obtener_usuario_reportado as resolver_usuario_reportado,
    motivo_para_no_suspender as evaluar_suspension,
)
from backend.rutas.autenticacion import crear_blueprint as crear_blueprint_autenticacion
from backend.rutas.mensajes import crear_blueprint as crear_blueprint_mensajes
from backend.rutas.moderacion import crear_blueprint as crear_blueprint_moderacion
from backend.rutas.ajustes import crear_blueprint as crear_blueprint_ajustes
from backend.rutas.eventos import crear_blueprint as crear_blueprint_eventos
from backend.rutas.portafolio import crear_blueprint as crear_blueprint_portafolio
from backend.rutas.foros import crear_blueprint as crear_blueprint_foros
from backend.rutas.social import crear_blueprint as crear_blueprint_social
from backend.rutas.publicaciones import crear_blueprint as crear_blueprint_publicaciones
from backend.rutas.decoradores import crear_moderador_required, login_required

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

# ──────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────
def get_db():
    """Abre una conexión SQLite y devuelve filas como diccionarios."""
    return abrir_conexion(DB)


app.register_blueprint(crear_blueprint_autenticacion(get_db))
app.register_blueprint(crear_blueprint_mensajes(get_db, socketio))
app.register_blueprint(crear_blueprint_moderacion(get_db))
app.register_blueprint(crear_blueprint_ajustes(get_db))
app.register_blueprint(crear_blueprint_eventos(get_db))
app.register_blueprint(crear_blueprint_portafolio(get_db))
app.register_blueprint(crear_blueprint_foros(get_db))
app.register_blueprint(crear_blueprint_social(get_db, socketio))
app.register_blueprint(crear_blueprint_publicaciones(get_db))
moderador_required = crear_moderador_required(get_db)


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




# ══════════════════════════════════════════
# RUTAS PÚBLICAS
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# FEED
# ══════════════════════════════════════════



# ── NUEVA PUBLICACIÓN ───────────────────────


# ── POST DETALLE ────────────────────────────


# ── COMENTAR ────────────────────────────────


# ── REACCIONAR (AJAX) ────────────────────────


# ── EDITAR PUBLICACIÓN ─────────────────────


# ── ELIMINAR PUBLICACIÓN ──────────────────


# ══════════════════════════════════════════
# PERFIL
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# EXPLORAR
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# FOROS
# ══════════════════════════════════════════







# ── FORO PREGUNTA DETALLE ── ★ NUEVO ────────


# ── NUEVA RESPUESTA ── ★ NUEVO ─────────────


# ── ACEPTAR RESPUESTA (solo el autor) ── ★ NUEVO ──


# ── VOTAR RESPUESTA (AJAX) ── ★ NUEVO ──────


# ══════════════════════════════════════════
# PORTAFOLIO  ★ NUEVO
# ══════════════════════════════════════════







# ══════════════════════════════════════════
# EVENTOS  ★ NUEVO
# ══════════════════════════════════════════









# ══════════════════════════════════════════
# AJUSTES DE CUENTA
# ══════════════════════════════════════════






# ══════════════════════════════════════════
# SEGUIMIENTO
# ══════════════════════════════════════════







# ══════════════════════════════════════════
# NOTIFICACIONES
# ══════════════════════════════════════════




# ══════════════════════════════════════════
# MODERACIÓN
# ══════════════════════════════════════════















# ══════════════════════════════════════════
# EVENTOS — Ver / Editar / Eliminar / Participantes
# ══════════════════════════════════════════









# ══════════════════════════════════════════
# RUTAS PENDIENTES DE IMPLEMENTAR
# (stubs funcionales para que no explote el sidebar)
# ══════════════════════════════════════════









# ══════════════════════════════════════════
# MENSAJES PRIVADOS
# ══════════════════════════════════════════











# ══════════════════════════════════════════
# SOCKETIO — Eventos
# ══════════════════════════════════════════

@socketio.on('connect')
def on_connect():
    # before_request no se ejecuta en las conexiones de Socket.IO
    if session.get('user_id'):
        cuenta = obtener_cuenta(session['user_id'])
        if not cuenta or not cuenta['activo']:
            return False

    if session.get('user_id'):
        join_room(f"user_{session['user_id']}")

@socketio.on('disconnect')
def on_disconnect():
    if session.get('user_id'):
        leave_room(f"user_{session['user_id']}")

@socketio.on('escribiendo')
def on_escribiendo(data):
    """Retransmite 'escribiendo…' al otro participante del chat."""
    conv_id  = data.get('conv_id')
    autor_id = data.get('autor_id')
    if not conv_id or not autor_id:
        return
    conn = get_db()
    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, autor_id)).fetchone()
    conn.close()
    if otro:
        socketio.emit('escribiendo', data, room=f"user_{otro['usuario_id']}")

@socketio.on('dejo_escribir')
def on_dejo_escribir(data):
    """Retransmite 'dejó de escribir' al otro participante."""
    conv_id  = data.get('conv_id')
    autor_id = data.get('autor_id')
    if not conv_id or not autor_id:
        return
    conn = get_db()
    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, autor_id)).fetchone()
    conn.close()
    if otro:
        socketio.emit('dejo_escribir', data, room=f"user_{otro['usuario_id']}")


# ══════════════════════════════════════════
# ARRANQUE
# ══════════════════════════════════════════