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
from backend.rutas.portafolio import crear_blueprint as crear_blueprint_portafolio
from backend.rutas.foros import crear_blueprint as crear_blueprint_foros
from backend.rutas.social import crear_blueprint as crear_blueprint_social
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
app.register_blueprint(crear_blueprint_portafolio(get_db))
app.register_blueprint(crear_blueprint_foros(get_db))
app.register_blueprint(crear_blueprint_social(get_db, socketio))
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



# ══════════════════════════════════════════
# EXPLORAR
# ══════════════════════════════════════════



# ══════════════════════════════════════════
# FOROS
# ══════════════════════════════════════════







# ── FORO PREGUNTA DETALLE ── ★ NUEVO ────────


# ── NUEVA RESPUESTA ── ★ NUEVO ─────────────


# ── ACEPTAR RESPUESTA (solo el autor) ── ★ NUEVO ──


# ── VOTAR RESPUESTA (AJAX) ── ★ NUEVO ──────


# ══════════════════════════════════════════
# PORTAFOLIO  ★ NUEVO
# ══════════════════════════════════════════







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







# ══════════════════════════════════════════
# NOTIFICACIONES
# ══════════════════════════════════════════




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