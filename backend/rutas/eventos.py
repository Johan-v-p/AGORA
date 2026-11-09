"""Rutas de eventos e inscripciones."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.nucleo.utilidades import procesar_evento


def crear_blueprint(get_db):
    """Crea el Blueprint de eventos."""
    blueprint = Blueprint('eventos', __name__)

    @blueprint.route('/eventos')
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

    @blueprint.route('/nuevo-evento', methods=['POST'])
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
            return redirect(url_for('eventos.eventos'))

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

        return redirect(url_for('eventos.eventos'))

    @blueprint.route('/eventos/<int:evento_id>/inscribir', methods=['POST'])
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

    @blueprint.route('/eventos/<int:evento_id>')
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
            return redirect(url_for('eventos.eventos'))

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

    @blueprint.route('/eventos/<int:evento_id>/editar', methods=['GET', 'POST'])
    @login_required
    def editar_evento(evento_id):
        """Editar un evento (solo el creador)."""
        user_id = session['user_id']
        conn    = get_db()
        evento  = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        if evento['creador_id'] != user_id:
            conn.close()
            flash('No tienes permiso para editar este evento.', 'error')
            return redirect(url_for('eventos.ver_evento', evento_id=evento_id))

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
        conn    = get_db()
        evento  = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

        # Verificar permiso: creador o moderador/admin
        usuario = conn.execute("SELECT rol FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        es_mod  = usuario and usuario['rol'] in ('admin', 'moderador')

        if evento['creador_id'] != user_id and not es_mod:
            conn.close()
            flash('No tienes permiso para eliminar este evento.', 'error')
            return redirect(url_for('eventos.ver_evento', evento_id=evento_id))

        # Eliminar inscripciones primero, luego el evento
        conn.execute("DELETE FROM inscripciones_evento WHERE evento_id = ?", (evento_id,))
        conn.execute("DELETE FROM eventos WHERE id = ?", (evento_id,))
        conn.commit()
        conn.close()

        flash('Evento eliminado.', 'success')
        return redirect(url_for('eventos.eventos'))

    @blueprint.route('/eventos/<int:evento_id>/participantes')
    @login_required
    def ver_participantes(evento_id):
        """Lista de usuarios inscritos en un evento."""
        conn   = get_db()
        evento = conn.execute("SELECT * FROM eventos WHERE id = ?", (evento_id,)).fetchone()

        if not evento:
            conn.close()
            flash('Evento no encontrado.', 'error')
            return redirect(url_for('eventos.eventos'))

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

    return blueprint
