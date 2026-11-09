"""Rutas del portafolio de proyectos."""

import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from backend.rutas.decoradores import login_required
from backend.nucleo.utilidades import parsear_tecnologias


def crear_blueprint(get_db):
    """Crea el Blueprint de portafolio."""
    blueprint = Blueprint('portafolio', __name__)

    @blueprint.route('/portafolio')
    @login_required
    def portafolio():
        user_id = session['user_id']
        conn    = get_db()
        cur     = conn.cursor()

        # Mis proyectos
        cur.execute("""
            SELECT p.*,
                   (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
                   (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
            FROM proyectos p
            WHERE p.autor_id = ?
            ORDER BY p.destacado DESC, p.creado_en DESC
        """, (user_id, user_id))
        mis = []
        for f in cur.fetchall():
            d = dict(f); d['tecnologias_lista'] = parsear_tecnologias(d.get('tecnologias')); mis.append(d)

        # Proyectos de la comunidad (excluye los propios)
        cur.execute("""
            SELECT p.*, u.nombre AS autor_nombre,
                   (SELECT COUNT(*) FROM aplausos_proyecto a WHERE a.proyecto_id = p.id) AS total_aplausos,
                   (SELECT 1 FROM aplausos_proyecto a WHERE a.proyecto_id = p.id AND a.usuario_id = ?) AS yo_aplaudí
            FROM proyectos p JOIN usuarios u ON u.id = p.autor_id
            WHERE p.autor_id != ?
            ORDER BY total_aplausos DESC, p.creado_en DESC
            LIMIT 20
        """, (user_id, user_id))
        todos = []
        for f in cur.fetchall():
            d = dict(f); d['tecnologias_lista'] = parsear_tecnologias(d.get('tecnologias')); todos.append(d)

        conn.close()
        return render_template('portafolio/lista.html', mis_proyectos=mis, todos_proyectos=todos)

    @blueprint.route('/nuevo-proyecto', methods=['POST'])
    @login_required
    def nuevo_proyecto():
        titulo       = request.form.get('titulo', '').strip()
        descripcion  = request.form.get('descripcion', '').strip()
        techs_raw    = request.form.get('tecnologias', '').strip()
        materia      = request.form.get('materia', '').strip()
        estado       = request.form.get('estado', 'en_desarrollo').strip()
        repo_url     = request.form.get('repo_url', '').strip() or None
        demo_url     = request.form.get('demo_url', '').strip() or None

        if not titulo:
            flash('El título es obligatorio.', 'error')
            return redirect(url_for('portafolio.portafolio'))

        if estado not in ('en_desarrollo', 'completado', 'pausado'):
            estado = 'en_desarrollo'

        # Convierte "Flask, Python" → '["Flask","Python"]' para almacenar en JSON
        techs_lista = [t.strip() for t in techs_raw.split(',') if t.strip()]
        tecnologias = json.dumps(techs_lista, ensure_ascii=False) if techs_lista else None

        conn = get_db()
        try:
            conn.execute("""
                INSERT INTO proyectos (autor_id, titulo, descripcion, tecnologias, materia, estado, repo_url, demo_url)
                VALUES (?,?,?,?,?,?,?,?)
            """, (session['user_id'], titulo, descripcion or None, tecnologias, materia or None, estado, repo_url, demo_url))
            conn.commit()
            flash('¡Proyecto publicado!', 'success')
        except Exception as e:
            flash(f'Error al crear proyecto: {e}', 'error')
        finally:
            conn.close()

        return redirect(url_for('portafolio.portafolio'))

    @blueprint.route('/portafolio/<int:proy_id>/aplaudir', methods=['POST'])
    @login_required
    def aplaudir_proyecto(proy_id):
        user_id = session['user_id']
        conn    = get_db()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?",
                (proy_id, user_id)
            )
            if cur.fetchone():
                conn.execute("DELETE FROM aplausos_proyecto WHERE proyecto_id = ? AND usuario_id = ?", (proy_id, user_id))
                activo = False
            else:
                conn.execute("INSERT INTO aplausos_proyecto (proyecto_id, usuario_id) VALUES (?,?)", (proy_id, user_id))
                activo = True
            conn.commit()

            cur.execute("SELECT COUNT(*) AS total FROM aplausos_proyecto WHERE proyecto_id = ?", (proy_id,))
            total = cur.fetchone()['total']
            return jsonify({'ok': True, 'activo': activo, 'total': total})
        except Exception as e:
            return jsonify({'ok': False, 'error': str(e)}), 500
        finally:
            conn.close()

    return blueprint
