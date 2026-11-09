"""Rutas del feed y de las publicaciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.nucleo.utilidades import tiempo_relativo


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
        cur  = conn.cursor()

        query = """
            SELECT
                p.id,
                p.autor_id,
                p.titulo,
                p.contenido,
                p.categoria,
                p.es_anonimo,
                p.creado_en,
                u.nombre            AS autor_nombre,
                u.avatar_url        AS autor_avatar,
                (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id)
                                    AS total_reacciones,
                (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id)
                                    AS total_comentarios
            FROM publicaciones p
            JOIN usuarios u ON u.id = p.autor_id
            WHERE p.estado = 'publicado'
        """

        if filtro in ('academico', 'meme', 'foro', 'portafolio', 'general'):
            cur.execute(query + " AND p.categoria = ? ORDER BY p.creado_en DESC", (filtro,))
        else:
            cur.execute(query + " ORDER BY p.creado_en DESC")

        filas = cur.fetchall()
        conn.close()

        posts = []
        for fila in filas:
            d = dict(fila)
            d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
            posts.append(d)

        return render_template('publicaciones/feed.html', posts=posts, filtro=filtro)

    @blueprint.route('/nueva-publicacion', methods=['POST'])
    @login_required
    def nueva_publicacion():
        titulo     = request.form.get('titulo', '').strip()
        contenido  = request.form.get('contenido', '').strip()
        categoria  = request.form.get('categoria', 'general').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') == '1' else 0

        if not titulo or not contenido:
            flash('El título y el contenido son obligatorios.', 'error')
            return redirect(url_for('publicaciones.feed'))

        if categoria not in ('general', 'academico', 'foro', 'meme', 'portafolio'):
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
            conn.execute(
                """INSERT INTO publicaciones (autor_id, titulo, contenido, categoria, es_anonimo, estado)
                   VALUES (?, ?, ?, ?, ?, 'publicado')""",
                (session['user_id'], titulo, contenido, categoria, es_anonimo)
            )
            conn.commit()
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
        cur  = conn.cursor()

        cur.execute("""
            SELECT
                p.id, p.autor_id, p.titulo, p.contenido, p.categoria,
                p.es_anonimo, p.creado_en,
                u.nombre AS autor_nombre,
                (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
                (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
            FROM publicaciones p
            JOIN usuarios u ON u.id = p.autor_id
            WHERE p.id = ? AND p.estado = 'publicado'
        """, (post_id,))
        post = cur.fetchone()

        if not post:
            conn.close()
            flash('Publicación no encontrada.', 'error')
            return redirect(url_for('publicaciones.feed'))

        post = dict(post)
        post['tiempo_relativo'] = tiempo_relativo(post['creado_en'])

        cur.execute("""
            SELECT c.id, c.contenido, c.creado_en, 0 AS es_anonimo, u.nombre AS autor_nombre
            FROM comentarios c
            JOIN usuarios u ON u.id = c.autor_id
            WHERE c.publicacion_id = ?
            ORDER BY c.creado_en ASC
        """, (post_id,))
        filas = cur.fetchall()

        cur.execute(
            "SELECT 1 FROM reacciones_publicacion WHERE publicacion_id = ? AND usuario_id = ?",
            (post_id, session['user_id'])
        )
        ya_reaccione = cur.fetchone() is not None
        conn.close()

        comentarios = []
        for fila in filas:
            d = dict(fila)
            d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
            comentarios.append(d)

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
            cur = conn.cursor()
            cur.execute("SELECT id FROM publicaciones WHERE id = ? AND estado = 'publicado'", (post_id,))
            if not cur.fetchone():
                flash('Publicación no encontrada.', 'error')
                return redirect(url_for('publicaciones.feed'))

            conn.execute(
                "INSERT INTO comentarios (publicacion_id, autor_id, contenido) VALUES (?, ?, ?)",
                (post_id, session['user_id'], contenido)
            )
            conn.commit()
        except Exception as e:
            flash(f'Error al comentar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('publicaciones.post_detalle', post_id=post_id))

    @blueprint.route('/reaccionar/<int:post_id>', methods=['POST'])
    @login_required
    def reaccionar(post_id):
        user_id = session['user_id']
        conn    = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT usuario_id FROM reacciones_publicacion WHERE publicacion_id = ? AND usuario_id = ?",
                (post_id, user_id)
            )
            if cur.fetchone():
                conn.execute(
                    "DELETE FROM reacciones_publicacion WHERE publicacion_id = ? AND usuario_id = ?",
                    (post_id, user_id)
                )
                activa = False
            else:
                conn.execute(
                    "INSERT INTO reacciones_publicacion (publicacion_id, usuario_id, tipo) VALUES (?, ?, 'aplauso')",
                    (post_id, user_id)
                )
                activa = True
            conn.commit()

            cur.execute("SELECT COUNT(*) AS total FROM reacciones_publicacion WHERE publicacion_id = ?", (post_id,))
            total = cur.fetchone()['total']
            return jsonify({'ok': True, 'activa': activa, 'total': total})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    @blueprint.route('/editar/<int:post_id>', methods=['GET', 'POST'])
    @login_required
    def editar_publicacion(post_id):
        conn = get_db()
        cur  = conn.cursor()
        cur.execute(
            "SELECT * FROM publicaciones WHERE id = ? AND autor_id = ? AND estado = 'publicado'",
            (post_id, session['user_id'])
        )
        post = cur.fetchone()

        if not post:
            conn.close()
            flash('Publicación no encontrada o sin permiso.', 'error')
            return redirect(url_for('perfil'))

        if request.method == 'POST':
            titulo    = request.form.get('titulo', '').strip()
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

            if categoria not in ('general', 'academico', 'foro', 'meme', 'portafolio'):
                flash('Categoría no válida.', 'error')
                conn.close()
                return redirect(url_for('publicaciones.editar_publicacion', post_id=post_id))

            try:
                conn.execute(
                    "UPDATE publicaciones SET titulo = ?, contenido = ?, categoria = ? WHERE id = ?",
                    (titulo, contenido, categoria, post_id)
                )
                conn.commit()
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
            cur = conn.cursor()
            cur.execute(
                "SELECT id FROM publicaciones WHERE id = ? AND autor_id = ? AND estado = 'publicado'",
                (post_id, session['user_id'])
            )
            if not cur.fetchone():
                flash('Publicación no encontrada o sin permiso.', 'error')
                return redirect(url_for('perfil'))

            conn.execute("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", (post_id,))
            conn.commit()
            flash('Publicación eliminada.', 'success')
        except Exception as e:
            flash(f'Error al eliminar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('perfil'))

    return blueprint
