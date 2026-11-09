"""Rutas del portafolio de proyectos."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import portafolio as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de portafolio."""
    blueprint = Blueprint('portafolio', __name__)

    @blueprint.route('/portafolio')
    @login_required
    def portafolio():
        user_id = session['user_id']
        conn = get_db()
        mis_proyectos = servicio.listar_propios(conn, user_id)
        todos_proyectos = servicio.listar_comunidad(conn, user_id)
        conn.close()
        return render_template('portafolio/lista.html', mis_proyectos=mis_proyectos, todos_proyectos=todos_proyectos)

    @blueprint.route('/nuevo-proyecto', methods=['POST'])
    @login_required
    def nuevo_proyecto():
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        techs_raw = request.form.get('tecnologias', '').strip()
        materia = request.form.get('materia', '').strip()
        estado = request.form.get('estado', 'en_desarrollo').strip()
        repo_url = request.form.get('repo_url', '').strip() or None
        demo_url = request.form.get('demo_url', '').strip() or None

        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('portafolio.portafolio'))

        if estado not in servicio.ESTADOS:
            estado = 'en_desarrollo'

        tecnologias = servicio.serializar_tecnologias(techs_raw)

        conn = get_db()
        try:
            servicio.crear(conn, session['user_id'], titulo, descripcion or None, tecnologias,
                           materia or None, estado, repo_url, demo_url)
            flash('¡Proyecto publicado!', 'success')
        except Exception as e:
            flash(f'Error al crear proyecto: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('portafolio.portafolio'))

    @blueprint.route('/portafolio/<int:proy_id>/aplaudir', methods=['POST'])
    @login_required
    def aplaudir_proyecto(proy_id):
        conn = get_db()
        try:
            activo, total = servicio.alternar_aplauso(conn, proy_id, session['user_id'])
            return jsonify({'ok': True, 'activo': activo, 'total': total})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    return blueprint
