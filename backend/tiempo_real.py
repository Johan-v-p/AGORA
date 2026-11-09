"""Eventos de Socket.IO para mensajería y notificaciones en tiempo real."""

from flask import session
from flask_socketio import join_room, leave_room


def registrar_eventos(socketio, get_db, obtener_cuenta):
    """Registra los manejadores de Socket.IO de la aplicación."""

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
