"""Reglas de dominio compartidas por la moderación."""


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
