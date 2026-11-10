"""Rutas de perfiles, exploración, seguimiento y notificaciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import social as servicio


def crear_blueprint(get_db, socketio):
    """Crea el Blueprint de la parte social."""
    blueprint = Blueprint('social', __name__)

    @blueprint.route('/perfil')
    @login_required
    def perfil():
        user_id = session['user_id']
        conn = get_db()
        usuario = servicio.obtener_usuario(conn, user_id)
        stats = servicio.estadisticas_propias(conn, user_id)
        mis_posts = servicio.publicaciones_recientes(conn, user_id)
        conn.close()

        return render_template('social/perfil.html',
                               usuario=usuario,
                               stats=stats,
                               mis_posts=mis_posts)

    @blueprint.route('/explorar')
    @login_required
    def explorar():
        q = request.args.get('q', '').strip()
        tipo = request.args.get('tipo', 'todo')

        if tipo not in servicio.TIPOS_BUSQUEDA:
            tipo = 'todo'

        conn = get_db()
        if q:
            posts, personas, foros = servicio.buscar(conn, q, tipo)
        else:
            posts, personas, foros = servicio.destacados(conn, session['user_id'])
        conn.close()

        return render_template('social/explorar.html', q=q, tipo=tipo, posts=posts, personas=personas, foros=foros)

    @blueprint.route('/tendencias')
    @login_required
    def tendencias():
        conn = get_db()
        top_posts = servicio.listar_tendencias(conn)
        top_tags = servicio.hashtags_populares(conn)
        conn.close()
        return render_template('social/tendencias.html', top_posts=top_posts, top_tags=top_tags,
                               pagina_activa='tendencias')

    @blueprint.route('/tendencias/<tag>')
    @login_required
    def tendencia_tag(tag):
        etiqueta = tag.strip().lstrip('#').lower()
        conn = get_db()
        top_posts = servicio.listar_por_hashtag(conn, etiqueta)
        top_tags = servicio.hashtags_populares(conn)
        conn.close()
        return render_template('social/tendencias.html', top_posts=top_posts, top_tags=top_tags,
                               tag_activo=etiqueta, pagina_activa='tendencias')

    @blueprint.route('/seguir/<int:objetivo_id>', methods=['POST'])
    @login_required
    def seguir_usuario(objetivo_id):
        user_id = session['user_id']
        if objetivo_id == user_id:
            return jsonify({'ok': False}), 400
        conn = get_db()
        try:
            if not servicio.ya_sigue(conn, user_id, objetivo_id):
                mensaje = f"{session['nombre']} comenzó a seguirte."
                url = url_for('social.ver_perfil_usuario', usuario_id=user_id)
                servicio.seguir(conn, user_id, objetivo_id, mensaje, url)
                socketio.emit('notificacion', {
                    'mensaje': mensaje,
                    'tipo': 'seguidor',
                    'url': url,
                }, room=f'user_{objetivo_id}')
            total = servicio.contar_seguidores(conn, objetivo_id)
            return jsonify({'ok': True, 'siguiendo': True, 'total_seguidores': total})
        finally:
            conn.close()

    @blueprint.route('/dejar-seguir/<int:objetivo_id>', methods=['POST'])
    @login_required
    def dejar_seguir_usuario(objetivo_id):
        conn = get_db()
        try:
            servicio.dejar_de_seguir(conn, session['user_id'], objetivo_id)
            total = servicio.contar_seguidores(conn, objetivo_id)
            return jsonify({'ok': True, 'siguiendo': False, 'total_seguidores': total})
        finally:
            conn.close()

    @blueprint.route('/perfil/<int:usuario_id>')
    @login_required
    def ver_perfil_usuario(usuario_id):
        viewer_id = session['user_id']
        conn = get_db()
        usuario = servicio.obtener_usuario_activo(conn, usuario_id)
        if not usuario:
            conn.close()
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('social.explorar'))

        stats = {
            'total_posts': servicio.contar_publicaciones(conn, usuario_id),
            'total_seguidores': servicio.contar_seguidores(conn, usuario_id),
            'total_siguiendo': servicio.contar_siguiendo(conn, usuario_id),
        }
        ya_sigue = servicio.ya_sigue(conn, viewer_id, usuario_id)
        posts = servicio.publicaciones_recientes(conn, usuario_id)
        conn.close()

        return render_template('social/perfil_usuario.html',
                               usuario=usuario,
                               stats=stats,
                               posts=posts, ya_sigue=ya_sigue,
                               es_propio=(viewer_id == usuario_id),
                               pagina_activa='perfil')

    def _lista_de_contactos(usuario_id, listar, modo):
        """Muestra los seguidores o seguidos de un usuario."""
        conn = get_db()
        usuario = servicio.obtener_usuario(conn, usuario_id)
        if not usuario:
            conn.close()
            return redirect(url_for('social.explorar'))
        lista = listar(conn, usuario_id)
        viewer_siguiendo = servicio.ids_seguidos(conn, session['user_id'])
        conn.close()
        return render_template('social/seguidores.html', usuario=usuario, lista=lista,
                               viewer_siguiendo=viewer_siguiendo, modo=modo, pagina_activa='perfil')

    @blueprint.route('/seguidores/<int:usuario_id>')
    @login_required
    def ver_seguidores(usuario_id):
        return _lista_de_contactos(usuario_id, servicio.listar_seguidores, 'seguidores')

    @blueprint.route('/siguiendo/<int:usuario_id>')
    @login_required
    def ver_siguiendo(usuario_id):
        return _lista_de_contactos(usuario_id, servicio.listar_siguiendo, 'siguiendo')

    @blueprint.route('/notificaciones')
    @login_required
    def notificaciones():
        conn = get_db()
        notifs = servicio.leer_notificaciones(conn, session['user_id'])
        conn.close()
        return render_template('social/notificaciones.html', notificaciones=notifs, pagina_activa='notificaciones')

    @blueprint.route('/notificaciones/no-leidas')
    @login_required
    def notificaciones_no_leidas():
        conn = get_db()
        total = servicio.contar_notificaciones_no_leidas(conn, session['user_id'])
        conn.close()
        return jsonify({'total': total})

    return blueprint
