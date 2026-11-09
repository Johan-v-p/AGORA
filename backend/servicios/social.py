"""Consultas de perfiles, exploración, seguimiento y notificaciones."""

from backend.nucleo.utilidades import con_tiempo_relativo

TIPOS_BUSQUEDA = ('todo', 'posts', 'personas', 'foros')

_SUBCONSULTAS_TOTALES = """
    (SELECT COUNT(*) FROM reacciones_publicacion r WHERE r.publicacion_id = p.id) AS total_reacciones,
    (SELECT COUNT(*) FROM comentarios c WHERE c.publicacion_id = p.id) AS total_comentarios
"""


def _contar(conn, consulta, parametros=()):
    return conn.execute(consulta, parametros).fetchone()['total']


def obtener_usuario(conn, usuario_id):
    return conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()


def obtener_usuario_activo(conn, usuario_id):
    return conn.execute(
        "SELECT * FROM usuarios WHERE id = ? AND activo = 1", (usuario_id,)
    ).fetchone()


def contar_publicaciones(conn, usuario_id):
    return _contar(
        conn,
        "SELECT COUNT(*) AS total FROM publicaciones WHERE autor_id = ? AND estado = 'publicado'",
        (usuario_id,),
    )


def estadisticas_propias(conn, usuario_id):
    """Devuelve los totales que se muestran en el perfil propio."""
    return {
        'total_posts': contar_publicaciones(conn, usuario_id),
        'total_reacciones': _contar(conn, """
            SELECT COUNT(*) AS total FROM reacciones_publicacion rp
            JOIN publicaciones p ON p.id = rp.publicacion_id
            WHERE p.autor_id = ?
        """, (usuario_id,)),
        'total_comentarios': _contar(conn, """
            SELECT COUNT(*) AS total FROM comentarios c
            JOIN publicaciones p ON p.id = c.publicacion_id
            WHERE p.autor_id = ?
        """, (usuario_id,)),
    }


def publicaciones_recientes(conn, usuario_id):
    filas = conn.execute(f"""
        SELECT
            p.id, p.titulo, p.categoria, p.creado_en,
            {_SUBCONSULTAS_TOTALES}
        FROM publicaciones p
        WHERE p.autor_id = ? AND p.estado = 'publicado'
        ORDER BY p.creado_en DESC
        LIMIT 10
    """, (usuario_id,)).fetchall()
    return con_tiempo_relativo(filas)


def buscar(conn, q, tipo):
    """Busca publicaciones, personas y foros. Devuelve (posts, personas, foros)."""
    termino = f'%{q}%'
    posts, personas, foros = [], [], []

    if tipo in ('todo', 'posts'):
        filas = conn.execute(f"""
            SELECT p.id, p.titulo, p.contenido, p.categoria, p.es_anonimo, p.creado_en,
                   u.nombre AS autor_nombre,
                   {_SUBCONSULTAS_TOTALES}
            FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
            WHERE p.estado = 'publicado' AND (p.titulo LIKE ? OR p.contenido LIKE ?)
            ORDER BY p.creado_en DESC LIMIT 20
        """, (termino, termino)).fetchall()
        posts = con_tiempo_relativo(filas)

    if tipo in ('todo', 'personas'):
        filas = conn.execute("""
            SELECT id, nombre, carrera, universidad FROM usuarios
            WHERE activo = 1 AND (nombre LIKE ? OR carrera LIKE ? OR universidad LIKE ?)
            ORDER BY nombre ASC LIMIT 20
        """, (termino, termino, termino)).fetchall()
        personas = [dict(r) for r in filas]

    if tipo in ('todo', 'foros'):
        filas = conn.execute("""
            SELECT f.id, f.nombre, f.descripcion, f.categoria,
                   (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
            FROM foros f WHERE f.nombre LIKE ? OR f.descripcion LIKE ?
            ORDER BY total_preguntas DESC LIMIT 20
        """, (termino, termino)).fetchall()
        foros = [dict(r) for r in filas]

    return posts, personas, foros


