"""Decoradores de control de acceso compartidos por los Blueprints."""

from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(vista):
    """Redirige al inicio de sesión si no hay una sesión activa."""
    @wraps(vista)
    def decorada(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('autenticacion.login'))
        return vista(*args, **kwargs)
    return decorada


def crear_moderador_required(get_db):
    """Crea el decorador que limita una vista a moderadores y administradores."""
    def moderador_required(vista):
        @wraps(vista)
        def decorada(*args, **kwargs):
            if not session.get('user_id'):
                return redirect(url_for('autenticacion.login'))
            conn = get_db()
            usuario = conn.execute(
                "SELECT rol FROM usuarios WHERE id = ?", (session['user_id'],)
            ).fetchone()
            conn.close()
            if not usuario or usuario['rol'] not in ('moderador', 'admin'):
                flash('No tienes permisos para acceder a esta sección.', 'error')
                return redirect(url_for('feed'))
            return vista(*args, **kwargs)
        return decorada
    return moderador_required
