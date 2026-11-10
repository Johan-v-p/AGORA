"""Reglas de dominio compartidas por la moderación."""


TIPOS_REPORTE = ('publicacion', 'comentario', 'usuario')
ACCIONES_REPORTE = ('ignorar', 'eliminar', 'suspender')
# Valores que ofrecen los formularios de reportar_*.html.
MOTIVOS_REPORTE = (
    'spam', 'acoso', 'contenido_inapropiado', 'desinformacion', 'plagio', 'suplantacion', 'otro',
)
ROLES = ('estudiante', 'moderador', 'admin')
CATEGORIAS_FORO = ('campus', 'matematicas', 'sistemas', 'academico', 'otro')
ESTADOS_ABIERTOS = ('enviado', 'en_revision')
SQL_REPORTE_ABIERTO = "estado IN ('enviado', 'en_revision')"

CONSULTAS_USUARIO_REPORTADO = {
    'usuario': "SELECT id, rol FROM usuarios WHERE id = ?",
    'publicacion': """SELECT u.id, u.rol FROM publicaciones p
                      JOIN usuarios u ON u.id = p.autor_id WHERE p.id = ?""",
    'comentario': """SELECT u.id, u.rol FROM comentarios c
                      JOIN usuarios u ON u.id = c.autor_id WHERE c.id = ?""",
}


def obtener_usuario_reportado(conn, tipo, referencia_id):
    """Devuelve el responsable del reporte, o None si ya no existe."""
    consulta = CONSULTAS_USUARIO_REPORTADO.get(tipo)
    if not consulta:
        return None
    return conn.execute(consulta, (referencia_id,)).fetchone()


def motivo_para_no_suspender(objetivo, usuario_id, rol):
    """Explica por qué el usuario actual no puede suspender al objetivo."""
    if not objetivo:
        return 'El contenido reportado ya no existe; no se puede identificar a su autor.'
    if objetivo['id'] == usuario_id:
        return 'No puedes suspender tu propia cuenta.'
    if rol != 'admin' and objetivo['rol'] in ('admin', 'moderador'):
        return (
            'Solo un administrador puede suspender a un moderador, y un '
            'moderador no puede suspender a un administrador.'
        )
    return None


def listar_reportes_abiertos(conn):
    return conn.execute(f"""
        SELECT r.id, r.tipo, r.motivo, r.creado_en, r.estado,
               u.nombre AS reportador,
               r.referencia_id AS contenido_id
        FROM reportes r
        JOIN usuarios u ON u.id = r.reportado_por
        WHERE r.{SQL_REPORTE_ABIERTO}
        ORDER BY r.creado_en DESC
        LIMIT 50
    """).fetchall()


def contar_reportes_abiertos(conn):
    return conn.execute(
        f"SELECT COUNT(*) AS n FROM reportes WHERE {SQL_REPORTE_ABIERTO}"
    ).fetchone()['n']


def contar_reportes_resueltos(conn):
    return conn.execute("SELECT COUNT(*) AS n FROM reportes WHERE estado = 'resuelto'").fetchone()['n']


def contar_usuarios_activos(conn):
    return conn.execute("SELECT COUNT(*) AS n FROM usuarios WHERE activo = 1").fetchone()['n']


def existe_reporte_abierto(conn, usuario_id, tipo, referencia_id):
    return conn.execute(
        f"SELECT 1 FROM reportes WHERE reportado_por = ? AND tipo = ? AND referencia_id = ? AND {SQL_REPORTE_ABIERTO}",
        (usuario_id, tipo, referencia_id),
    ).fetchone() is not None


def crear_reporte(conn, usuario_id, tipo, referencia_id, motivo, descripcion=None):
    conn.execute(
        """INSERT INTO reportes (reportado_por, tipo, referencia_id, motivo, descripcion)
           VALUES (?, ?, ?, ?, ?)""",
        (usuario_id, tipo, referencia_id, motivo, descripcion),
    )
    conn.commit()


def obtener_publicacion_a_reportar(conn, post_id):
    """Devuelve la publicación visible que se va a reportar, sin delatar a autores anónimos."""
    return conn.execute("""
        SELECT p.id, p.titulo, p.autor_id,
               CASE WHEN p.es_anonimo THEN NULL ELSE u.nombre END AS nombre_autor
        FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
        WHERE p.id = ? AND p.estado = 'publicado'
    """, (post_id,)).fetchone()


def obtener_comentario_a_reportar(conn, comentario_id):
    return conn.execute("""
        SELECT c.id, c.contenido, c.autor_id, u.nombre AS nombre_autor
        FROM comentarios c JOIN usuarios u ON u.id = c.autor_id
        WHERE c.id = ?
    """, (comentario_id,)).fetchone()


def obtener_usuario_a_reportar(conn, usuario_id):
    return conn.execute(
        "SELECT id, nombre, carrera FROM usuarios WHERE id = ? AND activo = 1", (usuario_id,)
    ).fetchone()


def obtener_reporte(conn, reporte_id):
    return conn.execute("SELECT * FROM reportes WHERE id = ?", (reporte_id,)).fetchone()


def eliminar_contenido_reportado(conn, reporte):
    """Retira la publicación o el comentario señalado por el reporte."""
    if reporte['tipo'] == 'publicacion':
        conn.execute("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", (reporte['referencia_id'],))
    elif reporte['tipo'] == 'comentario':
        conn.execute("DELETE FROM comentarios WHERE id = ?", (reporte['referencia_id'],))


