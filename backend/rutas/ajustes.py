"""Rutas de ajustes de cuenta y ayuda."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import cuentas as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de ajustes de cuenta."""
    blueprint = Blueprint('ajustes', __name__)

    @blueprint.route('/ajustes')
    @login_required
    def ajustes():
        conn = get_db()
        usuario = servicio.obtener_por_id(conn, session['user_id'])
        conn.close()
        return render_template('ajustes/ajustes.html', usuario=usuario, pagina_activa='ajustes')

    @blueprint.route('/ajustes/perfil', methods=['POST'])
    @login_required
    def ajustes_perfil():
        nombre = request.form.get('nombre', '').strip()
        bio = request.form.get('bio', '').strip()
        carrera = request.form.get('carrera', '').strip()
        universidad = request.form.get('universidad', '').strip()
        avatar_url = request.form.get('avatar_url', '').strip()
        if not nombre:
            flash('El nombre no puede estar vacío.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn = get_db()
        servicio.actualizar_perfil(conn, session['user_id'], nombre, bio or None, carrera or None,
                                   universidad or None, avatar_url or None)
        conn.close()
        session['nombre'] = nombre
        session['carrera'] = carrera
        session['universidad'] = universidad
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ajustes/correo', methods=['POST'])
    @login_required
    def ajustes_correo():
        nuevo_correo = request.form.get('correo', '').strip().lower()
        password_conf = request.form.get('password_conf', '')
        if not nuevo_correo or not password_conf:
            flash('Completa todos los campos.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn = get_db()
        usuario = servicio.obtener_por_id(conn, session['user_id'])
        if not servicio.verificar_password(usuario, password_conf):
            conn.close()
            flash('Contraseña incorrecta.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        if servicio.correo_en_uso(conn, nuevo_correo, session['user_id']):
            conn.close()
            flash('Ese correo ya está en uso.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        servicio.actualizar_correo(conn, session['user_id'], nuevo_correo)
        conn.close()
        flash('Correo actualizado correctamente.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ajustes/password', methods=['POST'])
    @login_required
    def ajustes_password():
        password_actual = request.form.get('password_actual', '')
        password_nueva = request.form.get('password_nueva', '')
        password_conf = request.form.get('password_conf', '')
        if not password_actual or not password_nueva or not password_conf:
            flash('Completa todos los campos.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        if password_nueva != password_conf:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        if len(password_nueva) < 6:
            flash('Mínimo 6 caracteres.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn = get_db()
        usuario = servicio.obtener_por_id(conn, session['user_id'])
        if not servicio.verificar_password(usuario, password_actual):
            conn.close()
            flash('Contraseña actual incorrecta.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        servicio.actualizar_password(conn, session['user_id'], password_nueva)
        conn.close()
        flash('Contraseña actualizada.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ayuda')
    @login_required
    def ayuda():
        return render_template('ajustes/ayuda.html', pagina_activa='ayuda')

    return blueprint
