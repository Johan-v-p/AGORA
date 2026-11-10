"""Consultas y reglas del portafolio de proyectos."""

import json

from backend.nucleo.utilidades import parsear_tecnologias

ESTADOS = ('en_desarrollo', 'completado', 'pausado')


def _con_tecnologias(filas):
    proyectos = []
    for fila in filas:
        proyecto = dict(fila)
        proyecto['tecnologias_lista'] = parsear_tecnologias(proyecto.get('tecnologias'))
        proyectos.append(proyecto)
    return proyectos


def listar_propios(conn, usuario_id):
    filas = conn.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
               (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
        FROM proyectos p
        WHERE p.autor_id = ?
        ORDER BY p.destacado DESC, p.creado_en DESC
    """, (usuario_id, usuario_id)).fetchall()
    return _con_tecnologias(filas)


def listar_comunidad(conn, usuario_id):
    """Devuelve los proyectos de otros usuarios, primero los más aplaudidos."""
    filas = conn.execute("""
        SELECT p.*, u.nombre AS autor_nombre,
               (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
               (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
        FROM proyectos p JOIN usuarios u ON u.id = p.autor_id
        WHERE p.autor_id != ?
        ORDER BY total_aplausos DESC, p.creado_en DESC
        LIMIT 20
    """, (usuario_id, usuario_id)).fetchall()
    return _con_tecnologias(filas)


def serializar_tecnologias(texto):
    """Convierte "Flask, Python" en el JSON que se almacena, o None si está vacío."""
    lista = [t.strip() for t in texto.split(',') if t.strip()]
    return json.dumps(lista, ensure_ascii=False) if lista else None


def crear(conn, autor_id, titulo, descripcion, tecnologias, materia, estado, repo_url, demo_url,
          imagen_url=None):
    conn.execute("""
        INSERT INTO proyectos (autor_id, titulo, descripcion, tecnologias, materia, estado,
                               repo_url, demo_url, imagen_url)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (autor_id, titulo, descripcion, tecnologias, materia, estado, repo_url, demo_url,
          imagen_url))
    conn.commit()


def alternar_aplauso(conn, proyecto_id, usuario_id):
    """Pone o quita el aplauso del usuario. Devuelve (activo, total)."""
    ya_aplaudio = conn.execute(
        "SELECT 1 FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?",
        (proyecto_id, usuario_id),
    ).fetchone()
    if ya_aplaudio:
        conn.execute(
            "DELETE FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?",
            (proyecto_id, usuario_id),
        )
        activo = False
    else:
        conn.execute(
            "INSERT INTO aplausos_proyecto (proyecto_id, usuario_id) VALUES (?,?)",
            (proyecto_id, usuario_id),
        )
        activo = True
    conn.commit()
    total = conn.execute(
        "SELECT COUNT(*) AS total FROM aplausos_proyecto WHERE proyecto_id = ?", (proyecto_id,)
    ).fetchone()['total']
    return activo, total
