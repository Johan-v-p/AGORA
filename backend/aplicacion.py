"""
app.py — Servidor principal de ÁGORA
Corre en LAN: python app.py  →  http://0.0.0.0:5000
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, join_room, leave_room
from datetime import datetime
import json
import sqlite3
import sys
from werkzeug.security import check_password_hash, generate_password_hash
from backend.nucleo.base_datos import abrir_conexion
from backend.nucleo.configuracion import obtener_configuracion
from backend.nucleo.utilidades import (
    parsear_tecnologias,
    procesar_evento,
    tiempo_relativo,
)
from backend.servicios.moderacion import (
    ACCIONES_REPORTE,
    ESTADOS_ABIERTOS,
    SQL_REPORTE_ABIERTO,
    TIPOS_REPORTE,
    obtener_usuario_reportado as resolver_usuario_reportado,
    motivo_para_no_suspender as evaluar_suspension,
)
from backend.rutas.autenticacion import crear_blueprint as crear_blueprint_autenticacion
from backend.rutas.publicaciones import crear_blueprint as crear_blueprint_publicaciones
from backend.rutas.decoradores import crear_moderador_required, login_required

# ── FIX: Python 3.14 redujo el límite de recursión por defecto.
# Jinja2 usa recursión interna al procesar extends + include anidados.
sys.setrecursionlimit(5000)

app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static',
)
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins='*')
CONFIGURACION = obtener_configuracion()
app.config['SECRET_KEY'] = CONFIGURACION['SECRET_KEY']

DB = CONFIGURACION['DATABASE_PATH']

# ──────────────────────────────────────────
# UTILIDADES
# ──────────────────────────────────────────
def get_db():
    """Abre una conexión SQLite y devuelve filas como diccionarios."""
    return abrir_conexion(DB)


app.register_blueprint(crear_blueprint_autenticacion(get_db))
app.register_blueprint(crear_blueprint_publicaciones(get_db))
moderador_required = crear_moderador_required(get_db)


def obtener_cuenta(user_id):
    """Devuelve el estado actual (activo, rol) de una cuenta, o None si no existe."""
    conn = get_db()
    cuenta = conn.execute("SELECT activo, rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return cuenta


@app.before_request
def validar_sesion():
    """Expulsa las sesiones de cuentas suspendidas o borradas y mantiene el rol al día."""
    user_id = session.get('user_id')
    if not user_id or request.endpoint == 'static':
        return None

    cuenta = obtener_cuenta(user_id)
    if not cuenta or not cuenta['activo']:
        session.clear()
        flash('Tu cuenta está suspendida. Contacta a un administrador.', 'error')
        return redirect(url_for('autenticacion.login'))

    session['rol'] = cuenta['rol']
    return None




# ══════════════════════════════════════════
# RUTAS PÚBLICAS
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# FEED
# ══════════════════════════════════════════



# ── NUEVA PUBLICACIÓN ───────────────────────


# ── POST DETALLE ────────────────────────────


# ── COMENTAR ────────────────────────────────


# ── REACCIONAR (AJAX) ────────────────────────


# ── EDITAR PUBLICACIÓN ─────────────────────


# ── ELIMINAR PUBLICACIÓN ──────────────────


# ══════════════════════════════════════════
# PERFIL
# ══════════════════════════════════════════

@app.route('/perfil')
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


# ══════════════════════════════════════════
# EXPLORAR
# ══════════════════════════════════════════

@app.route('/explorar')
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


# ══════════════════════════════════════════
# FOROS
# ══════════════════════════════════════════

@app.route('/foros')
@login_required
def foros():
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("""
        SELECT f.id, f.nombre, f.descripcion, f.categoria,
               (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
        FROM foros f ORDER BY total_preguntas DESC
    """)
    foros_lista = [dict(r) for r in cur.fetchall()]
    conn.close()
    return render_template('foros/lista.html', foros=foros_lista)


@app.route('/foros/<int:foro_id>')
@login_required
def foro_detalle(foro_id):
    conn = get_db()
    cur  = conn.cursor()

    cur.execute("SELECT * FROM foros WHERE id = ?", (foro_id,))
    foro = cur.fetchone()
    if not foro:
        conn.close()
        flash('Foro no encontrado.', 'error')
        return redirect(url_for('foros'))

    cur.execute("""
        SELECT pf.id, pf.titulo, pf.contenido, pf.tipo, pf.es_anonimo, pf.creado_en,
               u.nombre AS autor_nombre,
               (SELECT COUNT(*) FROM respuestas_foro rf WHERE rf.pregunta_id = pf.id) AS total_respuestas
        FROM preguntas_foro pf
        JOIN usuarios u ON u.id = pf.autor_id
        WHERE pf.foro_id = ? ORDER BY pf.creado_en DESC
    """, (foro_id,))
    filas = cur.fetchall()
    conn.close()

    preguntas = []
    for fila in filas:
        d = dict(fila); d['tiempo_relativo'] = tiempo_relativo(d['creado_en']); preguntas.append(d)

    return render_template('foros/detalle.html', foro=dict(foro), preguntas=preguntas)


@app.route('/foros/<int:foro_id>/nueva', methods=['POST'])
@login_required
def foro_nueva_pregunta(foro_id):
    titulo    = request.form.get('titulo', '').strip()
    contenido = request.form.get('contenido', '').strip()
    tipo      = request.form.get('tipo', 'pregunta').strip()
    es_anonimo = 1 if request.form.get('es_anonimo') else 0

    if not titulo:
        flash('El título es obligatorio.', 'error')
        return redirect(url_for('foro_detalle', foro_id=foro_id))

    if tipo not in ('pregunta', 'duda', 'apuntes', 'recurso', 'debate'):
        tipo = 'pregunta'

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO preguntas_foro (foro_id, autor_id, titulo, contenido, tipo, es_anonimo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (foro_id, session['user_id'], titulo, contenido, tipo, es_anonimo))
        conn.commit()
        flash('Pregunta publicada.', 'success')
    except Exception as e:
        flash(f'Error al publicar: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('foro_detalle', foro_id=foro_id))


# ── FORO PREGUNTA DETALLE ── ★ NUEVO ────────
@app.route('/foros/<int:foro_id>/pregunta/<int:pregunta_id>')
@login_required
def foro_pregunta(foro_id, pregunta_id):
    conn = get_db()
    cur  = conn.cursor()

    # Datos del foro
    cur.execute("SELECT * FROM foros WHERE id = ?", (foro_id,))
    foro = cur.fetchone()
    if not foro:
        conn.close()
        flash('Foro no encontrado.', 'error')
        return redirect(url_for('foros'))

    # Datos de la pregunta
    cur.execute("""
        SELECT pf.*, u.nombre AS autor_nombre
        FROM preguntas_foro pf
        JOIN usuarios u ON u.id = pf.autor_id
        WHERE pf.id = ? AND pf.foro_id = ?
    """, (pregunta_id, foro_id))
    pregunta = cur.fetchone()
    if not pregunta:
        conn.close()
        flash('Pregunta no encontrada.', 'error')
        return redirect(url_for('foro_detalle', foro_id=foro_id))

    pregunta = dict(pregunta)
    pregunta['tiempo_relativo'] = tiempo_relativo(pregunta['creado_en'])

    # Respuestas con votos
    cur.execute("""
        SELECT rf.id, rf.contenido, rf.es_anonimo, rf.aceptada, rf.creado_en,
               rf.autor_id, u.nombre AS autor_nombre,
               COALESCE((SELECT SUM(v.valor) FROM votos_respuesta v WHERE v.respuesta_id = rf.id), 0) AS votos,
               (SELECT v.valor FROM votos_respuesta v
                WHERE v.respuesta_id = rf.id AND v.usuario_id = ?) AS mi_voto
        FROM respuestas_foro rf
        JOIN usuarios u ON u.id = rf.autor_id
        WHERE rf.pregunta_id = ?
        ORDER BY rf.aceptada DESC, votos DESC, rf.creado_en ASC
    """, (session['user_id'], pregunta_id))
    filas = cur.fetchall()
    conn.close()

    respuestas = []
    for f in filas:
        d = dict(f)
        d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
        d['mi_voto'] = d['mi_voto'] or 0
        respuestas.append(d)

    es_autor_pregunta = (pregunta.get('autor_id') == session['user_id'])

    return render_template('foros/pregunta.html',
                           foro=dict(foro),
                           pregunta=pregunta,
                           respuestas=respuestas,
                           es_autor_pregunta=es_autor_pregunta)


# ── NUEVA RESPUESTA ── ★ NUEVO ─────────────
@app.route('/foros/<int:foro_id>/pregunta/<int:pregunta_id>/responder', methods=['POST'])
@login_required
def nueva_respuesta(foro_id, pregunta_id):
    contenido  = request.form.get('contenido', '').strip()
    es_anonimo = 1 if request.form.get('es_anonimo') else 0

    if not contenido:
        flash('La respuesta no puede estar vacía.', 'error')
        return redirect(url_for('foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

    if len(contenido) > 2000:
        flash('La respuesta no puede superar 2000 caracteres.', 'error')
        return redirect(url_for('foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO respuestas_foro (pregunta_id, autor_id, contenido, es_anonimo) VALUES (?,?,?,?)",
            (pregunta_id, session['user_id'], contenido, es_anonimo)
        )
        conn.commit()
        flash('Respuesta publicada.', 'success')
    except Exception as e:
        flash(f'Error al responder: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))


# ── ACEPTAR RESPUESTA (solo el autor) ── ★ NUEVO ──
@app.route('/foros/pregunta/<int:pregunta_id>/aceptar/<int:respuesta_id>', methods=['POST'])
@login_required
def aceptar_respuesta(pregunta_id, respuesta_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        # Verificar que el usuario es el autor de la pregunta
        cur.execute("SELECT autor_id, foro_id FROM preguntas_foro WHERE id = ?", (pregunta_id,))
        preg = cur.fetchone()
        if not preg or preg['autor_id'] != session['user_id']:
            flash('Sin permiso.', 'error')
            conn.close()
            return redirect(url_for('foros'))

        # Desmarcar cualquier respuesta aceptada anterior
        conn.execute("UPDATE respuestas_foro SET aceptada = 0 WHERE pregunta_id = ?", (pregunta_id,))
        # Marcar la nueva
        conn.execute("UPDATE respuestas_foro SET aceptada = 1 WHERE id = ? AND pregunta_id = ?",
                     (respuesta_id, pregunta_id))
        conn.commit()
        flash('Respuesta marcada como correcta.', 'success')
        foro_id = preg['foro_id']
    except Exception as e:
        flash(f'Error: {e}', 'error')
        foro_id = 0
    finally:
        conn.close()

    return redirect(url_for('foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))


# ── VOTAR RESPUESTA (AJAX) ── ★ NUEVO ──────
@app.route('/foros/respuesta/<int:respuesta_id>/votar', methods=['POST'])
@login_required
def votar_respuesta(respuesta_id):
    data  = request.get_json(silent=True) or {}
    valor = data.get('valor', 1)
    if valor not in (1, -1):
        return jsonify({'ok': False}), 400

    user_id = session['user_id']
    conn    = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT valor FROM votos_respuesta WHERE respuesta_id = ? AND usuario_id = ?",
            (respuesta_id, user_id)
        )
        existente = cur.fetchone()

        if existente:
            if existente['valor'] == valor:
                # Mismo voto → quita el voto (toggle)
                conn.execute(
                    "DELETE FROM votos_respuesta WHERE respuesta_id = ? AND usuario_id = ?",
                    (respuesta_id, user_id)
                )
                mi_voto = 0
            else:
                # Voto opuesto → cambia
                conn.execute(
                    "UPDATE votos_respuesta SET valor = ? WHERE respuesta_id = ? AND usuario_id = ?",
                    (valor, respuesta_id, user_id)
                )
                mi_voto = valor
        else:
            conn.execute(
                "INSERT INTO votos_respuesta (respuesta_id, usuario_id, valor) VALUES (?,?,?)",
                (respuesta_id, user_id, valor)
            )
            mi_voto = valor

        conn.commit()

        cur.execute(
            "SELECT COALESCE(SUM(valor), 0) AS total FROM votos_respuesta WHERE respuesta_id = ?",
            (respuesta_id,)
        )
        total = cur.fetchone()['total']
        return jsonify({'ok': True, 'total': total, 'mi_voto': mi_voto})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ══════════════════════════════════════════
# PORTAFOLIO  ★ NUEVO
# ══════════════════════════════════════════

@app.route('/portafolio')
@login_required
def portafolio():
    user_id = session['user_id']
    conn    = get_db()
    cur     = conn.cursor()

    # Mis proyectos
    cur.execute("""
        SELECT p.*,
               (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
               (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
        FROM proyectos p
        WHERE p.autor_id = ?
        ORDER BY p.destacado DESC, p.creado_en DESC
    """, (user_id, user_id))
    mis = []
    for f in cur.fetchall():
        d = dict(f); d['tecnologias_lista'] = parsear_tecnologias(d.get('tecnologias')); mis.append(d)

    # Proyectos de la comunidad (excluye los propios)
    cur.execute("""
        SELECT p.*, u.nombre AS autor_nombre,
               (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
               (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
        FROM proyectos p JOIN usuarios u ON u.id = p.autor_id
        WHERE p.autor_id != ?
        ORDER BY total_aplausos DESC, p.creado_en DESC
        LIMIT 20
    """, (user_id, user_id))
    todos = []
    for f in cur.fetchall():
        d = dict(f); d['tecnologias_lista'] = parsear_tecnologias(d.get('tecnologias')); todos.append(d)

    conn.close()
    return render_template('portafolio/lista.html', mis_proyectos=mis, todos_proyectos=todos)


@app.route('/nuevo-proyecto', methods=['POST'])
@login_required
def nuevo_proyecto():
    titulo       = request.form.get('titulo', '').strip()
    descripcion  = request.form.get('descripcion', '').strip()
    techs_raw    = request.form.get('tecnologias', '').strip()
    materia      = request.form.get('materia', '').strip()
    estado       = request.form.get('estado', 'en_desarrollo').strip()
    repo_url     = request.form.get('repo_url', '').strip() or None
    demo_url     = request.form.get('demo_url', '').strip() or None

    if not titulo:
        flash('El título es obligatorio.', 'error')
        return redirect(url_for('portafolio'))

    if estado not in ('en_desarrollo', 'completado', 'pausado'):
        estado = 'en_desarrollo'

    # Convierte "Flask, Python" → '["Flask","Python"]' para almacenar en JSON
    techs_lista = [t.strip() for t in techs_raw.split(',') if t.strip()]
    tecnologias = json.dumps(techs_lista, ensure_ascii=False) if techs_lista else None

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO proyectos (autor_id, titulo, descripcion, tecnologias, materia, estado, repo_url, demo_url)
            VALUES (?,?,?,?,?,?,?,?)
        """, (session['user_id'], titulo, descripcion or None, tecnologias, materia or None, estado, repo_url, demo_url))
        conn.commit()
        flash('¡Proyecto publicado!', 'success')
    except Exception as e:
        flash(f'Error al crear proyecto: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('portafolio'))


@app.route('/portafolio/<int:proy_id>/aplaudir', methods=['POST'])
@login_required
def aplaudir_proyecto(proy_id):
    user_id = session['user_id']
    conn    = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?",
            (proy_id, user_id)
        )
        if cur.fetchone():
            conn.execute("DELETE FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?", (proy_id, user_id))
            activo = False
        else:
            conn.execute("INSERT INTO aplausos_proyecto (proyecto_id, usuario_id) VALUES (?,?)", (proy_id, user_id))
            activo = True
        conn.commit()

        cur.execute("SELECT COUNT(*) AS total FROM aplausos_proyecto WHERE proyecto_id = ?", (proy_id,))
        total = cur.fetchone()['total']
        return jsonify({'ok': True, 'activo': activo, 'total': total})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        conn.close()


# ══════════════════════════════════════════
# EVENTOS  ★ NUEVO
# ══════════════════════════════════════════

@app.route('/eventos')
@login_required
def eventos():
    cat_activa = request.args.get('cat', 'todos')
    user_id    = session['user_id']
    conn       = get_db()
    cur        = conn.cursor()

    where = ""
    params = [user_id]
    if cat_activa in ('academico', 'cultural', 'deportivo', 'bienestar'):
        where = "AND e.categoria = ?"
        params.append(cat_activa)

    cur.execute(f"""
        SELECT e.*,
               (SELECT 1 FROM inscripciones_evento i
                WHERE i.evento_id = e.id AND i.usuario_id = ?) AS inscrito,
               CASE WHEN e.cupos IS NULL THEN NULL
                    ELSE e.cupos - (SELECT COUNT(*) FROM inscripciones_evento i2 WHERE i2.evento_id = e.id)
               END AS cupos_libres
        FROM eventos e
        WHERE e.fecha >= date('now') {where}
        ORDER BY e.fecha ASC, e.hora_inicio ASC
    """, params)

    eventos_lista = [procesar_evento(r) for r in cur.fetchall()]
    conn.close()

    return render_template('eventos/lista.html', eventos=eventos_lista, cat_activa=cat_activa)


@app.route('/nuevo-evento', methods=['POST'])
@login_required
def nuevo_evento():
    titulo      = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    categoria   = request.form.get('categoria', 'academico').strip()
    fecha       = request.form.get('fecha', '').strip()
    hora_inicio = request.form.get('hora_inicio', '').strip() or None
    hora_fin    = request.form.get('hora_fin', '').strip() or None
    lugar       = request.form.get('lugar', '').strip() or None
    cupos_raw   = request.form.get('cupos', '').strip()
    organizador = request.form.get('organizador', '').strip() or None

    if not titulo or not fecha:
        flash('El título y la fecha son obligatorios.', 'error')
        return redirect(url_for('eventos'))

    if categoria not in ('academico', 'cultural', 'deportivo', 'bienestar'):
        categoria = 'academico'

    cupos = int(cupos_raw) if cupos_raw.isdigit() else None

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO eventos (creador_id, titulo, descripcion, categoria, fecha, hora_inicio, hora_fin, lugar, cupos, organizador)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (session['user_id'], titulo, descripcion or None, categoria, fecha,
              hora_inicio, hora_fin, lugar, cupos, organizador))
        conn.commit()
        flash('¡Evento publicado!', 'success')
    except Exception as e:
        flash(f'Error al crear evento: {e}', 'error')
    finally:
        conn.close()

    return redirect(url_for('eventos'))


@app.route('/eventos/<int:evento_id>/inscribir', methods=['POST'])
@login_required
def inscribir_evento(evento_id):
    user_id = session['user_id']
    conn    = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT cupos FROM eventos WHERE id = ?", (evento_id,))
        ev = cur.fetchone()
        if not ev:
            return jsonify({'ok': False, 'error': 'Evento no encontrado'}), 404

        cur.execute(
            "SELECT 1 FROM inscripciones_evento WHERE evento_id = ? AND usuario_id = ?",
            (evento_id, user_id)
        )
        if cur.fetchone():
            # Ya inscrito → cancela
            conn.execute("DELETE FROM inscripciones_evento WHERE evento_id = ? AND usuario_id = ?", (evento_id, user_id))
            inscrito = False
        else:
            # Verificar cupos si existe límite
            if ev['cupos'] is not None:
                cur.execute("SELECT COUNT(*) AS n FROM inscripciones_evento WHERE evento_id = ?", (evento_id,))
                inscritos = cur.fetchone()['n']
                if inscritos >= ev['cupos']:
                    return jsonify({'ok': False, 'error': 'Sin cupos disponibles'}), 400
            conn.execute("INSERT INTO inscripciones_evento (evento_id, usuario_id) VALUES (?,?)", (evento_id, user_id))
            inscrito = True

        conn.commit()

        # Recalcular cupos libres
        cupos_libres = None
        if ev['cupos'] is not None:
            cur.execute("SELECT COUNT(*) AS n FROM inscripciones_evento WHERE evento_id = ?", (evento_id,))
            cupos_libres = ev['cupos'] - cur.fetchone()['n']

        return jsonify({'ok': True, 'inscrito': inscrito, 'cupos_libres': cupos_libres})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500
    finally:
        conn.close()




# ══════════════════════════════════════════
# AJUSTES DE CUENTA
# ══════════════════════════════════════════

@app.route('/ajustes')
@login_required
def ajustes():
    conn = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('ajustes/ajustes.html', usuario=usuario, pagina_activa='ajustes')

@app.route('/ajustes/perfil', methods=['POST'])
@login_required
def ajustes_perfil():
    nombre      = request.form.get('nombre', '').strip()
    bio         = request.form.get('bio', '').strip()
    carrera     = request.form.get('carrera', '').strip()
    universidad = request.form.get('universidad', '').strip()
    avatar_url  = request.form.get('avatar_url', '').strip()
    if not nombre:
        flash('El nombre no puede estar vacío.', 'error')
        return redirect(url_for('ajustes'))
    conn = get_db()
    conn.execute("UPDATE usuarios SET nombre=?, bio=?, carrera=?, universidad=?, avatar_url=? WHERE id=?",
        (nombre, bio or None, carrera or None, universidad or None, avatar_url or None, session['user_id']))
    conn.commit()
    conn.close()
    session['nombre'] = nombre
    session['carrera'] = carrera
    session['universidad'] = universidad
    flash('Perfil actualizado correctamente.', 'success')
    return redirect(url_for('ajustes'))

@app.route('/ajustes/correo', methods=['POST'])
@login_required
def ajustes_correo():
    nuevo_correo  = request.form.get('correo', '').strip().lower()
    password_conf = request.form.get('password_conf', '')
    if not nuevo_correo or not password_conf:
        flash('Completa todos los campos.', 'error')
        return redirect(url_for('ajustes'))
    conn    = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
    if not check_password_hash(usuario['password'], password_conf):
        conn.close()
        flash('Contraseña incorrecta.', 'error')
        return redirect(url_for('ajustes'))
    existente = conn.execute("SELECT id FROM usuarios WHERE correo = ? AND id != ?",
        (nuevo_correo, session['user_id'])).fetchone()
    if existente:
        conn.close()
        flash('Ese correo ya está en uso.', 'error')
        return redirect(url_for('ajustes'))
    conn.execute("UPDATE usuarios SET correo = ? WHERE id = ?", (nuevo_correo, session['user_id']))
    conn.commit()
    conn.close()
    flash('Correo actualizado correctamente.', 'success')
    return redirect(url_for('ajustes'))

@app.route('/ajustes/password', methods=['POST'])
@login_required
def ajustes_password():
    password_actual = request.form.get('password_actual', '')
    password_nueva  = request.form.get('password_nueva', '')
    password_conf   = request.form.get('password_conf', '')
    if not password_actual or not password_nueva or not password_conf:
        flash('Completa todos los campos.', 'error')
        return redirect(url_for('ajustes'))
    if password_nueva != password_conf:
        flash('Las contraseñas no coinciden.', 'error')
        return redirect(url_for('ajustes'))
    if len(password_nueva) < 6:
        flash('Mínimo 6 caracteres.', 'error')
        return redirect(url_for('ajustes'))
    conn    = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
    if not check_password_hash(usuario['password'], password_actual):
        conn.close()
        flash('Contraseña actual incorrecta.', 'error')
        return redirect(url_for('ajustes'))
    conn.execute("UPDATE usuarios SET password = ? WHERE id = ?",
        (generate_password_hash(password_nueva), session['user_id']))
    conn.commit()
    conn.close()
    flash('Contraseña actualizada.', 'success')
    return redirect(url_for('ajustes'))


# ══════════════════════════════════════════
# SEGUIMIENTO
# ══════════════════════════════════════════

@app.route('/seguir/<int:objetivo_id>', methods=['POST'])
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
                 url_for('ver_perfil_usuario', usuario_id=user_id)))
            conn.commit()
            socketio.emit('notificacion', {
                'mensaje': f"{session['nombre']} comenzó a seguirte.",
                'tipo': 'seguidor',
                'url': url_for('ver_perfil_usuario', usuario_id=user_id)
            }, room=f'user_{objetivo_id}')
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM seguidores WHERE seguido_id = ?", (objetivo_id,)).fetchone()['n']
        return jsonify({'ok': True, 'siguiendo': True, 'total_seguidores': total})
    finally:
        conn.close()

@app.route('/dejar-seguir/<int:objetivo_id>', methods=['POST'])
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

@app.route('/perfil/<int:usuario_id>')
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
        return redirect(url_for('explorar'))
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

@app.route('/seguidores/<int:usuario_id>')
@login_required
def ver_seguidores(usuario_id):
    conn = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not usuario:
        conn.close()
        return redirect(url_for('explorar'))
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

@app.route('/siguiendo/<int:usuario_id>')
@login_required
def ver_siguiendo(usuario_id):
    conn = get_db()
    usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if not usuario:
        conn.close()
        return redirect(url_for('explorar'))
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


# ══════════════════════════════════════════
# NOTIFICACIONES
# ══════════════════════════════════════════

@app.route('/notificaciones')
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

@app.route('/notificaciones/no-leidas')
@login_required
def notificaciones_no_leidas():
    conn  = get_db()
    total = conn.execute(
        "SELECT COUNT(*) AS n FROM notificaciones WHERE usuario_id = ? AND leida = 0",
        (session['user_id'],)).fetchone()['n']
    conn.close()
    return jsonify({'total': total})


# ══════════════════════════════════════════
# MODERACIÓN
# ══════════════════════════════════════════


def obtener_usuario_reportado(conn, tipo, referencia_id):
    """Mantiene la interfaz histórica para las rutas de moderación."""
    return resolver_usuario_reportado(conn, tipo, referencia_id)


def motivo_para_no_suspender(objetivo):
    """Mantiene la interfaz histórica para las rutas de moderación."""
    return evaluar_suspension(
        objetivo,
        session['user_id'],
        session.get('rol'),
    )



@app.route('/moderacion')
@login_required
@moderador_required
def moderacion():
    conn = get_db()
    cur  = conn.cursor()
    # Reportes pendientes de revisión
    cur.execute(f"""
        SELECT r.id, r.tipo, r.motivo, r.creado_en, r.estado,
               u.nombre AS reportador,
               r.referencia_id AS contenido_id
        FROM reportes r
        JOIN usuarios u ON u.id = r.reportado_por
        WHERE r.{SQL_REPORTE_ABIERTO}
        ORDER BY r.creado_en DESC
        LIMIT 50
    """)
    reportes = cur.fetchall()
    # Estadísticas rápidas
    cur.execute(f"SELECT COUNT(*) AS n FROM reportes WHERE {SQL_REPORTE_ABIERTO}")
    total_pendientes = cur.fetchone()['n']
    cur.execute("SELECT COUNT(*) AS n FROM reportes WHERE estado = 'resuelto'")
    total_resueltos  = cur.fetchone()['n']
    cur.execute("SELECT COUNT(*) AS n FROM usuarios WHERE activo = 1")
    total_usuarios   = cur.fetchone()['n']
    conn.close()
    return render_template('moderacion/moderacion.html',
                           reportes=reportes,
                           total_pendientes=total_pendientes,
                           total_resueltos=total_resueltos,
                           total_usuarios=total_usuarios,
                           pagina_activa='moderacion')

@app.route('/reporte/nuevo', methods=['POST'])
@login_required
def crear_reporte():
    """Cualquier usuario puede reportar contenido."""
    tipo         = request.form.get('tipo', '')        # publicacion, comentario, usuario
    contenido_id = request.form.get('contenido_id', 0, type=int)
    motivo       = request.form.get('motivo', '').strip()
    if tipo not in TIPOS_REPORTE:
        return jsonify({'ok': False, 'error': 'Tipo de reporte no válido'}), 400
    if not contenido_id or not motivo:
        return jsonify({'ok': False, 'error': 'Datos incompletos'}), 400
    conn = get_db()
    try:
        if not obtener_usuario_reportado(conn, tipo, contenido_id):
            return jsonify({'ok': False, 'error': 'El contenido reportado no existe.'}), 404
        # Evitar reportes duplicados del mismo usuario
        existe = conn.execute(
            f"SELECT 1 FROM reportes WHERE reportado_por = ? AND tipo = ? AND referencia_id = ? AND {SQL_REPORTE_ABIERTO}",
            (session['user_id'], tipo, contenido_id)).fetchone()
        if existe:
            return jsonify({'ok': False, 'error': 'Ya reportaste este contenido.'})
        conn.execute(
            "INSERT INTO reportes (reportado_por, tipo, referencia_id, motivo) VALUES (?, ?, ?, ?)",
            (session['user_id'], tipo, contenido_id, motivo))
        conn.commit()
        return jsonify({'ok': True})
    finally:
        conn.close()

@app.route('/moderacion/resolver/<int:reporte_id>', methods=['POST'])
@login_required
@moderador_required
def resolver_reporte(reporte_id):
    accion = request.form.get('accion', 'ignorar')  # ignorar | eliminar | suspender
    if accion not in ACCIONES_REPORTE:
        flash('Acción no válida.', 'error')
        return redirect(url_for('moderacion'))
    conn   = get_db()
    try:
        reporte = conn.execute("SELECT * FROM reportes WHERE id = ?", (reporte_id,)).fetchone()
        if not reporte:
            flash('Reporte no encontrado.', 'error')
            return redirect(url_for('moderacion'))
        if reporte['estado'] not in ESTADOS_ABIERTOS:
            flash('Este reporte ya estaba cerrado.', 'error')
            return redirect(url_for('moderacion'))
        if accion == 'eliminar' and reporte['tipo'] == 'usuario':
            flash('Un reporte de usuario no tiene contenido que eliminar.', 'error')
            return redirect(url_for('moderacion'))
        if accion == 'eliminar':
            if reporte['tipo'] == 'publicacion':
                conn.execute("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", (reporte['referencia_id'],))
            elif reporte['tipo'] == 'comentario':
                conn.execute("DELETE FROM comentarios WHERE id = ?", (reporte['referencia_id'],))
        elif accion == 'suspender':
            objetivo = obtener_usuario_reportado(conn, reporte['tipo'], reporte['referencia_id'])
            error = motivo_para_no_suspender(objetivo)
            if error:
                flash(error, 'error')
                return redirect(url_for('moderacion'))
            conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (objetivo['id'],))
        conn.execute("UPDATE reportes SET estado = 'resuelto', revisado_por = ? WHERE id = ?",
            (session['user_id'], reporte_id))
        conn.commit()
        flash(f'Reporte #{reporte_id} resuelto ({accion}).', 'success')
    finally:
        conn.close()
    return redirect(url_for('moderacion'))






