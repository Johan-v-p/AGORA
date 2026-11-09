"""Rutas de foros, preguntas y respuestas."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import foros as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de foros."""
    blueprint = Blueprint('foros', __name__)

    @blueprint.route('/foros')
    @login_required
    def foros():
        conn = get_db()
        foros_lista = servicio.listar_foros(conn)
        conn.close()
        return render_template('foros/lista.html', foros=foros_lista)

    @blueprint.route('/foros/<int:foro_id>')
    @login_required
    def foro_detalle(foro_id):
        conn = get_db()
        foro = servicio.obtener_foro(conn, foro_id)
        if not foro:
            conn.close()
            flash('Foro no encontrado.', 'error')
            return redirect(url_for('foros.foros'))

        preguntas = servicio.listar_preguntas(conn, foro_id)
        conn.close()
        return render_template('foros/detalle.html', foro=dict(foro), preguntas=preguntas)

    @blueprint.route('/foros/<int:foro_id>/nueva', methods=['POST'])
    @login_required
    def foro_nueva_pregunta(foro_id):
        titulo = request.form.get('titulo', '').strip()
        contenido = request.form.get('contenido', '').strip()
        tipo = request.form.get('tipo', 'pregunta').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') else 0

        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('foros.foro_detalle', foro_id=foro_id))

        if tipo not in servicio.TIPOS_PREGUNTA:
            tipo = 'pregunta'

        conn = get_db()
        try:
            servicio.crear_pregunta(conn, foro_id, session['user_id'], titulo, contenido, tipo, es_anonimo)
            flash('Pregunta publicada.', 'success')
        except Exception as e:
            flash(f'Error al publicar: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('foros.foro_detalle', foro_id=foro_id))

    @blueprint.route('/foros/<int:foro_id>/pregunta/<int:pregunta_id>')
    @login_required
    def foro_pregunta(foro_id, pregunta_id):
        conn = get_db()
        foro = servicio.obtener_foro(conn, foro_id)
        if not foro:
            conn.close()
            flash('Foro no encontrado.', 'error')
            return redirect(url_for('foros.foros'))

        pregunta = servicio.obtener_pregunta(conn, pregunta_id, foro_id)
        if not pregunta:
            conn.close()
            flash('Pregunta no encontrada.', 'error')
            return redirect(url_for('foros.foro_detalle', foro_id=foro_id))

        respuestas = servicio.listar_respuestas(conn, pregunta_id, session['user_id'])
        conn.close()

        return render_template('foros/pregunta.html',
                               foro=dict(foro),
                               pregunta=pregunta,
                               respuestas=respuestas,
                               es_autor_pregunta=(pregunta.get('autor_id') == session['user_id']))

    @blueprint.route('/foros/<int:foro_id>/pregunta/<int:pregunta_id>/responder', methods=['POST'])
    @login_required
    def nueva_respuesta(foro_id, pregunta_id):
        contenido = request.form.get('contenido', '').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') else 0

        if not contenido:
            flash('La respuesta no puede estar vacía.', 'error')
            return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

        if len(contenido) > 2000:
            flash('La respuesta no puede superar 2000 caracteres.', 'error')
            return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

        conn = get_db()
        try:
            servicio.crear_respuesta(conn, pregunta_id, session['user_id'], contenido, es_anonimo)
            flash('Respuesta publicada.', 'success')
        except Exception as e:
            flash(f'Error al responder: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

    @blueprint.route('/foros/pregunta/<int:pregunta_id>/aceptar/<int:respuesta_id>', methods=['POST'])
    @login_required
    def aceptar_respuesta(pregunta_id, respuesta_id):
        conn = get_db()
        try:
            pregunta = servicio.obtener_autoria_pregunta(conn, pregunta_id)
            if not pregunta or pregunta['autor_id'] != session['user_id']:
                flash('Sin permiso.', 'error')
                return redirect(url_for('foros.foros'))

            servicio.aceptar_respuesta(conn, pregunta_id, respuesta_id)
            flash('Respuesta marcada como correcta.', 'success')
            foro_id = pregunta['foro_id']
        except Exception as e:
            flash(f'Error: {e}', 'error')
            foro_id = 0
        finally:
            conn.close()

        return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

    @blueprint.route('/foros/respuesta/<int:respuesta_id>/votar', methods=['POST'])
    @login_required
    def votar_respuesta(respuesta_id):
        data = request.get_json(silent=True) or {}
        valor = data.get('valor', 1)
        if valor not in (1, -1):
            return jsonify({'ok': False}), 400

        conn = get_db()
        try:
            total, mi_voto = servicio.votar_respuesta(conn, respuesta_id, session['user_id'], valor)
            return jsonify({'ok': True, 'total': total, 'mi_voto': mi_voto})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    return blueprint
