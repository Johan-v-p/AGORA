"""
Pruebas del issue #3: endpoints que las plantillas usaban y no existían.
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Usan una base de datos temporal creada con scripts/esquema.sql; no tocan agora.db.
"""

import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from backend import aplicacion as agora  # noqa: E402

ADMIN, MODERADOR, ESTUDIANTE, AUTOR = 1, 2, 3, 4


class EndpointsBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = agora.DB
        agora.DB = os.path.join(self.tmp.name, 'test.db')
        conn = sqlite3.connect(agora.DB)
        conn.executescript((RAIZ / 'scripts' / 'esquema.sql').read_text(encoding='utf-8'))
        conn.executemany(
            "INSERT INTO usuarios (id, nombre, correo, password, carrera, rol) VALUES (?, ?, ?, 'x', ?, ?)",
            [
                (ADMIN, 'Admin', 'admin@t', 'Admin', 'admin'),
                (MODERADOR, 'Mod', 'mod@t', 'Sistemas', 'moderador'),
                (ESTUDIANTE, 'Estudiante', 'est@t', 'Sistemas', 'estudiante'),
                (AUTOR, 'Autora Secreta', 'autor@t', 'Diseño', 'estudiante'),
            ],
        )
        conn.execute(
            "INSERT INTO publicaciones (id, autor_id, titulo, contenido, hashtags) VALUES (1, ?, 'Visible', 'x', ?)",
            (AUTOR, json.dumps(['#Python', '#ia'])),
        )
        conn.execute(
            "INSERT INTO publicaciones (id, autor_id, titulo, contenido, es_anonimo, hashtags) "
            "VALUES (2, ?, 'Anónima', 'x', 1, ?)",
            (AUTOR, json.dumps(['#ia'])),
        )
        conn.execute("INSERT INTO comentarios (id, publicacion_id, autor_id, contenido) VALUES (1, 1, ?, 'hola')",
                     (AUTOR,))
        conn.execute("INSERT INTO proyectos (id, autor_id, titulo, repo_url) VALUES (1, ?, 'Robot', 'https://r')",
                     (AUTOR,))
        conn.execute("INSERT INTO foros (id, nombre, categoria) VALUES (1, 'Cálculo', 'matematicas')")
        conn.execute("INSERT INTO preguntas_foro (id, foro_id, autor_id, titulo) VALUES (1, 1, ?, '¿Límite?')",
                     (AUTOR,))
        conn.execute("INSERT INTO respuestas_foro (id, pregunta_id, autor_id, contenido) VALUES (1, 1, ?, 'Sí')",
                     (ADMIN,))
        conn.execute("INSERT INTO votos_respuesta (usuario_id, respuesta_id) VALUES (?, 1)", (AUTOR,))
        conn.commit()
        conn.close()
        agora.app.config['TESTING'] = True
        self.cliente = agora.app.test_client()

    def tearDown(self):
        agora.DB = self.db_original
        self.tmp.cleanup()

    def entrar_como(self, usuario_id):
        with self.cliente.session_transaction() as sesion:
            sesion['user_id'] = usuario_id
            sesion['nombre'] = f'Usuario {usuario_id}'

    def consultar(self, sql, parametros=()):
        conn = sqlite3.connect(agora.DB)
        conn.row_factory = sqlite3.Row
        filas = conn.execute(sql, parametros).fetchall()
        conn.close()
        return filas


class PlantillasTest(unittest.TestCase):
    def test_ningun_url_for_apunta_a_un_endpoint_inexistente(self):
        existentes = {regla.endpoint for regla in agora.app.url_map.iter_rules()}
        faltantes = set()
        for plantilla in (RAIZ / 'frontend' / 'templates').rglob('*.html'):
            texto = plantilla.read_text(encoding='utf-8')
            for endpoint in re.findall(r"url_for\(\s*['\"]([^'\"]+)['\"]", texto):
                if endpoint not in existentes:
                    faltantes.add(f'{plantilla.name}: {endpoint}')
        self.assertEqual(faltantes, set())


class PaginasCarganTest(EndpointsBase):
    def test_paginas_del_issue_cargan_sin_error(self):
        self.entrar_como(ADMIN)
        for url in ('/admin', '/reportes', '/tendencias', '/admin/usuarios', '/admin/foros',
                    '/admin/estadisticas', '/reportar/publicacion?post_id=1',
                    '/reportar/comentario?comentario_id=1', '/reportar/usuario?usuario_id=4',
                    '/tendencias/ia', '/portafolio/1'):
            with self.subTest(url=url):
                self.assertEqual(self.cliente.get(url).status_code, 200)

    def test_panel_muestra_los_contadores(self):
        self.entrar_como(ADMIN)
        html = self.cliente.get('/admin').get_data(as_text=True)
        self.assertIn('Usuarios activos', html)
        self.assertIn('<span class="stat-num">4</span>', html)