# ══════════════════════════════════════════
# EVENTOS — Ver / Editar / Eliminar / Participantes
# ══════════════════════════════════════════

@app.route('/eventos/<int:evento_id>')
@login_required
def ver_evento(evento_id):
    """Detalle completo de un evento con participantes."""
    user_id = session['user_id']
    conn    = get_db()
    cur     = conn.cursor()

    cur.execute("""
        SELECT e.*,
               (SELECT 1 FROM inscripciones_evento i
                WHERE i.evento_id = e.id AND i.usuario_id = ?) AS inscrito,
               CASE WHEN e.cupos IS NULL THEN NULL
                    ELSE e.cupos - (SELECT COUNT(*) FROM inscripciones_evento i2
                                   WHERE i2.evento_id = e.id)
               END AS cupos_libres
        FROM eventos e WHERE e.id = ?
    """, (user_id, evento_id))
    row = cur.fetchone()

    if not row:
        conn.close()
        flash('Evento no encontrado.', 'error')
        return redirect(url_for('eventos'))

    evento = procesar_evento(row)

    # Lista de participantes inscritos
    cur.execute("""
        SELECT u.id, u.nombre, u.avatar_url
        FROM inscripciones_evento ie
        JOIN usuarios u ON u.id = ie.usuario_id
        WHERE ie.evento_id = ?
        ORDER BY ie.creado_en ASC
    """, (evento_id,))
    participantes = cur.fetchall()
    conn.close()

    es_creador = (evento['creador_id'] == user_id)

    return render_template('eventos/ver_evento.html',
                           evento=evento,
                           participantes=participantes,
                           es_creador=es_creador,
                           pagina_activa='eventos')


