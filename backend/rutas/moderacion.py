"""Rutas de reportes, moderación y panel de administración."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import crear_moderador_required, login_required
from backend.servicios.moderacion import (
    ACCIONES_REPORTE,
    ESTADOS_ABIERTOS,
    SQL_REPORTE_ABIERTO,
    TIPOS_REPORTE,
    motivo_para_no_suspender,
    obtener_usuario_reportado,
)


def crear_blueprint(get_db):
    """Crea el Blueprint de moderación."""
    blueprint = Blueprint('moderacion', __name__)
    moderador_required = crear_moderador_required(get_db)

    @blueprint.route('/moderacion')
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

    @blueprint.route('/reporte/nuevo', methods=['POST'])
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

    @blueprint.route('/moderacion/resolver/<int:reporte_id>', methods=['POST'])
    @login_required
    @moderador_required
    def resolver_reporte(reporte_id):
        accion = request.form.get('accion', 'ignorar')  # ignorar | eliminar | suspender
        if accion not in ACCIONES_REPORTE:
            flash('Acción no válida.', 'error')
            return redirect(url_for('moderacion.moderacion'))
        conn   = get_db()
        try:
            reporte = conn.execute("SELECT * FROM reportes WHERE id = ?", (reporte_id,)).fetchone()
            if not reporte:
                flash('Reporte no encontrado.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if reporte['estado'] not in ESTADOS_ABIERTOS:
                flash('Este reporte ya estaba cerrado.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if accion == 'eliminar' and reporte['tipo'] == 'usuario':
                flash('Un reporte de usuario no tiene contenido que eliminar.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if accion == 'eliminar':
                if reporte['tipo'] == 'publicacion':
                    conn.execute("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", (reporte['referencia_id'],))
                elif reporte['tipo'] == 'comentario':
                    conn.execute("DELETE FROM comentarios WHERE id = ?", (reporte['referencia_id'],))
            elif accion == 'suspender':
                objetivo = obtener_usuario_reportado(conn, reporte['tipo'], reporte['referencia_id'])
                error = motivo_para_no_suspender(
                    objetivo, session['user_id'], session.get('rol')
                )
                if error:
                    flash(error, 'error')
                    return redirect(url_for('moderacion.moderacion'))
                conn.execute("UPDATE usuarios SET activo = 0 WHERE id = ?", (objetivo['id'],))
            conn.execute("UPDATE reportes SET estado = 'resuelto', revisado_por = ? WHERE id = ?",
                (session['user_id'], reporte_id))
            conn.commit()
            flash(f'Reporte #{reporte_id} resuelto ({accion}).', 'success')
        finally:
            conn.close()
        return redirect(url_for('moderacion.moderacion'))

    @blueprint.route('/reportes')
    @login_required
    def reportes():
        conn   = get_db()
        mis_reportes = conn.execute(
            "SELECT * FROM reportes WHERE reportado_por = ? ORDER BY creado_en DESC",
            (session['user_id'],)
        ).fetchall()
        conn.close()
        return render_template('moderacion/reportes.html', reportes=mis_reportes, pagina_activa='reportes')

    @blueprint.route('/admin')
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

    return blueprint