class AdministracionTest(EndpointsBase):
    def test_estudiante_y_moderador_no_gestionan_usuarios_ni_foros(self):
        for usuario in (ESTUDIANTE, MODERADOR):
            self.entrar_como(usuario)
            for url in ('/admin/usuarios', '/admin/foros'):
                with self.subTest(usuario=usuario, url=url):
                    respuesta = self.cliente.get(url)
                    self.assertEqual(respuesta.status_code, 302)
                    self.assertTrue(respuesta.headers['Location'].endswith('/feed'))
            self.cliente.post(f'/admin/usuarios/{AUTOR}/rol', data={'rol': 'admin'})
            self.cliente.post(f'/admin/usuarios/{AUTOR}/activo')
        autor = self.consultar("SELECT rol, activo FROM usuarios WHERE id = ?", (AUTOR,))[0]
        self.assertEqual((autor['rol'], autor['activo']), ('estudiante', 1))

    def test_estudiante_no_ve_estadisticas_pero_moderador_si(self):
        self.entrar_como(ESTUDIANTE)
        self.assertEqual(self.cliente.get('/admin/estadisticas').status_code, 302)
        self.entrar_como(MODERADOR)
        self.assertEqual(self.cliente.get('/admin/estadisticas').status_code, 200)

    def test_buscar_usuarios(self):
        self.entrar_como(ADMIN)
        html = self.cliente.get('/admin/usuarios?q=autor@').get_data(as_text=True)
        self.assertIn('Autora Secreta', html)
        self.assertNotIn('est@t', html)

    def test_admin_cambia_rol(self):
        self.entrar_como(ADMIN)
        self.cliente.post(f'/admin/usuarios/{AUTOR}/rol', data={'rol': 'moderador'})
        self.assertEqual(self.consultar("SELECT rol FROM usuarios WHERE id = ?", (AUTOR,))[0]['rol'], 'moderador')

    def test_rol_invalido_o_propio_no_se_cambia(self):
        self.entrar_como(ADMIN)
        self.cliente.post(f'/admin/usuarios/{AUTOR}/rol', data={'rol': 'superusuario'})
        self.cliente.post(f'/admin/usuarios/{ADMIN}/rol', data={'rol': 'estudiante'})
        roles = {f['id']: f['rol'] for f in self.consultar("SELECT id, rol FROM usuarios")}
        self.assertEqual(roles[AUTOR], 'estudiante')
        self.assertEqual(roles[ADMIN], 'admin')

    def test_admin_suspende_y_reactiva(self):
        self.entrar_como(ADMIN)
        self.cliente.post(f'/admin/usuarios/{AUTOR}/activo')
        self.assertEqual(self.consultar("SELECT activo FROM usuarios WHERE id = ?", (AUTOR,))[0]['activo'], 0)
        self.cliente.post(f'/admin/usuarios/{AUTOR}/activo')
        self.assertEqual(self.consultar("SELECT activo FROM usuarios WHERE id = ?", (AUTOR,))[0]['activo'], 1)

    def test_admin_no_se_suspende_a_si_mismo(self):
        self.entrar_como(ADMIN)
        self.cliente.post(f'/admin/usuarios/{ADMIN}/activo')
        self.assertEqual(self.consultar("SELECT activo FROM usuarios WHERE id = ?", (ADMIN,))[0]['activo'], 1)

    def test_crear_foro_y_rechazar_nombre_repetido(self):
        self.entrar_como(ADMIN)
        datos = {'accion': 'crear', 'nombre': 'Redes', 'categoria': 'sistemas', 'descripcion': 'TCP/IP'}
        self.cliente.post('/admin/foros', data=datos)
        self.cliente.post('/admin/foros', data=dict(datos, nombre='redes'))
        foros = self.consultar("SELECT nombre, categoria, creado_por FROM foros WHERE nombre LIKE 'redes'")
        self.assertEqual(len(foros), 1)
        self.assertEqual((foros[0]['categoria'], foros[0]['creado_por']), ('sistemas', ADMIN))

    def test_eliminar_foro_borra_preguntas_respuestas_y_votos(self):
        self.entrar_como(ADMIN)
        self.cliente.post('/admin/foros', data={'accion': 'eliminar', 'foro_id': 1})
        for tabla in ('foros', 'preguntas_foro', 'respuestas_foro', 'votos_respuesta'):
            with self.subTest(tabla=tabla):
                self.assertEqual(self.consultar(f"SELECT COUNT(*) AS n FROM {tabla}")[0]['n'], 0)


