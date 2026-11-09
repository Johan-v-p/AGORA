"""Rutas de mensajes privados."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import mensajes as servicio


def crear_blueprint(get_db, socketio):
    """Crea el Blueprint de mensajes privados."""
    blueprint = Blueprint('mensajes', __name__)

    @blueprint.route('/mensajes/no-leidos')
    @login_required
    def mensajes_no_leidos():
        """Devuelve el total de mensajes no leídos del usuario (para el badge del sidebar)."""
        conn = get_db()
        total = servicio.contar_no_leidos(conn, session['user_id'])
        conn.close()
        return {'total': total}

    @blueprint.route('/mensajes')
    @login_required
    def mensajes():
        """Lista de conversaciones activas del usuario, con preview y no-leídos."""
        conn = get_db()
        convs = servicio.listar_conversaciones(conn, session['user_id'])
        conn.close()
        return render_template('mensajes/lista.html',
                               pagina_activa='mensajes',
                               conversaciones=convs)

    @blueprint.route('/mensajes/<int:otro_id>')
    @login_required
    def ver_chat(otro_id):
        """Abre (o crea) la conversación 1-a-1 con otro usuario."""
        conn = get_db()
        otro = servicio.obtener_destinatario(conn, otro_id)
        if not otro:
            conn.close()
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('mensajes.mensajes'))

        me = session['user_id']
        conv_id = servicio.obtener_o_crear_conversacion(conn, me, otro_id)
        servicio.marcar_leidos(conn, conv_id, me)
        mensajes_list = servicio.listar_mensajes(conn, conv_id)
        conn.close()

        return render_template('mensajes/chat.html',
                               pagina_activa='mensajes',
                               otro=otro,
                               conv_id=conv_id,
                               mensajes=mensajes_list,
                               user_id=me)

    @blueprint.route('/mensajes/<int:conv_id>/enviar', methods=['POST'])
    @login_required
    def enviar_mensaje(conv_id):
        """Guarda el mensaje y lo emite en tiempo real por Socket.IO."""
        contenido = request.form.get('contenido', '').strip()
        if not contenido or len(contenido) > 1000:
            return ('', 400)

        me = session['user_id']
        conn = get_db()

        if not servicio.participa(conn, conv_id, me):
            conn.close()
            return ('', 403)

        msg_id, hora, otro = servicio.guardar_mensaje(conn, conv_id, me, contenido)
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
                'url': url_for('mensajes.ver_chat', otro_id=me)
            }, room=f"user_{receptor_id}")

        return {'ok': True, 'msg_id': msg_id, 'hora': hora}

    @blueprint.route('/mensajes/<int:conv_id>/archivar', methods=['POST'])
    @login_required
    def archivar_conversacion(conv_id):
        """Oculta la conversación de la lista sin borrarla."""
        conn = get_db()
        servicio.archivar(conn, conv_id, session['user_id'])
        conn.close()
        flash('Conversación archivada.', 'success')
        return redirect(url_for('mensajes.mensajes'))

    return blueprint
