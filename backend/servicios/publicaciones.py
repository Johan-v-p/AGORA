"""Consultas y reglas de las publicaciones, comentarios y reacciones."""

from backend.nucleo.utilidades import con_tiempo_relativo, tiempo_relativo

CATEGORIAS = ('general', 'academico', 'foro', 'meme', 'portafolio')
FILTROS_FEED = ('academico', 'meme', 'foro', 'portafolio', 'general')

_CONSULTA_FEED = """
    SELECT
        p.id,
        p.autor_id,
        p.titulo,
        p.contenido,
        p.imagen_url,
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


def listar_feed(conn, filtro):
    """Devuelve las publicaciones del feed, opcionalmente de una categoría."""
    if filtro in FILTROS_FEED:
        filas = conn.execute(
            _CONSULTA_FEED + " AND p.categoria = ? ORDER BY p.creado_en DESC",
            (filtro,),
        ).fetchall()
    else:
        filas = conn.execute(_CONSULTA_FEED + " ORDER BY p.creado_en DESC").fetchall()
    return con_tiempo_relativo(filas)


def crear(conn, autor_id, titulo, contenido, categoria, es_anonimo, imagen_url=None):
    conn.execute(
        """INSERT INTO publicaciones
               (autor_id, titulo, contenido, categoria, es_anonimo, imagen_url, estado)
           VALUES (?, ?, ?, ?, ?, ?, 'publicado')""",
        (autor_id, titulo, contenido, categoria, es_anonimo, imagen_url),
    )
    conn.commit()


def obtener_detalle(conn, post_id):
    """Devuelve una publicación visible con sus totales, o None si no existe."""
    fila = conn.execute("""
        SELECT
            p.id, p.autor_id, p.titulo, p.contenido, p.categoria, p.imagen_url,
            p.es_anonimo, p.creado_en,
            u.nombre AS autor_nombre,
            (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
            (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
        FROM publicaciones p
        JOIN usuarios u ON u.id = p.autor_id
        WHERE p.id = ? AND p.estado = 'publicado'
    """, (post_id,)).fetchone()
    if not fila:
        return None
    post = dict(fila)
    post['tiempo_relativo'] = tiempo_relativo(post['creado_en'])
    return post


def listar_comentarios(conn, post_id):
    filas = conn.execute("""
        SELECT c.id, c.contenido, c.creado_en, 0 AS es_anonimo, u.nombre AS autor_nombre
        FROM comentarios c
        JOIN usuarios u ON u.id = c.autor_id
        WHERE c.publicacion_id = ?
        ORDER BY c.creado_en ASC
    """, (post_id,)).fetchall()
    return con_tiempo_relativo(filas)


def ya_reacciono(conn, post_id, usuario_id):
    return conn.execute(
        "SELECT 1 FROM reacciones_publicacion WHERE publicacion_id = ? AND usuario_id = ?",
        (post_id, usuario_id),
    ).fetchone() is not None


def esta_publicada(conn, post_id):
    return conn.execute(
        "SELECT id FROM publicaciones WHERE id = ? AND estado = 'publicado'", (post_id,)
    ).fetchone() is not None


def comentar(conn, post_id, autor_id, contenido):
    conn.execute(
        "INSERT INTO comentarios (publicacion_id, autor_id, contenido) VALUES (?, ?, ?)",
        (post_id, autor_id, contenido),
    )
    conn.commit()


def alternar_reaccion(conn, post_id, usuario_id):
    """Pone o quita la reacción del usuario. Devuelve (activa, total)."""
    if ya_reacciono(conn, post_id, usuario_id):
        conn.execute(
            "DELETE FROM reacciones_publicacion WHERE publicacion_id = ? AND usuario_id = ?",
            (post_id, usuario_id),
        )
        activa = False
    else:
        conn.execute(
            "INSERT INTO reacciones_publicacion (publicacion_id, usuario_id, tipo) VALUES (?, ?, 'aplauso')",
            (post_id, usuario_id),
        )
        activa = True
    conn.commit()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM reacciones_publicacion WHERE publicacion_id = ?",
        (post_id,),
    ).fetchone()['total']
    return activa, total


def obtener_propia(conn, post_id, autor_id):
    """Devuelve una publicación visible si pertenece al autor indicado."""
    return conn.execute(
        "SELECT * FROM publicaciones WHERE id = ? AND autor_id = ? AND estado = 'publicado'",
        (post_id, autor_id),
    ).fetchone()


def actualizar(conn, post_id, titulo, contenido, categoria):
    conn.execute(
        "UPDATE publicaciones SET titulo = ?, contenido = ?, categoria = ? WHERE id = ?",
        (titulo, contenido, categoria, post_id),
    )
    conn.commit()


def actualizar_imagen(conn, post_id, imagen_url):
    """Cambia o quita (None) la imagen de una publicación."""
    conn.execute("UPDATE publicaciones SET imagen_url = ? WHERE id = ?", (imagen_url, post_id))
    conn.commit()


def marcar_eliminada(conn, post_id):
    conn.execute("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", (post_id,))
    conn.commit()