class ReportesTest(EndpointsBase):
    def reportar(self, **datos):
        base = {'tipo': 'publicacion', 'referencia_id': 1, 'motivo': 'spam', 'descripcion': 'Es spam'}
        return self.cliente.post('/reportar', data=dict(base, **datos))

    def test_enviar_reporte_guarda_motivo_y_descripcion(self):
        self.entrar_como(ESTUDIANTE)
        respuesta = self.reportar()
        self.assertTrue(respuesta.headers['Location'].endswith('/reportes'))
        reporte = self.consultar("SELECT * FROM reportes")[0]
        self.assertEqual(
            (reporte['reportado_por'], reporte['tipo'], reporte['referencia_id'],
             reporte['motivo'], reporte['descripcion']),
            (ESTUDIANTE, 'publicacion', 1, 'spam', 'Es spam'),
        )

    def test_reportes_invalidos_no_se_guardan(self):
        self.entrar_como(ESTUDIANTE)
        self.reportar(tipo='proyecto')
        self.reportar(motivo='me cae mal')
        self.reportar(referencia_id='')
        self.reportar(referencia_id=999)
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM reportes")[0]['n'], 0)

    def test_no_se_reporta_contenido_propio(self):
        self.entrar_como(AUTOR)
        self.reportar()
        self.reportar(tipo='usuario', referencia_id=AUTOR)
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM reportes")[0]['n'], 0)

    def test_no_se_duplica_un_reporte_abierto(self):
        self.entrar_como(ESTUDIANTE)
        self.reportar()
        self.reportar(motivo='acoso')
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM reportes")[0]['n'], 1)

    def test_formulario_de_publicacion_anonima_no_revela_autor(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/reportar/publicacion?post_id=2').get_data(as_text=True)
        self.assertIn('Anónima', html)
        self.assertNotIn('Autora Secreta', html)

    def test_formulario_sin_id_avisa(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/reportar/usuario').get_data(as_text=True)
        self.assertIn('No se especificó un usuario', html)


class PortafolioTest(EndpointsBase):
    def test_ver_proyecto_muestra_autor_y_repositorio(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/portafolio/1').get_data(as_text=True)
        self.assertIn('Autora Secreta', html)
        self.assertIn('https://r', html)
        self.assertIn(f'/reportar/usuario?usuario_id={AUTOR}', html)

    def test_proyecto_inexistente_redirige(self):
        self.entrar_como(ESTUDIANTE)
        respuesta = self.cliente.get('/portafolio/999')
        self.assertTrue(respuesta.headers['Location'].endswith('/portafolio'))

    def test_comentar_proyecto(self):
        self.entrar_como(ESTUDIANTE)
        respuesta = self.cliente.post('/portafolio/1/comentar', data={'contenido': '  ¡Genial!  '})
        self.assertTrue(respuesta.headers['Location'].endswith('/portafolio/1'))
        comentario = self.consultar("SELECT * FROM comentarios_proyecto")[0]
        self.assertEqual((comentario['autor_id'], comentario['contenido']), (ESTUDIANTE, '¡Genial!'))
        self.assertIn('¡Genial!', self.cliente.get('/portafolio/1').get_data(as_text=True))

    def test_comentario_vacio_o_proyecto_inexistente_no_se_guarda(self):
        self.entrar_como(ESTUDIANTE)
        self.cliente.post('/portafolio/1/comentar', data={'contenido': '   '})
        self.cliente.post('/portafolio/999/comentar', data={'contenido': 'hola'})
        self.assertEqual(self.consultar("SELECT COUNT(*) AS n FROM comentarios_proyecto")[0]['n'], 0)


class TendenciasTest(EndpointsBase):
    def test_tendencias_lista_posts_y_hashtags(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/tendencias').get_data(as_text=True)
        self.assertIn('Visible', html)
        self.assertIn('/tendencias/ia', html)
        self.assertIn('/tendencias/python', html)

    def test_tendencias_oculta_autor_anonimo(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/tendencias/ia').get_data(as_text=True)
        self.assertEqual(html.count('Autora Secreta'), 1)  # solo la publicación firmada
        self.assertIn('Anónimo', html)

    def test_tendencia_tag_filtra_sin_importar_mayusculas_ni_numeral(self):
        self.entrar_como(ESTUDIANTE)
        html = self.cliente.get('/tendencias/PYTHON').get_data(as_text=True)
        self.assertIn('Visible', html)
        self.assertNotIn('Anónima', html)


if __name__ == '__main__':
    unittest.main()
