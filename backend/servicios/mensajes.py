"""Consultas de conversaciones y mensajes privados."""


def contar_no_leidos(conn, usuario_id):
    return conn.execute("""
        SELECT COUNT(*) FROM mensajes m
        JOIN participantes_conversacion pc ON pc.conversacion_id = m.conversacion_id
            AND pc.usuario_id = ?
        WHERE m.autor_id != ? AND m.leido = 0
    """, (usuario_id, usuario_id)).fetchone()[0]


def listar_conversaciones(conn, usuario_id):
    """Devuelve las conversaciones activas con su último texto y mensajes no leídos."""
    return conn.execute("""
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
    """, {'me': usuario_id}).fetchall()


def obtener_destinatario(conn, usuario_id):
    return conn.execute(
        "SELECT id, nombre, carrera FROM usuarios WHERE id = ? AND activo = 1", (usuario_id,)
    ).fetchone()


def obtener_o_crear_conversacion(conn, usuario_id, otro_id):
    """Devuelve el id de la conversación entre dos usuarios, creándola si no existe."""
    conversacion = conn.execute("""
        SELECT c.id FROM conversaciones c
        JOIN participantes_conversacion p1 ON p1.conversacion_id = c.id AND p1.usuario_id = ?
        JOIN participantes_conversacion p2 ON p2.conversacion_id = c.id AND p2.usuario_id = ?
        LIMIT 1
    """, (usuario_id, otro_id)).fetchone()
    if conversacion:
        return conversacion['id']

    conversacion_id = conn.execute("INSERT INTO conversaciones DEFAULT VALUES").lastrowid
    for participante in (usuario_id, otro_id):
        conn.execute(
            "INSERT INTO participantes_conversacion (conversacion_id, usuario_id) VALUES (?,?)",
            (conversacion_id, participante),
        )
    conn.commit()
    return conversacion_id


def marcar_leidos(conn, conversacion_id, usuario_id):
    conn.execute("""
        UPDATE mensajes SET leido = 1
        WHERE conversacion_id = ? AND autor_id != ? AND leido = 0
    """, (conversacion_id, usuario_id))
    conn.commit()


def listar_mensajes(conn, conversacion_id):
    return conn.execute("""
        SELECT m.id, m.autor_id, m.contenido, m.leido, m.creado_en,
               u.nombre AS autor_nombre
        FROM mensajes m
        JOIN usuarios u ON u.id = m.autor_id
        WHERE m.conversacion_id = ?
        ORDER BY m.creado_en ASC
    """, (conversacion_id,)).fetchall()


def participa(conn, conversacion_id, usuario_id):
    return conn.execute("""
        SELECT 1 FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conversacion_id, usuario_id)).fetchone() is not None


def obtener_otro_participante(conn, conversacion_id, usuario_id):
    return conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conversacion_id, usuario_id)).fetchone()


def guardar_mensaje(conn, conversacion_id, autor_id, contenido):
    """Guarda el mensaje. Devuelve (id del mensaje, hora, otro participante)."""
    mensaje_id = conn.execute("""
        INSERT INTO mensajes (conversacion_id, autor_id, contenido)
        VALUES (?, ?, ?)
    """, (conversacion_id, autor_id, contenido)).lastrowid

    conn.execute(
        "UPDATE conversaciones SET ultimo_msg = CURRENT_TIMESTAMP WHERE id = ?",
        (conversacion_id,),
    )
    otro = obtener_otro_participante(conn, conversacion_id, autor_id)
    fila = conn.execute("SELECT creado_en FROM mensajes WHERE id = ?", (mensaje_id,)).fetchone()
    hora = fila['creado_en'][11:16] if fila else ''
    conn.commit()
    return mensaje_id, hora, otro


def archivar(conn, conversacion_id, usuario_id):
    """Oculta la conversación de la lista del usuario sin borrarla."""
    conn.execute("""
        UPDATE participantes_conversacion
        SET archivada = 1
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conversacion_id, usuario_id))
    conn.commit()