def destacados(conn, usuario_id):
    """Devuelve el contenido inicial de Explorar: (posts, personas, foros)."""
    filas = conn.execute(f"""
        SELECT p.id, p.titulo, p.categoria, p.es_anonimo, p.creado_en,
               u.nombre AS autor_nombre,
               {_SUBCONSULTAS_TOTALES}
        FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
        WHERE p.estado = 'publicado' ORDER BY p.creado_en DESC LIMIT 6
    """).fetchall()
    posts = con_tiempo_relativo(filas)

    foros = [dict(r) for r in conn.execute("""
        SELECT f.id, f.nombre, f.descripcion, f.categoria,
               (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
        FROM foros f ORDER BY total_preguntas DESC LIMIT 5
    """).fetchall()]

    personas = [dict(r) for r in conn.execute("""
        SELECT id, nombre, carrera, universidad FROM usuarios
        WHERE activo = 1 AND id != ? ORDER BY creado_en DESC LIMIT 6
    """, (usuario_id,)).fetchall()]

    return posts, personas, foros


def listar_tendencias(conn):
    return conn.execute("""
        SELECT p.id, p.titulo, p.categoria, p.creado_en,
               u.nombre AS autor,
               COUNT(DISTINCT r.usuario_id) AS total_reacciones,
               COUNT(DISTINCT c.id) AS total_comentarios
        FROM publicaciones p
        JOIN usuarios u ON u.id = p.autor_id
        LEFT JOIN reacciones_publicacion r ON r.publicacion_id = p.id
        LEFT JOIN comentarios c ON c.publicacion_id = p.id
        WHERE p.estado = 'publicado'
          AND p.creado_en >= datetime('now', '-7 days')
        GROUP BY p.id
        ORDER BY (COUNT(DISTINCT r.usuario_id) + COUNT(DISTINCT c.id)) DESC
        LIMIT 20
    """).fetchall()


def contar_seguidores(conn, usuario_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM seguidores WHERE seguido_id = ?", (usuario_id,)
    ).fetchone()['n']


def contar_siguiendo(conn, usuario_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM seguidores WHERE seguidor_id = ?", (usuario_id,)
    ).fetchone()['n']


def ya_sigue(conn, seguidor_id, seguido_id):
    return conn.execute(
        "SELECT 1 FROM seguidores WHERE seguidor_id = ? AND seguido_id = ?",
        (seguidor_id, seguido_id),
    ).fetchone() is not None


def seguir(conn, seguidor_id, seguido_id, mensaje, url):
    """Registra el seguimiento y su notificación."""
    conn.execute(
        "INSERT INTO seguidores (seguidor_id, seguido_id) VALUES (?, ?)",
        (seguidor_id, seguido_id),
    )
    conn.execute(
        "INSERT INTO notificaciones (usuario_id, tipo, mensaje, url) VALUES (?, 'seguidor', ?, ?)",
        (seguido_id, mensaje, url),
    )
    conn.commit()


def dejar_de_seguir(conn, seguidor_id, seguido_id):
    conn.execute(
        "DELETE FROM seguidores WHERE seguidor_id = ? AND seguido_id = ?",
        (seguidor_id, seguido_id),
    )
    conn.commit()


def listar_seguidores(conn, usuario_id):
    return conn.execute("""
        SELECT u.id, u.nombre, u.carrera, u.universidad, u.avatar_url, u.bio
        FROM seguidores s JOIN usuarios u ON u.id = s.seguidor_id
        WHERE s.seguido_id = ? ORDER BY s.creado_en DESC
    """, (usuario_id,)).fetchall()


def listar_siguiendo(conn, usuario_id):
    return conn.execute("""
        SELECT u.id, u.nombre, u.carrera, u.universidad, u.avatar_url, u.bio
        FROM seguidores s JOIN usuarios u ON u.id = s.seguido_id
        WHERE s.seguidor_id = ? ORDER BY s.creado_en DESC
    """, (usuario_id,)).fetchall()


def ids_seguidos(conn, usuario_id):
    filas = conn.execute(
        "SELECT seguido_id FROM seguidores WHERE seguidor_id = ?", (usuario_id,)
    ).fetchall()
    return set(r['seguido_id'] for r in filas)


def leer_notificaciones(conn, usuario_id):
    """Devuelve las últimas notificaciones y las marca como leídas."""
    notificaciones = conn.execute(
        "SELECT * FROM notificaciones WHERE usuario_id = ? ORDER BY creado_en DESC LIMIT 50",
        (usuario_id,),
    ).fetchall()
    conn.execute("UPDATE notificaciones SET leida = 1 WHERE usuario_id = ?", (usuario_id,))
    conn.commit()
    return notificaciones


def contar_notificaciones_no_leidas(conn, usuario_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = ? AND leida = 0",
        (usuario_id,),
    ).fetchone()['n']
