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

@app.route('/mensajes/no-leidos')
@login_required
def mensajes_no_leidos():
    """Devuelve el total de mensajes no leídos del usuario (para el badge del sidebar)."""
    conn = get_db()
    total = conn.execute("""
        SELECT COUNT(*) FROM mensajes m
        JOIN participantes_conversacion pc ON pc.conversacion_id = m.conversacion_id
            AND pc.usuario_id = ?
        WHERE m.autor_id != ? AND m.leido = 0
    """, (session['user_id'], session['user_id'])).fetchone()[0]
    conn.close()
    return {'total': total}


@app.route('/mensajes')
@login_required
def mensajes():
    """Lista de conversaciones activas del usuario, con preview y no-leídos."""
    conn = get_db()
    convs = conn.execute("""
        SELECT
            c.id,
            c.ultimo_msg,
            u.id     AS otro_id,
            u.nombre AS otro_nombre,
            (SELECT m2.contenido FROM mensajes m2
             WHERE m2.conversacion_id = c.id
             ORDER BY m2.creado_en DESC LIMIT 1) AS ultimo_texto,
            (SELECT COUNT(*) FROM mensajes m3
             WHERE m3.conversacion_id = c.id
               AND m3.autor_id != :me
               AND m3.leido = 0) AS no_leidos
        FROM conversaciones c
        JOIN participantes_conversacion pc  ON pc.conversacion_id = c.id
                                          AND pc.usuario_id = :me
                                          AND pc.archivada = 0
        JOIN participantes_conversacion pc2 ON pc2.conversacion_id = c.id
                                          AND pc2.usuario_id != :me
        JOIN usuarios u ON u.id = pc2.usuario_id
        ORDER BY c.ultimo_msg DESC
    """, {'me': session['user_id']}).fetchall()
    conn.close()
    return render_template('mensajes/lista.html',
                           pagina_activa='mensajes',
                           conversaciones=convs)


@app.route('/mensajes/<int:otro_id>')
@login_required
def ver_chat(otro_id):
    """Abre (o crea) la conversación 1-a-1 con otro usuario."""
    conn = get_db()
    otro = conn.execute(
        "SELECT id, nombre, carrera FROM usuarios WHERE id = ? AND activo = 1",
        (otro_id,)
    ).fetchone()
    if not otro:
        conn.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('mensajes'))

    me = session['user_id']

    # Buscar conversación existente
    conv = conn.execute("""
        SELECT c.id FROM conversaciones c
        JOIN participantes_conversacion p1 ON p1.conversacion_id = c.id AND p1.usuario_id = ?
        JOIN participantes_conversacion p2 ON p2.conversacion_id = c.id AND p2.usuario_id = ?
        LIMIT 1
    """, (me, otro_id)).fetchone()

    if conv:
        conv_id = conv['id']
    else:
        cur = conn.execute("INSERT INTO conversaciones DEFAULT VALUES")
        conv_id = cur.lastrowid
        conn.execute(
            "INSERT INTO participantes_conversacion (conversacion_id, usuario_id) VALUES (?,?)",
            (conv_id, me))
        conn.execute(
            "INSERT INTO participantes_conversacion (conversacion_id, usuario_id) VALUES (?,?)",
            (conv_id, otro_id))
        conn.commit()

    # Marcar como leídos
    conn.execute("""
        UPDATE mensajes SET leido = 1
        WHERE conversacion_id = ? AND autor_id != ? AND leido = 0
    """, (conv_id, me))
    conn.commit()

    mensajes_list = conn.execute("""
        SELECT m.id, m.autor_id, m.contenido, m.leido, m.creado_en,
               u.nombre AS autor_nombre
        FROM mensajes m
        JOIN usuarios u ON u.id = m.autor_id
        WHERE m.conversacion_id = ?
        ORDER BY m.creado_en ASC
    """, (conv_id,)).fetchall()

    conn.close()
    return render_template('mensajes/chat.html',
                           pagina_activa='mensajes',
                           otro=otro,
                           conv_id=conv_id,
                           mensajes=mensajes_list,
                           user_id=me)


@app.route('/mensajes/<int:conv_id>/enviar', methods=['POST'])
@login_required
def enviar_mensaje(conv_id):
    """Guarda el mensaje y lo emite en tiempo real por Socket.IO."""
    contenido = request.form.get('contenido', '').strip()
    if not contenido or len(contenido) > 1000:
        return ('', 400)

    me = session['user_id']
    conn = get_db()

    participa = conn.execute("""
        SELECT 1 FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conv_id, me)).fetchone()
    if not participa:
        conn.close()
        return ('', 403)

    cur = conn.execute("""
        INSERT INTO mensajes (conversacion_id, autor_id, contenido)
        VALUES (?, ?, ?)
    """, (conv_id, me, contenido))
    msg_id = cur.lastrowid

    conn.execute(
        "UPDATE conversaciones SET ultimo_msg = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,))

    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, me)).fetchone()

    msg_row = conn.execute(
        "SELECT creado_en FROM mensajes WHERE id = ?", (msg_id,)
    ).fetchone()
    hora = msg_row['creado_en'][11:16] if msg_row else ''

    conn.commit()
    conn.close()

    payload = {
        'msg_id':    msg_id,
        'conv_id':   conv_id,
        'autor_id':  me,
        'nombre':    session['nombre'],
        'contenido': contenido,
        'hora':      hora,
    }
    # Emitir al remitente y al receptor
    socketio.emit('mensaje_nuevo', payload, room=f"user_{me}")
    if otro:
        receptor_id = otro['usuario_id']
        socketio.emit('mensaje_nuevo', payload, room=f"user_{receptor_id}")
        socketio.emit('notificacion', {
            'mensaje': f"{session['nombre']} te envió un mensaje.",
            'url': url_for('ver_chat', otro_id=me)
        }, room=f"user_{receptor_id}")

    return {'ok': True, 'msg_id': msg_id, 'hora': hora}


@app.route('/mensajes/<int:conv_id>/archivar', methods=['POST'])
@login_required
def archivar_conversacion(conv_id):
    """Oculta la conversación de la lista sin borrarla."""
    conn = get_db()
    conn.execute("""
        UPDATE participantes_conversacion
        SET archivada = 1
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conv_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Conversación archivada.', 'success')
    return redirect(url_for('mensajes'))


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