@app.route('/eventos/<int:evento_id>/editar', methods=['GET', 'POST'])
@login_required
def editar_evento(evento_id):
    """Editar un evento (solo el creador)."""
    user_id = session['user_id']
    conn    = get_db()
    evento  = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if not evento:
        conn.close()
        flash('Evento no encontrado.', 'error')
        return redirect(url_for('eventos'))

    if evento['creador_id'] != user_id:
        conn.close()
        flash('No tienes permiso para editar este evento.', 'error')
        return redirect(url_for('ver_evento', evento_id=evento_id))

    if request.method == 'POST':
        titulo      = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria   = request.form.get('categoria', 'academico')
        fecha       = request.form.get('fecha', '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip() or None
        hora_fin    = request.form.get('hora_fin', '').strip() or None
        lugar       = request.form.get('lugar', '').strip() or None
        organizador = request.form.get('organizador', '').strip() or None
        cupos_raw   = request.form.get('cupos', '').strip()
        cupos       = int(cupos_raw) if cupos_raw.isdigit() else None

        if not titulo or not fecha:
            flash('El título y la fecha son obligatorios.', 'error')
            return render_template('eventos/editar_evento.html', evento=dict(evento),
                                   pagina_activa='eventos')

        conn.execute("""
            UPDATE eventos
            SET titulo=?, descripcion=?, categoria=?, fecha=?,
                hora_inicio=?, hora_fin=?, lugar=?, organizador=?, cupos=?
            WHERE id=?
        """, (titulo, descripcion or None, categoria, fecha,
              hora_inicio, hora_fin, lugar, organizador, cupos, evento_id))
        conn.commit()
        conn.close()
        flash('Evento actualizado correctamente.', 'success')
        return redirect(url_for('ver_evento', evento_id=evento_id))

    conn.close()
    return render_template('eventos/editar_evento.html',
                           evento=dict(evento),
                           pagina_activa='eventos')


@app.route('/eventos/<int:evento_id>/eliminar', methods=['POST'])
@login_required
def eliminar_evento(evento_id):
    """Eliminar un evento (solo el creador o admin/moderador)."""
    user_id = session['user_id']
    conn    = get_db()
    evento  = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if not evento:
        conn.close()
        flash('Evento no encontrado.', 'error')
        return redirect(url_for('eventos'))

    # Verificar permiso: creador o moderador/admin
    usuario = conn.execute("SELECT rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
    es_mod  = usuario and usuario['rol'] in ('admin', 'moderador')

    if evento['creador_id'] != user_id and not es_mod:
        conn.close()
        flash('No tienes permiso para eliminar este evento.', 'error')
        return redirect(url_for('ver_evento', evento_id=evento_id))

    # Eliminar inscripciones primero, luego el evento
    conn.execute("DELETE FROM inscripciones_evento WHERE evento_id = ?", (evento_id,))
    conn.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
    conn.commit()
    conn.close()

    flash('Evento eliminado.', 'success')
    return redirect(url_for('eventos'))


@app.route('/eventos/<int:evento_id>/participantes')
@login_required
def ver_participantes(evento_id):
    """Lista de usuarios inscritos en un evento."""
    conn   = get_db()
    evento = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

    if not evento:
        conn.close()
        flash('Evento no encontrado.', 'error')
        return redirect(url_for('eventos'))

    participantes = conn.execute("""
        SELECT u.id, u.nombre, u.avatar_url, u.carrera, u.universidad,
               ie.creado_en
        FROM inscripciones_evento ie
        JOIN usuarios u ON u.id = ie.usuario_id
        WHERE ie.evento_id = ?
        ORDER BY ie.creado_en ASC
    """, (evento_id,)).fetchall()

    conn.close()
    return render_template('eventos/ver_participantes.html',
                           evento=dict(evento),
                           participantes=participantes,
                           pagina_activa='eventos')


# ══════════════════════════════════════════
# RUTAS PENDIENTES DE IMPLEMENTAR
# (stubs funcionales para que no explote el sidebar)
# ══════════════════════════════════════════

@app.route('/ayuda')
@login_required
def ayuda():
    return render_template('ajustes/ayuda.html', pagina_activa='ayuda')


@app.route('/reportes')
@login_required
def reportes():
    conn   = get_db()
    mis_reportes = conn.execute(
        "SELECT * FROM reportes WHERE reportado_por = ? ORDER BY creado_en DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()
    return render_template('moderacion/reportes.html', reportes=mis_reportes, pagina_activa='reportes')


@app.route('/tendencias')
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


@app.route('/admin')
@login_required
def admin_panel():
    conn    = get_db()
    cur     = conn.cursor()
    usuario = cur.execute(
        "SELECT rol FROM usuarios WHERE id = ?", (session['user_id'],)
    ).fetchone()
    if not usuario or usuario['rol'] not in ('admin', 'moderador'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('publicaciones.feed'))
    cur.execute("SELECT COUNT(*) AS n FROM usuarios WHERE activo = 1")
    total_usuarios = cur.fetchone()['n']
    cur.execute("SELECT COUNT(*) AS n FROM publicaciones WHERE estado = 'publicado'")
    total_posts = cur.fetchone()['n']
    cur.execute(f"SELECT COUNT(*) AS n FROM reportes WHERE {SQL_REPORTE_ABIERTO}")
    total_reportes = cur.fetchone()['n']
    cur.execute("SELECT COUNT(*) AS n FROM eventos WHERE fecha >= date('now')")
    total_eventos = cur.fetchone()['n']
    conn.close()
    return render_template('moderacion/panel.html',
                           total_usuarios=total_usuarios,
                           total_posts=total_posts,
                           total_reportes=total_reportes,
                           total_eventos=total_eventos,
                           pagina_activa='admin')


# ══════════════════════════════════════════
# MENSAJES PRIVADOS
# ══════════════════════════════════════════

@app.route('/mensajes/no-leidos')
@login_required
def mensajes_no_leidos():
    """Devuelve el total de mensajes no leídos del usuario (para el badge del sidebar)."""
    conn = get_db()
    total = conn.execute("""
        SELECT COUNT(*) FROM mensajes m
        JOIN participantes_conversacion pc ON pc.conversacion_id = m.conversacion_id
            AND pc.usuario_id = ?
        WHERE m.autor_id != ? AND m.leido = 0
    """, (session['user_id'], session['user_id'])).fetchone()[0]
    conn.close()
    return {'total': total}


@app.route('/mensajes')
@login_required
def mensajes():
    """Lista de conversaciones activas del usuario, con preview y no-leídos."""
    conn = get_db()
    convs = conn.execute("""
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
    """, {'me': session['user_id']}).fetchall()
    conn.close()
    return render_template('mensajes/lista.html',
                           pagina_activa='mensajes',
                           conversaciones=convs)


@app.route('/mensajes/<int:otro_id>')
@login_required
def ver_chat(otro_id):
    """Abre (o crea) la conversación 1-a-1 con otro usuario."""
    conn = get_db()
    otro = conn.execute(
        "SELECT id, nombre, carrera FROM usuarios WHERE id = ? AND activo = 1",
        (otro_id,)
    ).fetchone()
    if not otro:
        conn.close()
        flash('Usuario no encontrado.', 'error')
        return redirect(url_for('mensajes'))

    me = session['user_id']

    # Buscar conversación existente
    conv = conn.execute("""
        SELECT c.id FROM conversaciones c
        JOIN participantes_conversacion p1 ON p1.conversacion_id = c.id AND p1.usuario_id = ?
        JOIN participantes_conversacion p2 ON p2.conversacion_id = c.id AND p2.usuario_id = ?
        LIMIT 1
    """, (me, otro_id)).fetchone()

    if conv:
        conv_id = conv['id']
    else:
        cur = conn.execute("INSERT INTO conversaciones DEFAULT VALUES")
        conv_id = cur.lastrowid
        conn.execute(
            "INSERT INTO participantes_conversacion (conversacion_id, usuario_id) VALUES (?,?)",
            (conv_id, me))
        conn.execute(
            "INSERT INTO participantes_conversacion (conversacion_id, usuario_id) VALUES (?,?)",
            (conv_id, otro_id))
        conn.commit()

    # Marcar como leídos
    conn.execute("""
        UPDATE mensajes SET leido = 1
        WHERE conversacion_id = ? AND autor_id != ? AND leido = 0
    """, (conv_id, me))
    conn.commit()

    mensajes_list = conn.execute("""
        SELECT m.id, m.autor_id, m.contenido, m.leido, m.creado_en,
               u.nombre AS autor_nombre
        FROM mensajes m
        JOIN usuarios u ON u.id = m.autor_id
        WHERE m.conversacion_id = ?
        ORDER BY m.creado_en ASC
    """, (conv_id,)).fetchall()

    conn.close()
    return render_template('mensajes/chat.html',
                           pagina_activa='mensajes',
                           otro=otro,
                           conv_id=conv_id,
                           mensajes=mensajes_list,
                           user_id=me)


@app.route('/mensajes/<int:conv_id>/enviar', methods=['POST'])
@login_required
def enviar_mensaje(conv_id):
    """Guarda el mensaje y lo emite en tiempo real por Socket.IO."""
    contenido = request.form.get('contenido', '').strip()
    if not contenido or len(contenido) > 1000:
        return ('', 400)

    me = session['user_id']
    conn = get_db()

    participa = conn.execute("""
        SELECT 1 FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conv_id, me)).fetchone()
    if not participa:
        conn.close()
        return ('', 403)

    cur = conn.execute("""
        INSERT INTO mensajes (conversacion_id, autor_id, contenido)
        VALUES (?, ?, ?)
    """, (conv_id, me, contenido))
    msg_id = cur.lastrowid

    conn.execute(
        "UPDATE conversaciones SET ultimo_msg = CURRENT_TIMESTAMP WHERE id = ?",
        (conv_id,))

    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, me)).fetchone()

    msg_row = conn.execute(
        "SELECT creado_en FROM mensajes WHERE id = ?", (msg_id,)
    ).fetchone()
    hora = msg_row['creado_en'][11:16] if msg_row else ''

    conn.commit()
    conn.close()

    payload = {
        'msg_id':    msg_id,
        'conv_id':   conv_id,
        'autor_id':  me,
        'nombre':    session['nombre'],
        'contenido': contenido,
        'hora':      hora,
    }
    # Emitir al remitente y al receptor
    socketio.emit('mensaje_nuevo', payload, room=f"user_{me}")
    if otro:
        receptor_id = otro['usuario_id']
        socketio.emit('mensaje_nuevo', payload, room=f"user_{receptor_id}")
        socketio.emit('notificacion', {
            'mensaje': f"{session['nombre']} te envió un mensaje.",
            'url': url_for('ver_chat', otro_id=me)
        }, room=f"user_{receptor_id}")

    return {'ok': True, 'msg_id': msg_id, 'hora': hora}


@app.route('/mensajes/<int:conv_id>/archivar', methods=['POST'])
@login_required
def archivar_conversacion(conv_id):
    """Oculta la conversación de la lista sin borrarla."""
    conn = get_db()
    conn.execute("""
        UPDATE participantes_conversacion
        SET archivada = 1
        WHERE conversacion_id = ? AND usuario_id = ?
    """, (conv_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('Conversación archivada.', 'success')
    return redirect(url_for('mensajes'))


# ══════════════════════════════════════════
# SOCKETIO — Eventos
# ══════════════════════════════════════════

@socketio.on('connect')
def on_connect():
    # before_request no se ejecuta en las conexiones de Socket.IO
    if session.get('user_id'):
        cuenta = obtener_cuenta(session['user_id'])
        if not cuenta or not cuenta['activo']:
            return False

    if session.get('user_id'):
        join_room(f"user_{session['user_id']}")

@socketio.on('disconnect')
def on_disconnect():
    if session.get('user_id'):
        leave_room(f"user_{session['user_id']}")

@socketio.on('escribiendo')
def on_escribiendo(data):
    """Retransmite 'escribiendo…' al otro participante del chat."""
    conv_id  = data.get('conv_id')
    autor_id = data.get('autor_id')
    if not conv_id or not autor_id:
        return
    conn = get_db()
    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, autor_id)).fetchone()
    conn.close()
    if otro:
        socketio.emit('escribiendo', data, room=f"user_{otro['usuario_id']}")

@socketio.on('dejo_escribir')
def on_dejo_escribir(data):
    """Retransmite 'dejó de escribir' al otro participante."""
    conv_id  = data.get('conv_id')
    autor_id = data.get('autor_id')
    if not conv_id or not autor_id:
        return
    conn = get_db()
    otro = conn.execute("""
        SELECT usuario_id FROM participantes_conversacion
        WHERE conversacion_id = ? AND usuario_id != ?
    """, (conv_id, autor_id)).fetchone()
    conn.close()
    if otro:
        socketio.emit('dejo_escribir', data, room=f"user_{otro['usuario_id']}")


# ══════════════════════════════════════════
# ARRANQUE
# ══════════════════════════════════════════