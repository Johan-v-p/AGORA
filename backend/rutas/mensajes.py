"""Rutas de mensajes privados."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required


def crear_blueprint(get_db, socketio):
    """Crea el Blueprint de mensajes privados."""
    blueprint = Blueprint('mensajes', __name__)

    @blueprint.route('/mensajes/no-leidos')
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

    @blueprint.route('/mensajes')
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

    @blueprint.route('/mensajes/<int:otro_id>')
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
            return redirect(url_for('mensajes.mensajes'))

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

    @blueprint.route('/mensajes/<int:conv_id>/enviar', methods=['POST'])
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
                'url': url_for('mensajes.ver_chat', otro_id=me)
            }, room=f"user_{receptor_id}")

        return {'ok': True, 'msg_id': msg_id, 'hora': hora}

    @blueprint.route('/mensajes/<int:conv_id>/archivar', methods=['POST'])
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
        return redirect(url_for('mensajes.mensajes'))

    return blueprint
