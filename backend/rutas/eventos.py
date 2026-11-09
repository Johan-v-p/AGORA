"""Rutas de eventos e inscripciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.servicios import cuentas
from backend.servicios import eventos as servicio


def crear_blueprint(get_db):
    """Crea el Blueprint de eventos."""
    blueprint = Blueprint('eventos', __name__)

    @blueprint.route('/eventos')
    @login_required
    def eventos():
        cat_activa = request.args.get('cat', 'todos')
        conn = get_db()
        eventos_lista = servicio.listar_proximos(conn, session['user_id'], cat_activa)
        conn.close()
        return render_template('eventos/lista.html', eventos=eventos_lista, cat_activa=cat_activa)

    @blueprint.route('/nuevo-evento', methods=['POST'])
    @login_required
    def nuevo_evento():
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        categoria = request.form.get('categoria', 'academico').strip()
        fecha = request.form.get('fecha', '').strip()
        hora_inicio = request.form.get('hora_inicio', '').strip() or None
        hora_fin = request.form.get('hora_fin', '').strip() or None
        lugar = request.form.get('lugar', '').strip() or None
        cupos_raw = request.form.get('cupos', '').strip()
        organizador = request.form.get('organizador', '').strip() or None

        if not titulo or not fecha:
            flash('El título y la fecha son obligatorios.', 'error')
            return redirect(url_for('eventos.eventos'))

        if categoria not in servicio.CATEGORIAS:
            categoria = 'academico'

        cupos = int(cupos_raw) if cupos_raw.isdigit() else None

        conn = get_db()
        try:
            servicio.crear(conn, session['user_id'], titulo, descripcion or None, categoria, fecha,
                           hora_inicio, hora_fin, lugar, cupos, organizador)
            flash('¡Evento publicado!', 'success')
        except Exception as e:
            flash(f'Error al crear evento: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('eventos.eventos'))

    @blueprint.route('/eventos/<int:evento_id>/inscribir', methods=['POST'])
    @login_required
    def inscribir_evento(evento_id):
        conn = get_db()
        try:
            evento = servicio.obtener_cupos(conn, evento_id)
            if not evento:
                return jsonify({'ok': False, 'error': 'Evento no encontrado'}), 404

            inscrito = servicio.alternar_inscripcion(conn, evento_id, session['user_id'], evento['cupos'])
            if inscrito is None:
                return jsonify({'ok': False, 'error': 'Sin cupos disponibles'}), 400

            cupos_libres = servicio.calcular_cupos_libres(conn, evento_id, evento['cupos'])
            return jsonify({'ok': True, 'inscrito': inscrito, 'cupos_libres': cupos_libres})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    @blueprint.route('/eventos/<int:evento_id>')
    @login_required
    def ver_evento(evento_id):
        """Detalle completo de un evento con participantes."""
        user_id = session['user_id']
        conn = get_db()
        evento = servicio.obtener_detalle(conn, evento_id, user_id)

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        participantes = servicio.listar_participantes_resumen(conn, evento_id)
        conn.close()

        return render_template('eventos/ver_evento.html',
                               evento=evento,
                               participantes=participantes,
                               es_creador=(evento['creador_id'] == user_id),
                               pagina_activa='eventos')

    @blueprint.route('/eventos/<int:evento_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_evento(evento_id):
        """Editar un evento (solo el creador)."""
        conn = get_db()
        evento = servicio.obtener(conn, evento_id)

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        if evento['creador_id'] != session['user_id']:
            conn.close()
            flash('No tienes permiso para editar este evento.', 'error')
            return redirect(url_for('eventos.ver_evento', evento_id=evento_id))

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            categoria = request.form.get('categoria', 'academico')
            fecha = request.form.get('fecha', '').strip()
            hora_inicio = request.form.get('hora_inicio', '').strip() or None
            hora_fin = request.form.get('hora_fin', '').strip() or None
            lugar = request.form.get('lugar', '').strip() or None
            organizador = request.form.get('organizador', '').strip() or None
            cupos_raw = request.form.get('cupos', '').strip()
            cupos = int(cupos_raw) if cupos_raw.isdigit() else None

            if not titulo or not fecha:
                flash('El título y la fecha son obligatorios.', 'error')
                return render_template('eventos/editar_evento.html', evento=dict(evento),
                                       pagina_activa='eventos')

            servicio.actualizar(conn, evento_id, titulo, descripcion or None, categoria, fecha,
                                hora_inicio, hora_fin, lugar, organizador, cupos)
            conn.close()
            flash('Evento actualizado correctamente.', 'success')
            return redirect(url_for('eventos.ver_evento', evento_id=evento_id))

        conn.close()
        return render_template('eventos/editar_evento.html',
                               evento=dict(evento),
                               pagina_activa='eventos')

    @blueprint.route('/eventos/<int:evento_id>/eliminar', methods=['POST'])
    @login_required
    def eliminar_evento(evento_id):
        """Eliminar un evento (solo el creador o admin/moderador)."""
        user_id = session['user_id']
        conn = get_db()
        evento = servicio.obtener(conn, evento_id)

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        usuario = cuentas.obtener_rol(conn, user_id)
        es_mod = usuario and usuario['rol'] in ('admin', 'moderador')

        if evento['creador_id'] != user_id and not es_mod:
            conn.close()
            flash('No tienes permiso para eliminar este evento.', 'error')
            return redirect(url_for('eventos.ver_evento', evento_id=evento_id))

        servicio.eliminar(conn, evento_id)
        conn.close()

        flash('Evento eliminado.', 'success')
        return redirect(url_for('eventos.eventos'))

    @blueprint.route('/eventos/<int:evento_id>/participantes')
    @login_required
    def ver_participantes(evento_id):
        """Lista de usuarios inscritos en un evento."""
        conn = get_db()
        evento = servicio.obtener(conn, evento_id)

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        participantes = servicio.listar_participantes(conn, evento_id)
        conn.close()
        return render_template('eventos/ver_participantes.html',
                               evento=dict(evento),
                               participantes=participantes,
                               pagina_activa='eventos')

    return blueprint
