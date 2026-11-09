"""Rutas de ajustes de cuenta y ayuda."""

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from backend.rutas.decoradores import login_required


def crear_blueprint(get_db):
    """Crea el Blueprint de ajustes de cuenta."""
    blueprint = Blueprint('ajustes', __name__)

    @blueprint.route('/ajustes')
    @login_required
    def ajustes():
        conn = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
        conn.close()
        return render_template('ajustes/ajustes.html', usuario=usuario, pagina_activa='ajustes')

    @blueprint.route('/ajustes/perfil', methods=['POST'])
    @login_required
    def ajustes_perfil():
        nombre      = request.form.get('nombre', '').strip()
        bio         = request.form.get('bio', '').strip()
        carrera     = request.form.get('carrera', '').strip()
        universidad = request.form.get('universidad', '').strip()
        avatar_url  = request.form.get('avatar_url', '').strip()
        if not nombre:
            flash('El nombre no puede estar vacío.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn = get_db()
        conn.execute("UPDATE usuarios SET nombre=?, bio=?, carrera=?, universidad=?, avatar_url=? WHERE id=?",
            (nombre, bio or None, carrera or None, universidad or None, avatar_url or None, session['user_id']))
        conn.commit()
        conn.close()
        session['nombre'] = nombre
        session['carrera'] = carrera
        session['universidad'] = universidad
        flash('Perfil actualizado correctamente.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ajustes/correo', methods=['POST'])
    @login_required
    def ajustes_correo():
        nuevo_correo  = request.form.get('correo', '').strip().lower()
        password_conf = request.form.get('password_conf', '')
        if not nuevo_correo or not password_conf:
            flash('Completa todos los campos.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn    = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
        if not check_password_hash(usuario['password'], password_conf):
            conn.close()
            flash('Contraseña incorrecta.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        existente = conn.execute("SELECT id FROM usuarios WHERE correo = ? AND id != ?",
            (nuevo_correo, session['user_id'])).fetchone()
        if existente:
            conn.close()
            flash('Ese correo ya está en uso.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn.execute("UPDATE usuarios SET correo = ? WHERE id = ?", (nuevo_correo, session['user_id']))
        conn.commit()
        conn.close()
        flash('Correo actualizado correctamente.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ajustes/password', methods=['POST'])
    @login_required
    def ajustes_password():
        password_actual = request.form.get('password_actual', '')
        password_nueva  = request.form.get('password_nueva', '')
        password_conf   = request.form.get('password_conf', '')
        if not password_actual or not password_nueva or not password_conf:
            flash('Completa todos los campos.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        if password_nueva != password_conf:
            flash('Las contraseñas no coinciden.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        if len(password_nueva) < 6:
            flash('Mínimo 6 caracteres.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn    = get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (session['user_id'],)).fetchone()
        if not check_password_hash(usuario['password'], password_actual):
            conn.close()
            flash('Contraseña actual incorrecta.', 'error')
            return redirect(url_for('ajustes.ajustes'))
        conn.execute("UPDATE usuarios SET password = ? WHERE id = ?",
            (generate_password_hash(password_nueva), session['user_id']))
        conn.commit()
        conn.close()
        flash('Contraseña actualizada.', 'success')
        return redirect(url_for('ajustes.ajustes'))

    @blueprint.route('/ayuda')
    @login_required
    def ayuda():
        return render_template('ajustes/ayuda.html', pagina_activa='ayuda')

    return blueprint
