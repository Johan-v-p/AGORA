"""Rutas de reportes, moderación y panel de administración."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import crear_admin_required, crear_moderador_required, login_required
from backend.servicios import cuentas
from backend.servicios import moderacion as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de moderación."""
    blueprint = Blueprint('moderacion', __name__)
    moderador_required = crear_moderador_required(get_db)
    admin_required = crear_admin_required(get_db)

    @blueprint.route('/moderacion')
    @login_required
    @moderador_required
    def moderacion():
        conn = get_db()
        reportes = servicio.listar_reportes_abiertos(conn)
        total_pendientes = servicio.contar_reportes_abiertos(conn)
        total_resueltos = servicio.contar_reportes_resueltos(conn)
        total_usuarios = servicio.contar_usuarios_activos(conn)
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
        tipo = request.form.get('tipo', '')        # publicacion, comentario, usuario
        contenido_id = request.form.get('contenido_id', 0, type=int)
        motivo = request.form.get('motivo', '').strip()
        if tipo not in servicio.TIPOS_REPORTE:
            return jsonify({'ok': False, 'error': 'Tipo de reporte no válido'}), 400
        if not contenido_id or not motivo:
            return jsonify({'ok': False, 'error': 'Datos incompletos'}), 400
        conn = get_db()
        try:
            if not servicio.obtener_usuario_reportado(conn, tipo, contenido_id):
                return jsonify({'ok': False, 'error': 'El contenido reportado no existe.'}), 404
            # Evitar reportes duplicados del mismo usuario
            if servicio.existe_reporte_abierto(conn, session['user_id'], tipo, contenido_id):
                return jsonify({'ok': False, 'error': 'Ya reportaste este contenido.'})
            servicio.crear_reporte(conn, session['user_id'], tipo, contenido_id, motivo)
            return jsonify({'ok': True})
        finally:
            conn.close()

    @blueprint.route('/moderacion/resolver/<int:reporte_id>', methods=['POST'])
    @login_required
    @moderador_required
    def resolver_reporte(reporte_id):
        accion = request.form.get('accion', 'ignorar')  # ignorar | eliminar | suspender
        if accion not in servicio.ACCIONES_REPORTE:
            flash('Acción no válida.', 'error')
            return redirect(url_for('moderacion.moderacion'))
        conn = get_db()
        try:
            reporte = servicio.obtener_reporte(conn, reporte_id)
            if not reporte:
                flash('Reporte no encontrado.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if reporte['estado'] not in servicio.ESTADOS_ABIERTOS:
                flash('Este reporte ya estaba cerrado.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if accion == 'eliminar' and reporte['tipo'] == 'usuario':
                flash('Un reporte de usuario no tiene contenido que eliminar.', 'error')
                return redirect(url_for('moderacion.moderacion'))
            if accion == 'eliminar':
                servicio.eliminar_contenido_reportado(conn, reporte)
            elif accion == 'suspender':
                objetivo = servicio.obtener_usuario_reportado(conn, reporte['tipo'], reporte['referencia_id'])
                error = servicio.motivo_para_no_suspender(
                    objetivo, session['user_id'], session.get('rol')
                )
                if error:
                    flash(error, 'error')
                    return redirect(url_for('moderacion.moderacion'))
                servicio.suspender_usuario(conn, objetivo['id'])
            servicio.cerrar_reporte(conn, reporte_id, session['user_id'])
            flash(f'Reporte #{reporte_id} resuelto ({accion}).', 'success')
        finally:
            conn.close()
        return redirect(url_for('moderacion.moderacion'))

    @blueprint.route('/reportes')
    @login_required
    def reportes():
        conn = get_db()
        mis_reportes = servicio.listar_reportes_de_usuario(conn, session['user_id'])
        conn.close()
        return render_template('moderacion/reportes.html', reportes=mis_reportes, pagina_activa='reportes')

    @blueprint.route('/admin')
    @login_required
    def admin_panel():
        conn = get_db()
        usuario = cuentas.obtener_rol(conn, session['user_id'])
        if not usuario or usuario['rol'] not in ('admin', 'moderador'):
            conn.close()
            flash('Acceso denegado.', 'error')
            return redirect(url_for('publicaciones.feed'))
        totales = servicio.totales_panel(conn)
        conn.close()
        # La plantilla lee los contadores como stats.total_*.
        return render_template('moderacion/panel.html', stats=totales, pagina_activa='admin')

    # ── Reportes desde formulario ──

    @blueprint.route('/reportar/publicacion')
    @login_required
    def reportar_publicacion():
        post_id = request.args.get('post_id', type=int)
        conn = get_db()
        post = servicio.obtener_publicacion_a_reportar(conn, post_id) if post_id else None
        conn.close()
        return render_template('moderacion/reportar_publicacion.html', post=post,
                               pagina_activa='reportes')

    @blueprint.route('/reportar/comentario')
    @login_required
    def reportar_comentario():
        comentario_id = request.args.get('comentario_id', type=int)
        conn = get_db()
        comentario = (servicio.obtener_comentario_a_reportar(conn, comentario_id)
                      if comentario_id else None)
        conn.close()
        return render_template('moderacion/reportar_comentario.html', comentario=comentario,
                               pagina_activa='reportes')

    @blueprint.route('/reportar/usuario')
    @login_required
    def reportar_usuario():
        usuario_id = request.args.get('usuario_id', type=int)
        conn = get_db()
        usuario_reportado = (servicio.obtener_usuario_a_reportar(conn, usuario_id)
                             if usuario_id else None)
        conn.close()
        return render_template('moderacion/reportar_usuario.html',
                               usuario_reportado=usuario_reportado, pagina_activa='reportes')

    @blueprint.route('/reportar', methods=['POST'])
    @login_required
    def enviar_reporte():
        """Recibe los formularios de reportar_*.html."""
        tipo = request.form.get('tipo', '')
        referencia_id = request.form.get('referencia_id', 0, type=int)
        motivo = request.form.get('motivo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()[:500] or None

        if tipo not in servicio.TIPOS_REPORTE:
            flash('Tipo de reporte no válido.', 'error')
            return redirect(url_for('moderacion.reportes'))
        if not referencia_id:
            flash('No se indicó qué contenido quieres reportar.', 'error')
            return redirect(url_for('moderacion.reportes'))
        if motivo not in servicio.MOTIVOS_REPORTE:
            flash('Elige un motivo para el reporte.', 'error')
            return redirect(url_for('moderacion.reportes'))

        conn = get_db()
        try:
            objetivo = servicio.obtener_usuario_reportado(conn, tipo, referencia_id)
            if not objetivo:
                flash('El contenido reportado no existe.', 'error')
            elif objetivo['id'] == session['user_id']:
                flash('No puedes reportar tu propio contenido.', 'error')
            elif servicio.existe_reporte_abierto(conn, session['user_id'], tipo, referencia_id):
                flash('Ya reportaste este contenido.', 'error')
            else:
                servicio.crear_reporte(conn, session['user_id'], tipo, referencia_id,
                                       motivo, descripcion)
                flash('Reporte enviado. El equipo de moderación lo revisará.', 'success')
        finally:
            conn.close()
        return redirect(url_for('moderacion.reportes'))

    # ── Administración ──

    @blueprint.route('/admin/usuarios')
    @login_required
    @admin_required
    def admin_usuarios():
        q = request.args.get('q', '').strip()
        conn = get_db()
        usuarios = servicio.listar_usuarios(conn, q)
        conn.close()
        return render_template('moderacion/usuarios.html', usuarios=usuarios, q=q,
                               pagina_activa='admin')

    @blueprint.route('/admin/usuarios/<int:uid>/rol', methods=['POST'])
    @login_required
    @admin_required
    def admin_cambiar_rol(uid):
        rol = request.form.get('rol', '')
        if rol not in servicio.ROLES:
            flash('Rol no válido.', 'error')
        elif uid == session['user_id']:
            flash('No puedes cambiar tu propio rol.', 'error')
        else:
            conn = get_db()
            try:
                if not cuentas.obtener_rol(conn, uid):
                    flash('Usuario no encontrado.', 'error')
                else:
                    servicio.cambiar_rol(conn, uid, rol)
                    flash(f'Rol actualizado a {rol}.', 'success')
            finally:
                conn.close()
        return redirect(url_for('moderacion.admin_usuarios'))

    @blueprint.route('/admin/usuarios/<int:uid>/activo', methods=['POST'])
    @login_required
    @admin_required
    def admin_toggle_activo(uid):
        if uid == session['user_id']:
            flash('No puedes suspender tu propia cuenta.', 'error')
            return redirect(url_for('moderacion.admin_usuarios'))
        conn = get_db()
        try:
            if not cuentas.obtener_rol(conn, uid):
                flash('Usuario no encontrado.', 'error')
            else:
                activo = servicio.alternar_activo(conn, uid)
                flash('Cuenta reactivada.' if activo else 'Cuenta suspendida.', 'success')
        finally:
            conn.close()
        return redirect(url_for('moderacion.admin_usuarios'))

    @blueprint.route('/admin/foros', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def admin_foros():
        conn = get_db()
        try:
            if request.method == 'POST':
                accion = request.form.get('accion', '')
                if accion == 'crear':
                    nombre = request.form.get('nombre', '').strip()[:80]
                    descripcion = request.form.get('descripcion', '').strip()[:200] or None
                    categoria = request.form.get('categoria', 'otro')
                    if categoria not in servicio.CATEGORIAS_FORO:
                        categoria = 'otro'
                    if not nombre:
                        flash('El nombre del foro es obligatorio.', 'error')
                    elif servicio.existe_foro_con_nombre(conn, nombre):
                        flash('Ya existe un foro con ese nombre.', 'error')
                    else:
                        servicio.crear_foro(conn, nombre, descripcion, categoria, session['user_id'])
                        flash(f'Foro «{nombre}» creado.', 'success')
                elif accion == 'eliminar':
                    foro_id = request.form.get('foro_id', 0, type=int)
                    if servicio.eliminar_foro(conn, foro_id):
                        flash('Foro eliminado.', 'success')
                    else:
                        flash('Foro no encontrado.', 'error')
                else:
                    flash('Acción no válida.', 'error')
                return redirect(url_for('moderacion.admin_foros'))

            foros = servicio.listar_foros_admin(conn)
        finally:
            conn.close()
        return render_template('moderacion/foros.html', foros=foros, pagina_activa='admin')

    @blueprint.route('/admin/estadisticas')
    @login_required
    @moderador_required
    def admin_estadisticas():
        conn = get_db()
        datos = servicio.estadisticas(conn)
        conn.close()
        return render_template('moderacion/estadisticas.html', **datos, pagina_activa='admin')

    return blueprint
