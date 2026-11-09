"""Consultas y reglas de las cuentas de usuario."""

from werkzeug.security import check_password_hash, generate_password_hash


def obtener_por_id(conn, usuario_id):
    return conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()


def obtener_por_correo(conn, correo):
    return conn.execute("SELECT * FROM usuarios WHERE correo = ?", (correo,)).fetchone()


def obtener_estado(conn, usuario_id):
    """Devuelve el estado actual (activo, rol) de una cuenta, o None si no existe."""
    return conn.execute(
        "SELECT activo, rol FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()


def obtener_rol(conn, usuario_id):
    return conn.execute("SELECT rol FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()


def verificar_password(usuario, password):
    return check_password_hash(usuario['password'], password)


def registrar(conn, nombre, correo, carrera, universidad, password):
    conn.execute(
        """INSERT INTO usuarios
           (nombre, correo, password, carrera, universidad, rol)
           VALUES (?, ?, ?, ?, ?, 'estudiante')""",
        (nombre, correo, generate_password_hash(password), carrera, universidad),
    )
    conn.commit()


def actualizar_perfil(conn, usuario_id, nombre, bio, carrera, universidad, avatar_url):
    conn.execute(
        "UPDATE usuarios SET nombre=?, bio=?, carrera=?, universidad=?, avatar_url=? WHERE id=?",
        (nombre, bio, carrera, universidad, avatar_url, usuario_id),
    )
    conn.commit()


def correo_en_uso(conn, correo, usuario_id):
    """Indica si otro usuario ya tiene ese correo."""
    return conn.execute(
        "SELECT id FROM usuarios WHERE correo = ? AND id != ?", (correo, usuario_id)
    ).fetchone() is not None


def actualizar_correo(conn, usuario_id, correo):
    conn.execute("UPDATE usuarios SET correo = ? WHERE id = ?", (correo, usuario_id))
    conn.commit()


def actualizar_password(conn, usuario_id, password):
    conn.execute(
        "UPDATE usuarios SET password = ? WHERE id = ?",
        (generate_password_hash(password), usuario_id),
    )
    conn.commit()
