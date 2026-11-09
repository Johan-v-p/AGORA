"""Rutas de foros, preguntas y respuestas."""

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.nucleo.utilidades import tiempo_relativo


def crear_blueprint(get_db):
    """Crea el Blueprint de foros."""
    blueprint = Blueprint('foros', __name__)

    @blueprint.route('/foros')
    @login_required
    def foros():
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("""
            SELECT f.id, f.nombre, f.descripcion, f.categoria,
                   (SELECT COUNT(*) FROM preguntas_foro pf WHERE pf.foro_id = f.id) AS total_preguntas
            FROM foros f ORDER BY total_preguntas DESC
        """)
        foros_lista = [dict(r) for r in cur.fetchall()]
        conn.close()
        return render_template('foros/lista.html', foros=foros_lista)

    @blueprint.route('/foros/<int:foro_id>')
    @login_required
    def foro_detalle(foro_id):
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT * FROM foros WHERE id = ?", (foro_id,))
        foro = cur.fetchone()
        if not foro:
            conn.close()
            flash('Foro no encontrado.', 'error')
            return redirect(url_for('foros.foros'))

        cur.execute("""
            SELECT pf.id, pf.titulo, pf.contenido, pf.tipo, pf.es_anonimo, pf.creado_en,
                   u.nombre AS autor_nombre,
                   (SELECT COUNT(*) FROM respuestas_foro rf WHERE rf.pregunta_id = pf.id) AS total_respuestas
            FROM preguntas_foro pf
            JOIN usuarios u ON u.id = pf.autor_id
            WHERE pf.foro_id = ? ORDER BY pf.creado_en DESC
        """, (foro_id,))
        filas = cur.fetchall()
        conn.close()

        preguntas = []
        for fila in filas:
            d = dict(fila); d['tiempo_relativo'] = tiempo_relativo(d['creado_en']); preguntas.append(d)

        return render_template('foros/detalle.html', foro=dict(foro), preguntas=preguntas)

    @blueprint.route('/foros/<int:foro_id>/nueva', methods=['POST'])
    @login_required
    def foro_nueva_pregunta(foro_id):
        titulo    = request.form.get('titulo', '').strip()
        contenido = request.form.get('contenido', '').strip()
        tipo      = request.form.get('tipo', 'pregunta').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') else 0

        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('foros.foro_detalle', foro_id=foro_id))

        if tipo not in ('pregunta', 'duda', 'apuntes', 'recurso', 'debate'):
            tipo = 'pregunta'

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO preguntas_foro (foro_id, autor_id, titulo, contenido, tipo, es_anonimo)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (foro_id, session['user_id'], titulo, contenido, tipo, es_anonimo))
            conn.commit()
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
        cur  = conn.cursor()

        # Datos del foro
        cur.execute("SELECT * FROM foros WHERE id = ?", (foro_id,))
        foro = cur.fetchone()
        if not foro:
            conn.close()
            flash('Foro no encontrado.', 'error')
            return redirect(url_for('foros.foros'))

        # Datos de la pregunta
        cur.execute("""
            SELECT pf.*, u.nombre AS autor_nombre
            FROM preguntas_foro pf
            JOIN usuarios u ON u.id = pf.autor_id
            WHERE pf.id = ? AND pf.foro_id = ?
        """, (pregunta_id, foro_id))
        pregunta = cur.fetchone()
        if not pregunta:
            conn.close()
            flash('Pregunta no encontrada.', 'error')
            return redirect(url_for('foros.foro_detalle', foro_id=foro_id))

        pregunta = dict(pregunta)
        pregunta['tiempo_relativo'] = tiempo_relativo(pregunta['creado_en'])

        # Respuestas con votos
        cur.execute("""
            SELECT rf.id, rf.contenido, rf.es_anonimo, rf.aceptada, rf.creado_en,
                   rf.autor_id, u.nombre AS autor_nombre,
                   COALESCE((SELECT SUM(v.valor) FROM votos_respuesta v WHERE v.respuesta_id = rf.id), 0) AS votos,
                   (SELECT v.valor FROM votos_respuesta v
                    WHERE v.respuesta_id = rf.id AND v.usuario_id = ?) AS mi_voto
            FROM respuestas_foro rf
            JOIN usuarios u ON u.id = rf.autor_id
            WHERE rf.pregunta_id = ?
            ORDER BY rf.aceptada DESC, votos DESC, rf.creado_en ASC
        """, (session['user_id'], pregunta_id))
        filas = cur.fetchall()
        conn.close()

        respuestas = []
        for f in filas:
            d = dict(f)
            d['tiempo_relativo'] = tiempo_relativo(d['creado_en'])
            d['mi_voto'] = d['mi_voto'] or 0
            respuestas.append(d)

        es_autor_pregunta = (pregunta.get('autor_id') == session['user_id'])

        return render_template('foros/pregunta.html',
                               foro=dict(foro),
                               pregunta=pregunta,
                               respuestas=respuestas,
                               es_autor_pregunta=es_autor_pregunta)

    @blueprint.route('/foros/<int:foro_id>/pregunta/<int:pregunta_id>/responder', methods=['POST'])
    @login_required
    def nueva_respuesta(foro_id, pregunta_id):
        contenido  = request.form.get('contenido', '').strip()
        es_anonimo = 1 if request.form.get('es_anonimo') else 0

        if not contenido:
            flash('La respuesta no puede estar vacía.', 'error')
            return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

        if len(contenido) > 2000:
            flash('La respuesta no puede superar 2000 caracteres.', 'error')
            return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO respuestas_foro (pregunta_id, autor_id, contenido, es_anonimo) VALUES (?,?,?,?)",
                (pregunta_id, session['user_id'], contenido, es_anonimo)
            )
            conn.commit()
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
            cur = conn.cursor()
            # Verificar que el usuario es el autor de la pregunta
            cur.execute("SELECT autor_id, foro_id FROM preguntas_foro WHERE id = ?", (pregunta_id,))
            preg = cur.fetchone()
            if not preg or preg['autor_id'] != session['user_id']:
                flash('Sin permiso.', 'error')
                conn.close()
                return redirect(url_for('foros.foros'))

            # Desmarcar cualquier respuesta aceptada anterior
            conn.execute("UPDATE respuestas_foro SET aceptada = 0 WHERE pregunta_id = ?", (pregunta_id,))
            # Marcar la nueva
            conn.execute("UPDATE respuestas_foro SET aceptada = 1 WHERE id = ? AND pregunta_id = ?",
                         (respuesta_id, pregunta_id))
            conn.commit()
            flash('Respuesta marcada como correcta.', 'success')
            foro_id = preg['foro_id']
        except Exception as e:
            flash(f'Error: {e}', 'error')
            foro_id = 0
        finally:
            conn.close()

        return redirect(url_for('foros.foro_pregunta', foro_id=foro_id, pregunta_id=pregunta_id))

    @blueprint.route('/foros/respuesta/<int:respuesta_id>/votar', methods=['POST'])
    @login_required
    def votar_respuesta(respuesta_id):
        data  = request.get_json(silent=True) or {}
        valor = data.get('valor', 1)
        if valor not in (1, -1):
            return jsonify({'ok': False}), 400

        user_id = session['user_id']
        conn    = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT valor FROM votos_respuesta WHERE respuesta_id = ? AND usuario_id = ?",
                (respuesta_id, user_id)
            )
            existente = cur.fetchone()

            if existente:
                if existente['valor'] == valor:
                    # Mismo voto → quita el voto (toggle)
                    conn.execute(
                        "DELETE FROM votos_respuesta WHERE respuesta_id = ? AND usuario_id = ?",
                        (respuesta_id, user_id)
                    )
                    mi_voto = 0
                else:
                    # Voto opuesto → cambia
                    conn.execute(
                        "UPDATE votos_respuesta SET valor = ? WHERE respuesta_id = ? AND usuario_id = ?",
                        (valor, respuesta_id, user_id)
                    )
                    mi_voto = valor
            else:
                conn.execute(
                    "INSERT INTO votos_respuesta (respuesta_id, usuario_id, valor) VALUES (?,?,?)",
                    (respuesta_id, user_id, valor)
                )
                mi_voto = valor

            conn.commit()

            cur.execute(
                "SELECT COALESCE(SUM(valor), 0) AS total FROM votos_respuesta WHERE respuesta_id = ?",
                (respuesta_id,)
            )
            total = cur.fetchone()['total']
            return jsonify({'ok': True, 'total': total, 'mi_voto': mi_voto})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    return blueprint
