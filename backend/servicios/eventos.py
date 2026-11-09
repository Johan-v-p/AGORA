"""Consultas y reglas de eventos e inscripciones."""

from backend.nucleo.utilidades import procesar_evento

CATEGORIAS = ('academico', 'cultural', 'deportivo', 'bienestar')


def listar_proximos(conn, usuario_id, categoria):
    """Devuelve los eventos futuros, opcionalmente de una categoría."""
    where = ""
    parametros = [usuario_id]
    if categoria in CATEGORIAS:
        where = "AND e.categoria = ?"
        parametros.append(categoria)

    filas = conn.execute(f"""
        SELECT e.*,
               (SELECT 1 FROM inscripciones_evento i
                WHERE i.evento_id = e.id AND i.usuario_id = ?) AS inscrito,
               CASE WHEN e.cupos IS NULL THEN NULL
                    ELSE e.cupos - (SELECT COUNT(*) FROM inscripciones_evento i2 WHERE i2.evento_id = e.id)
               END AS cupos_libres
        FROM eventos e
        WHERE e.fecha >= date('now') {where}
        ORDER BY e.fecha ASC, e.hora_inicio ASC
    """, parametros).fetchall()
    return [procesar_evento(fila) for fila in filas]


def crear(conn, creador_id, titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, cupos, organizador):
    conn.execute("""
        INSERT INTO eventos (creador_id, titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, cupos, organizador)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (creador_id, titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, cupos, organizador))
    conn.commit()


def obtener_cupos(conn, evento_id):
    return conn.execute("SELECT cupos FROM eventos WHERE id = ?", (evento_id,)).fetchone()


def _contar_inscritos(conn, evento_id):
    return conn.execute(
        "SELECT COUNT(*) AS n FROM inscripciones_evento WHERE evento_id = ?", (evento_id,)
    ).fetchone()['n']


def alternar_inscripcion(conn, evento_id, usuario_id, cupos):
    """Inscribe o cancela al usuario. Devuelve si quedó inscrito, o None si no hay cupos."""
    inscrito = conn.execute(
        "SELECT 1 FROM inscripciones_evento WHERE evento_id = ? AND usuario_id = ?",
        (evento_id, usuario_id),
    ).fetchone()
    if inscrito:
        conn.execute(
            "DELETE FROM inscripciones_evento WHERE evento_id = ? AND usuario_id = ?",
            (evento_id, usuario_id),
        )
        resultado = False
    else:
        if cupos is not None and _contar_inscritos(conn, evento_id) >= cupos:
            return None
        conn.execute(
            "INSERT INTO inscripciones_evento (evento_id, usuario_id) VALUES (?,?)",
            (evento_id, usuario_id),
        )
        resultado = True
    conn.commit()
    return resultado


def calcular_cupos_libres(conn, evento_id, cupos):
    if cupos is None:
        return None
    return cupos - _contar_inscritos(conn, evento_id)


def obtener_detalle(conn, evento_id, usuario_id):
    """Devuelve un evento procesado con la inscripción del usuario, o None."""
    fila = conn.execute("""
        SELECT e.*,
               (SELECT 1 FROM inscripciones_evento i
                WHERE i.evento_id = e.id AND i.usuario_id = ?) AS inscrito,
               CASE WHEN e.cupos IS NULL THEN NULL
                    ELSE e.cupos - (SELECT COUNT(*) FROM inscripciones_evento i2
                                   WHERE i2.evento_id = e.id)
               END AS cupos_libres
        FROM eventos e WHERE e.id = ?
    """, (usuario_id, evento_id)).fetchone()
    return procesar_evento(fila) if fila else None


def listar_participantes_resumen(conn, evento_id):
    return conn.execute("""
        SELECT u.id, u.nombre, u.avatar_url
        FROM inscripciones_evento ie
        JOIN usuarios u ON u.id = ie.usuario_id
        WHERE ie.evento_id = ?
        ORDER BY ie.creado_en ASC
    """, (evento_id,)).fetchall()


def listar_participantes(conn, evento_id):
    return conn.execute("""
        SELECT u.id, u.nombre, u.avatar_url, u.carrera, u.universidad,
               ie.creado_en
        FROM inscripciones_evento ie
        JOIN usuarios u ON u.id = ie.usuario_id
        WHERE ie.evento_id = ?
        ORDER BY ie.creado_en ASC
    """, (evento_id,)).fetchall()


def obtener(conn, evento_id):
    return conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()


def actualizar(conn, evento_id, titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, organizador, cupos):
    conn.execute("""
        UPDATE eventos
        SET titulo=?, descripcion=?, categoria=?, fecha=?,
            hora_inicio=?, hora_fin=?, lugar=?, organizador=?, cupos=?
        WHERE id=?
    """, (titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, organizador, cupos, evento_id))
    conn.commit()


def eliminar(conn, evento_id):
    """Elimina el evento y sus inscripciones."""
    conn.execute("DELETE FROM inscripciones_evento WHERE evento_id = ?", (evento_id,))
    conn.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
    conn.commit()
