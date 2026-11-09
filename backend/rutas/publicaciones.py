"""Rutas del feed y de las publicaciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import publicaciones as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de publicaciones."""
    blueprint = Blueprint('publicaciones', __name__)

    @blueprint.route('/')
    def index():
        if session.get('user_id'):
            return redirect(url_for('publicaciones.feed'))
        return redirect(url_for('autenticacion.login'))

    @blueprint.route('/feed')
    @login_required
    def feed():
        filtro = request.args.get('f', 'todo')
        conn = get_db()
        posts = servicio.listar_feed(conn, filtro)
        conn.close()
        return render_template('publicaciones/feed.html', posts=posts, filtro=filtro)

    @blueprint.route('/nueva-publicacion', methods=['POST'])
    @login_required
    def nueva_publicacion():
        titulo = request.form.get('titulo', '').strip()
        contenido = request.form.get('contenido', '').strip()
        categoria = request.form.get('categoria', 'general').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') == '1' else 0

        if not titulo or not contenido:
            flash('El título y el contenido son obligatorios.', 'error')
            return redirect(url_for('publicaciones.feed'))

        if categoria not in servicio.CATEGORIAS:
            flash('Categoría no válida.', 'error')
            return redirect(url_for('publicaciones.feed'))

        if len(titulo) > 120:
            flash('El título no puede superar 120 caracteres.', 'error')
            return redirect(url_for('publicaciones.feed'))

        if len(contenido) > 2000:
            flash('El contenido no puede superar 2000 caracteres.', 'error')
            return redirect(url_for('publicaciones.feed'))

        conn = get_db()
        try:
            servicio.crear(conn, session['user_id'], titulo, contenido, categoria, es_anonimo)
            flash('¡Publicación creada!', 'success')
        except Exception as e:
            flash(f'Error al publicar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('publicaciones.feed'))

    @blueprint.route('/post/<int:post_id>')
    @login_required
    def post_detalle(post_id):
        conn = get_db()
        post = servicio.obtener_detalle(conn, post_id)

        if not post:
            conn.close()
            flash('Publicación no encontrada.', 'error')
            return redirect(url_for('publicaciones.feed'))

        comentarios = servicio.listar_comentarios(conn, post_id)
        ya_reaccione = servicio.ya_reacciono(conn, post_id, session['user_id'])
        conn.close()

        return render_template('publicaciones/detalle.html',
                               post=post,
                               comentarios=comentarios,
                               ya_reaccione=ya_reaccione,
                               es_propio=(post.get('autor_id') == session['user_id']))

    @blueprint.route('/comentar/<int:post_id>', methods=['POST'])
    @login_required
    def comentar(post_id):
        contenido = request.form.get('contenido', '').strip()
        if not contenido:
            flash('El comentario no puede estar vacío.', 'error')
            return redirect(url_for('publicaciones.post_detalle', post_id=post_id))

        if len(contenido) > 1000:
            flash('El comentario no puede superar 1000 caracteres.', 'error')
            return redirect(url_for('publicaciones.post_detalle', post_id=post_id))

        conn = get_db()
        try:
            if not servicio.esta_publicada(conn, post_id):
                flash('Publicación no encontrada.', 'error')
                return redirect(url_for('publicaciones.feed'))

            servicio.comentar(conn, post_id, session['user_id'], contenido)
        except Exception as e:
            flash(f'Error al comentar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('publicaciones.post_detalle', post_id=post_id))

    @blueprint.route('/reaccionar/<int:post_id>', methods=['POST'])
    @login_required
    def reaccionar(post_id):
        conn = get_db()
        try:
            activa, total = servicio.alternar_reaccion(conn, post_id, session['user_id'])
            return jsonify({'ok': True, 'activa': activa, 'total': total})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    @blueprint.route('/editar/<int:post_id>', methods=['GET', 'POST'])
    @login_required
    def editar_publicacion(post_id):
        conn = get_db()
        post = servicio.obtener_propia(conn, post_id, session['user_id'])

        if not post:
            conn.close()
            flash('Publicación no encontrada o sin permiso.', 'error')
            return redirect(url_for('social.perfil'))

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            contenido = request.form.get('contenido', '').strip()
            categoria = request.form.get('categoria', post['categoria']).strip()

            if not titulo or not contenido:
                flash('El título y el contenido son obligatorios.', 'error')
                conn.close()
                return redirect(url_for('publicaciones.editar_publicacion', post_id=post_id))

            if len(titulo) > 120 or len(contenido) > 2000:
                flash('El contenido supera el límite de caracteres.', 'error')
                conn.close()
                return redirect(url_for('publicaciones.editar_publicacion', post_id=post_id))

            if categoria not in servicio.CATEGORIAS:
                flash('Categoría no válida.', 'error')
                conn.close()
                return redirect(url_for('publicaciones.editar_publicacion', post_id=post_id))

            try:
                servicio.actualizar(conn, post_id, titulo, contenido, categoria)
                flash('Publicación actualizada.', 'success')
            except Exception as e:
                flash(f'Error al actualizar: {e}', 'error')
            finally:
                conn.close()

            return redirect(url_for('publicaciones.post_detalle', post_id=post_id))

        conn.close()
        return render_template('publicaciones/editar.html', post=dict(post))

    @blueprint.route('/eliminar/<int:post_id>', methods=['POST'])
    @login_required
    def eliminar_publicacion(post_id):
        conn = get_db()
        try:
            if not servicio.obtener_propia(conn, post_id, session['user_id']):
                flash('Publicación no encontrada o sin permiso.', 'error')
                return redirect(url_for('social.perfil'))

            servicio.marcar_eliminada(conn, post_id)
            flash('Publicación eliminada.', 'success')
        except Exception as e:
            flash(f'Error al eliminar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('social.perfil'))

    return blueprint
