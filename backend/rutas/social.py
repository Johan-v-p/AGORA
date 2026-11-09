"""Rutas de perfiles, exploración, seguimiento y notificaciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.nucleo.utilidades import tiempo_relativo


def crear_blueprint(get_db, socketio):
    """Crea el Blueprint de la parte social."""
    blueprint = Blueprint('social', __name__)

    @blueprint.route('/perfil')
    @login_required
    def perfil():
        user_id = session['user_id']
        conn    = get_db()
        cur     = conn.cursor()

        cur.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
        usuario = cur.fetchone()

        cur.execute("SELECT COUNT(*) AS total FROM publicaciones WHERE autor_id = ? AND estado = 'publicado'", (user_id,))
        total_posts = cur.fetchone()['total']

        cur.execute("""
            SELECT COUNT(*) AS total FROM reacciones_publicacion rp
            JOIN publicaciones p ON p.id = rp.publicacion_id
            WHERE p.autor_id = ?
        """, (user_id,))
        total_reacciones = cur.fetchone()['total']

        cur.execute("""
            SELECT COUNT(*) AS total FROM comentarios c
            JOIN publicaciones p ON p.id = c.publicacion_id
            WHERE p.autor_id = ?
        """, (user_id,))
        total_comentarios = cur.fetchone()['total']

        cur.execute("""
            SELECT
                p.id, p.titulo, p.categoria, p.creado_en,
                (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
                (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
            FROM publicaciones p
            WHERE p.autor_id = ? AND p.estado = 'publicado'
            ORDER BY p.creado_en DESC
            LIMIT 10
        """, (user_id,))
        filas = cur.fetchall()
        conn.close()

        mis_posts = []
        for fila in filas:
            d = dict(fila)
            d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
            mis_posts.append(d)

        stats = {
            'total_posts':       total_posts,
            'total_reacciones':  total_reacciones,
            'total_comentarios': total_comentarios,
        }

        return render_template('social/perfil.html',
                               usuario=usuario,
                               stats=stats,
                               mis_posts=mis_posts)

    @blueprint.route('/explorar')
    @login_required
    def explorar():
        q    = request.args.get('q', '').strip()
        tipo = request.args.get('tipo', 'todo')

        if tipo not in ('todo', 'posts', 'personas', 'foros'):
            tipo = 'todo'

        posts = []; personas = []; foros = []
        conn = get_db()
        cur  = conn.cursor()

        if q:
            termino = f'%{q}%'

            if tipo in ('todo', 'posts'):
                cur.execute("""
                    SELECT p.id, p.titulo, p.contenido, p.categoria, p.es_anonimo, p.creado_en,
                           u.nombre AS autor_nombre,
                           (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
                           (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
                    FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
                    WHERE p.estado = 'publicado' AND (p.titulo LIKE ? OR p.contenido LIKE ?)
                    ORDER BY p.creado_en DESC LIMIT 20
                """, (termino, termino))
                for f in cur.fetchall():
                    d = dict(f); d['tiempo_relativo'] = tiempo_relativo(d['creado_en']); posts.append(d)

            if tipo in ('todo', 'personas'):
                cur.execute("""
                    SELECT id, nombre, carrera, universidad FROM usuarios
                    WHERE activo = 1 AND (nombre LIKE ? OR carrera LIKE ? OR universidad LIKE ?)
                    ORDER BY nombre ASC LIMIT 20
                """, (termino, termino, termino))
                personas = [dict(r) for r in cur.fetchall()]

            if tipo in ('todo', 'foros'):
                cur.execute("""
                    SELECT f.id, f.nombre, f.descripcion, f.categoria,
                           (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
                    FROM foros f WHERE f.nombre LIKE ? OR f.descripcion LIKE ?
                    ORDER BY total_preguntas DESC LIMIT 20
                """, (termino, termino))
                foros = [dict(r) for r in cur.fetchall()]
        else:
            cur.execute("""
                SELECT p.id, p.titulo, p.categoria, p.es_anonimo, p.creado_en,
                       u.nombre AS autor_nombre,
                       (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
                       (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
                FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
                WHERE p.estado = 'publicado' ORDER BY p.creado_en DESC LIMIT 6
            """)
            for f in cur.fetchall():
                d = dict(f); d['tiempo_relativo'] = tiempo_relativo(d['creado_en']); posts.append(d)

            cur.execute("""
                SELECT f.id, f.nombre, f.descripcion, f.categoria,
                       (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
                FROM foros f ORDER BY total_preguntas DESC LIMIT 5
            """)
            foros = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT id, nombre, carrera, universidad FROM usuarios
                WHERE activo = 1 AND id != ? ORDER BY creado_en DESC LIMIT 6
            """, (session['user_id'],))
            personas = [dict(r) for r in cur.fetchall()]

        conn.close()
        return render_template('social/explorar.html', q=q, tipo=tipo, posts=posts, personas=personas, foros=foros)

    @blueprint.route('/tendencias')
    @login_required
    def tendencias():
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT p.id, p.titulo, p.categoria, p.creado_en,
                   u.nombre AS autor,
                   COUNT(DISTINCT r.id) AS total_reacciones,
                   COUNT(DISTINCT c.id) AS total_comentarios
            FROM publicaciones p
            JOIN usuarios u ON u.id = p.autor_id
            LEFT JOIN reacciones_publicacion r ON r.publicacion_id = p.id
            LEFT JOIN comentarios c ON c.publicacion_id = p.id
            WHERE p.estado = 'publicado'
              AND p.creado_en >= datetime('now', '-7 days')
            GROUP BY p.id
            ORDER BY (COUNT(DISTINCT r.id) + COUNT(DISTINCT c.id)) DESC
            LIMIT 20
        """)
        posts = cur.fetchall()
        conn.close()
        return render_template('social/tendencias.html', posts=posts, pagina_activa='tendencias')

    @blueprint.route('/seguir/<int:objetivo_id>', methods=['POST'])
    @login_required
    def seguir_usuario(objetivo_id):
        user_id = session['user_id']
        if objetivo_id == user_id:
            return jsonify({'ok': False}), 400
        conn = get_db()
        try:
            existe = conn.execute(
                "SELECT 1 FROM seguidores WHERE seguidor_id = ? AND seguido_id = ?",
                (user_id, objetivo_id)).fetchone()
            if not existe:
                conn.execute("INSERT INTO seguidores (seguidor_id, seguido_id) VALUES (?, ?)",
                    (user_id, objetivo_id))
                conn.execute(
                    "INSERT INTO notificaciones (usuario_id, tipo, mensaje, url) VALUES (?, 'seguidor', ?, ?)",
                    (objetivo_id,
                     f"{session['nombre']} comenzó a seguirte.",
                     url_for('social.ver_perfil_usuario', usuario_id=user_id)))
                conn.commit()
                socketio.emit('notificacion', {
                    'mensaje': f"{session['nombre']} comenzó a seguirte.",
                    'tipo': 'seguidor',
                    'url': url_for('social.ver_perfil_usuario', usuario_id=user_id)
                }, room=f'user_{objetivo_id}')
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM seguidores WHERE seguido_id = ?", (objetivo_id,)).fetchone()['n']
            return jsonify({'ok': True, 'siguiendo': True, 'total_seguidores': total})
        finally:
            conn.close()

    @blueprint.route('/dejar-seguir/<int:objetivo_id>', methods=['POST'])
    @login_required
    def dejar_seguir_usuario(objetivo_id):
        user_id = session['user_id']
        conn = get_db()
        try:
            conn.execute("DELETE FROM seguidores WHERE seguidor_id = ? AND seguido_id = ?",
                (user_id, objetivo_id))
            conn.commit()
            total = conn.execute(
                "SELECT COUNT(*) AS n FROM seguidores WHERE seguido_id = ?", (objetivo_id,)).fetchone()['n']
            return jsonify({'ok': True, 'siguiendo': False, 'total_seguidores': total})
        finally:
            conn.close()

    @blueprint.route('/perfil/<int:usuario_id>')
    @login_required
    def ver_perfil_usuario(usuario_id):
        viewer_id = session['user_id']
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE id = ? AND activo = 1", (usuario_id,))
        usuario = cur.fetchone()
        if not usuario:
            conn.close()
            flash('Usuario no encontrado.', 'error')
            return redirect(url_for('social.explorar'))
        cur.execute("SELECT COUNT(*) AS n FROM publicaciones WHERE autor_id = ? AND estado = 'publicado'", (usuario_id,))
        total_posts = cur.fetchone()['n']
        cur.execute("SELECT COUNT(*) AS n FROM seguidores WHERE seguido_id = ?", (usuario_id,))
        total_seguidores = cur.fetchone()['n']
        cur.execute("SELECT COUNT(*) AS n FROM seguidores WHERE seguidor_id = ?", (usuario_id,))
        total_siguiendo = cur.fetchone()['n']
        cur.execute("SELECT 1 FROM seguidores WHERE seguidor_id = ? AND seguido_id = ?", (viewer_id, usuario_id))
        ya_sigue = cur.fetchone() is not None
        cur.execute("""
            SELECT p.id, p.titulo, p.categoria, p.creado_en,
                   (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
                   (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
            FROM publicaciones p
            WHERE p.autor_id = ? AND p.estado = 'publicado'
            ORDER BY p.creado_en DESC LIMIT 10
        """, (usuario_id,))
        filas = cur.fetchall()
        conn.close()
        posts = []
        for f in filas:
            d = dict(f)
            d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
            posts.append(d)
        return render_template('social/perfil_usuario.html',
                               usuario=usuario,
                               stats={'total_posts': total_posts, 'total_seguidores': total_seguidores, 'total_siguiendo': total_siguiendo},
                               posts=posts, ya_sigue=ya_sigue,
                               es_propio=(viewer_id == usuario_id),
                               pagina_activa='perfil')

    @blueprint.route('/seguidores/<int:usuario_id>')
    @login_required
    def ver_seguidores(usuario_id):
        conn = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not usuario:
            conn.close()
            return redirect(url_for('social.explorar'))
        lista = conn.execute("""
            SELECT u.id, u.nombre, u.carrera, u.universidad, u.avatar_url, u.bio
            FROM seguidores s JOIN usuarios u ON u.id = s.seguidor_id
            WHERE s.seguido_id = ? ORDER BY s.creado_en DESC
        """, (usuario_id,)).fetchall()
        viewer_siguiendo = set(r['seguido_id'] for r in conn.execute(
            "SELECT seguido_id FROM seguidores WHERE seguidor_id = ?", (session['user_id'],)).fetchall())
        conn.close()
        return render_template('social/seguidores.html', usuario=usuario, lista=lista,
                               viewer_siguiendo=viewer_siguiendo, modo='seguidores', pagina_activa='perfil')

    @blueprint.route('/siguiendo/<int:usuario_id>')
    @login_required
    def ver_siguiendo(usuario_id):
        conn = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if not usuario:
            conn.close()
            return redirect(url_for('social.explorar'))
        lista = conn.execute("""
            SELECT u.id, u.nombre, u.carrera, u.universidad, u.avatar_url, u.bio
            FROM seguidores s JOIN usuarios u ON u.id = s.seguido_id
            WHERE s.seguidor_id = ? ORDER BY s.creado_en DESC
        """, (usuario_id,)).fetchall()
        viewer_siguiendo = set(r['seguido_id'] for r in conn.execute(
            "SELECT seguido_id FROM seguidores WHERE seguidor_id = ?", (session['user_id'],)).fetchall())
        conn.close()
        return render_template('social/seguidores.html', usuario=usuario, lista=lista,
                               viewer_siguiendo=viewer_siguiendo, modo='siguiendo', pagina_activa='perfil')

    @blueprint.route('/notificaciones')
    @login_required
    def notificaciones():
        conn = get_db()
        notifs = conn.execute(
            "SELECT * FROM notificaciones WHERE usuario_id = ? ORDER BY creado_en DESC LIMIT 50",
            (session['user_id'],)).fetchall()
        conn.execute("UPDATE notificaciones SET leida = 1 WHERE usuario_id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
        return render_template('social/notificaciones.html', notificaciones=notifs, pagina_activa='notificaciones')

    @blueprint.route('/notificaciones/no-leidas')
    @login_required
    def notificaciones_no_leidas():
        conn  = get_db()
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = ? AND leida = 0",
            (session['user_id'],)).fetchone()['n']
        conn.close()
        return jsonify({'total': total})

    return blueprint