def suspender_usuario(conn, usuario_id):
    conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (usuario_id,))


def cerrar_reporte(conn, reporte_id, revisor_id):
    """Marca el reporte como resuelto y confirma los cambios de la moderación."""
    conn.execute(
        "UPDATE reportes SET estado = 'resuelto', revisado_por = ? WHERE id = ?",
        (revisor_id, reporte_id),
    )
    conn.commit()


def listar_reportes_de_usuario(conn, usuario_id):
    return conn.execute(
        "SELECT * FROM reportes WHERE reportado_por = ? ORDER BY creado_en DESC",
        (usuario_id,),
    ).fetchall()


def totales_panel(conn):
    """Devuelve los contadores del panel de administración."""
    return {
        'total_usuarios': contar_usuarios_activos(conn),
        'total_posts': conn.execute(
            "SELECT COUNT(*) AS n FROM publicaciones WHERE estado = 'publicado'"
        ).fetchone()['n'],
        'total_reportes': contar_reportes_abiertos(conn),
        'total_eventos': conn.execute(
            "SELECT COUNT(*) AS n FROM eventos WHERE fecha >= date('now')"
        ).fetchone()['n'],
    }


# ── Gestión de usuarios (administración) ──

def listar_usuarios(conn, q=''):
    """Lista las cuentas, filtrando por nombre o correo cuando hay búsqueda."""
    if q:
        patron = f'%{q}%'
        return conn.execute("""
            SELECT id, nombre, correo, rol, activo, creado_en FROM usuarios
            WHERE nombre LIKE ? OR correo LIKE ?
            ORDER BY creado_en DESC, id DESC
        """, (patron, patron)).fetchall()
    return conn.execute("""
        SELECT id, nombre, correo, rol, activo, creado_en FROM usuarios
        ORDER BY creado_en DESC, id DESC
    """).fetchall()


def cambiar_rol(conn, usuario_id, rol):
    conn.execute("UPDATE usuarios SET rol = ? WHERE id = ?", (rol, usuario_id))
    conn.commit()


def alternar_activo(conn, usuario_id):
    """Suspende una cuenta activa o reactiva una suspendida. Devuelve el nuevo estado."""
    conn.execute(
        "UPDATE usuarios SET activo = CASE WHEN activo = 1 THEN 0 ELSE 1 END WHERE id = ?",
        (usuario_id,),
    )
    conn.commit()
    return conn.execute("SELECT activo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()['activo']


# ── Gestión de foros (administración) ──

def listar_foros_admin(conn):
    return conn.execute("""
        SELECT f.id, f.nombre, f.categoria,
               (SELECT COUNT(*) FROM preguntas_foro p WHERE p.foro_id = f.id) AS total_preguntas
        FROM foros f
        ORDER BY f.nombre
    """).fetchall()


def existe_foro_con_nombre(conn, nombre):
    return conn.execute(
        "SELECT 1 FROM foros WHERE nombre = ? COLLATE NOCASE", (nombre,)
    ).fetchone() is not None


def crear_foro(conn, nombre, descripcion, categoria, creado_por):
    conn.execute(
        "INSERT INTO foros (nombre, descripcion, categoria, creado_por) VALUES (?, ?, ?, ?)",
        (nombre, descripcion, categoria, creado_por),
    )
    conn.commit()


def eliminar_foro(conn, foro_id):
    """Borra el foro con sus preguntas, respuestas y votos. Devuelve False si no existía."""
    if not conn.execute("SELECT 1 FROM foros WHERE id = ?", (foro_id,)).fetchone():
        return False
    # Se borra en cascada a mano: SQLite solo aplica ON DELETE CASCADE con PRAGMA foreign_keys.
    conn.execute("""
        DELETE FROM votos_respuesta WHERE respuesta_id IN (
            SELECT r.id FROM respuestas_foro r
            JOIN preguntas_foro p ON p.id = r.pregunta_id WHERE p.foro_id = ?)
    """, (foro_id,))
    conn.execute("""
        DELETE FROM respuestas_foro WHERE pregunta_id IN (
            SELECT id FROM preguntas_foro WHERE foro_id = ?)
    """, (foro_id,))
    conn.execute("DELETE FROM preguntas_foro WHERE foro_id = ?", (foro_id,))
    conn.execute("DELETE FROM foros WHERE id = ?", (foro_id,))
    conn.commit()
    return True


# ── Estadísticas (administración) ──

def estadisticas(conn):
    """Devuelve los datos de la página de estadísticas."""
    posts_cat = conn.execute("""
        SELECT categoria, COUNT(*) AS n FROM publicaciones
        WHERE estado = 'publicado'
        GROUP BY categoria ORDER BY n DESC
    """).fetchall()
    top_usuarios = conn.execute("""
        SELECT u.nombre, COUNT(*) AS n
        FROM publicaciones p JOIN usuarios u ON u.id = p.autor_id
        WHERE p.estado = 'publicado'
        GROUP BY u.id ORDER BY n DESC LIMIT 5
    """).fetchall()
    usuarios_dia = conn.execute("""
        SELECT date(creado_en) AS dia, COUNT(*) AS n FROM usuarios
        WHERE creado_en >= date('now', '-6 days')
        GROUP BY dia ORDER BY dia
    """).fetchall()
    return {'posts_cat': posts_cat, 'top_usuarios': top_usuarios, 'usuarios_dia': usuarios_dia}
