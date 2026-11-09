"""Rutas de inicio de sesión, registro y cierre de sesión."""

import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


def crear_blueprint(get_db):
    """Crea el Blueprint de autenticación con acceso a la base de datos."""
    blueprint = Blueprint('autenticacion', __name__)

    @blueprint.route('/login', methods=['GET', 'POST'])
    def login():
        if session.get('user_id'):
            return redirect(url_for('feed'))

        if request.method == 'POST':
            correo = request.form.get('correo', '').strip().lower()
            password = request.form.get('password', '')

            if not correo or not password:
                flash('Completa todos los campos.', 'error')
                return render_template('auth/login.html')

            conn = get_db()
            usuario = conn.execute(
                "SELECT * FROM usuarios WHERE correo = ?", (correo,)
            ).fetchone()
            conn.close()

            if usuario and check_password_hash(usuario['password'], password):
                if not usuario['activo']:
                    flash(
                        'Tu cuenta está suspendida. Contacta a un administrador.',
                        'error',
                    )
                    return render_template('auth/login.html')

                session.clear()
                session['user_id'] = usuario['id']
                session['nombre'] = usuario['nombre']
                session['carrera'] = usuario['carrera']
                session['universidad'] = usuario['universidad']
                session['rol'] = usuario['rol']
                return redirect(url_for('feed'))
            flash('Correo o contraseña incorrectos.', 'error')

        return render_template('auth/login.html')

    @blueprint.route('/registro', methods=['GET', 'POST'])
    def registro():
        if session.get('user_id'):
            return redirect(url_for('feed'))

        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            correo = request.form.get('correo', '').strip().lower()
            carrera = request.form.get('carrera', '').strip()
            universidad = request.form.get('universidad', '').strip()
            password = request.form.get('password', '')
            confirmar = request.form.get('confirmar', '')

            if not all([nombre, correo, carrera, universidad, password, confirmar]):
                flash('Completa todos los campos.', 'error')
                return render_template('auth/registro.html')

            if password != confirmar:
                flash('Las contraseñas no coinciden.', 'error')
                return render_template('auth/registro.html')

            conn = None
            try:
                conn = get_db()
                conn.execute(
                    """INSERT INTO usuarios
                       (nombre, correo, password, carrera, universidad, rol)
                       VALUES (?, ?, ?, ?, ?, 'estudiante')""",
                    (
                        nombre,
                        correo,
                        generate_password_hash(password),
                        carrera,
                        universidad,
                    ),
                )
                conn.commit()
                flash('¡Cuenta creada! Ya puedes entrar.', 'success')
                return redirect(url_for('autenticacion.login'))
            except sqlite3.IntegrityError:
                flash('Ese correo ya está registrado.', 'error')
                return render_template('auth/registro.html')
            except Exception as error:
                flash(f'Error inesperado: {error}', 'error')
                return render_template('auth/registro.html')
            finally:
                if conn:
                    conn.close()

        return render_template('auth/registro.html')

    @blueprint.route('/logout')
    def logout():
        session.clear()
        flash('Sesión cerrada.', 'success')
        return redirect(url_for('autenticacion.login'))

    return blueprint
