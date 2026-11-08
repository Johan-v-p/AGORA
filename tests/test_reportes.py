"""
Pruebas del issue #4: la moderación actúa sobre el usuario correcto.
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Usan una base de datos temporal; no tocan agora.db.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as agora  # noqa: E402

# Los ids coinciden a propósito: la publicación 3 y el comentario 3 son de AUTOR (id 4),
# mientras que el usuario con id 3 es TESTIGO, que no tiene nada que ver.
ADMIN, MODERADOR, TESTIGO, AUTOR, OTRO_ADMIN, OTRO_MODERADOR = 1, 2, 3, 4, 5, 6
PUBLICACION, COMENTARIO = 3, 3

ESQUEMA = """
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL DEFAULT 'x', carrera TEXT DEFAULT 'S', universidad TEXT DEFAULT 'U',
    bio TEXT, avatar_url TEXT, rol TEXT NOT NULL DEFAULT 'estudiante',
    activo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE publicaciones (
    id INTEGER PRIMARY KEY, autor_id INTEGER NOT NULL, titulo TEXT NOT NULL,
    contenido TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'publicado'
);
CREATE TABLE comentarios (
    id INTEGER PRIMARY KEY, publicacion_id INTEGER NOT NULL,
    autor_id INTEGER NOT NULL, contenido TEXT NOT NULL
);
CREATE TABLE reportes (
    id INTEGER PRIMARY KEY AUTOINCREMENT, reportado_por INTEGER NOT NULL, tipo TEXT NOT NULL,
    referencia_id INTEGER NOT NULL, motivo TEXT NOT NULL, descripcion TEXT,
    estado TEXT NOT NULL DEFAULT 'enviado', revisado_por INTEGER, resolucion TEXT,
    creado_en DATETIME DEFAULT CURRENT_TIMESTAMP, resuelto_en DATETIME
);
CREATE TABLE eventos (id INTEGER PRIMARY KEY, fecha DATE NOT NULL);
"""

USUARIOS = [
    (ADMIN, 'Admin', 'admin'),
    (MODERADOR, 'Mod', 'moderador'),
    (TESTIGO, 'Testigo', 'estudiante'),
    (AUTOR, 'Autor', 'estudiante'),
    (OTRO_ADMIN, 'Admin 2', 'admin'),
    (OTRO_MODERADOR, 'Mod 2', 'moderador'),
]


class ModeracionBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = agora.DB
        agora.DB = os.path.join(self.tmp.name, 'test.db')
        agora.app.config['TESTING'] = True

        conn = sqlite3.connect(agora.DB)
        conn.executescript(ESQUEMA)
        conn.executemany(
            "INSERT INTO usuarios (id, nombre, correo, rol) VALUES (?, ?, ?, ?)",
            [(i, n, f'{i}@test.edu', r) for i, n, r in USUARIOS],
        )
        conn.execute(
            "INSERT INTO publicaciones (id, autor_id, titulo, contenido) VALUES (?, ?, 't', 'c')",
            (PUBLICACION, AUTOR),
        )
        conn.execute(
            "INSERT INTO comentarios (id, publicacion_id, autor_id, contenido) VALUES (?, ?, ?, 'c')",
            (COMENTARIO, PUBLICACION, AUTOR),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        agora.DB = self.db_original
        self.tmp.cleanup()

    def cliente(self, user_id):
        client = agora.app.test_client()
        conn = agora.get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        with client.session_transaction() as s:
            s.update(user_id=usuario['id'], nombre=usuario['nombre'], carrera=usuario['carrera'],
                     universidad=usuario['universidad'], rol=usuario['rol'])
        return client

    def consulta(self, sql, *params):
        conn = agora.get_db()
        fila = conn.execute(sql, params).fetchone()
        conn.close()
        return fila

    def ejecutar(self, sql, *params):
        conn = agora.get_db()
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    def crear_reporte(self, tipo, referencia, estado='enviado'):
        conn = agora.get_db()
        cur = conn.execute(
            "INSERT INTO reportes (reportado_por, tipo, referencia_id, motivo, estado) VALUES (?, ?, ?, 'm', ?)",
            (TESTIGO, tipo, referencia, estado),
        )
        conn.commit()
        reporte_id = cur.lastrowid
        conn.close()
        return reporte_id

    def resolver(self, actor, reporte_id, accion='suspender'):
        return self.cliente(actor).post(
            f'/moderacion/resolver/{reporte_id}', data={'accion': accion}, follow_redirects=True,
        )

    def activo(self, user_id):
        return self.consulta("SELECT activo FROM usuarios WHERE id = ?", user_id)['activo']

    def estado_reporte(self, reporte_id):
        return self.consulta("SELECT estado FROM reportes WHERE id = ?", reporte_id)['estado']


class SuspenderUsuarioCorrecto(ModeracionBase):
    def test_reporte_de_publicacion_suspende_a_su_autor(self):
        reporte = self.crear_reporte('publicacion', PUBLICACION)
        self.resolver(MODERADOR, reporte)
        self.assertEqual(self.activo(AUTOR), 0)
        self.assertEqual(self.activo(TESTIGO), 1)
        self.assertEqual(self.estado_reporte(reporte), 'resuelto')

    def test_reporte_de_comentario_suspende_a_su_autor(self):
        reporte = self.crear_reporte('comentario', COMENTARIO)
        self.resolver(MODERADOR, reporte)
        self.assertEqual(self.activo(AUTOR), 0)
        self.assertEqual(self.activo(TESTIGO), 1)

    def test_reporte_de_usuario_suspende_a_ese_usuario(self):
        reporte = self.crear_reporte('usuario', TESTIGO)
        self.resolver(MODERADOR, reporte)
        self.assertEqual(self.activo(TESTIGO), 0)
        self.assertEqual(self.activo(AUTOR), 1)

    def test_publicacion_ya_eliminada_conserva_su_autor(self):
        self.ejecutar("UPDATE publicaciones SET estado = 'eliminado' WHERE id = ?", PUBLICACION)
        self.resolver(MODERADOR, self.crear_reporte('publicacion', PUBLICACION))
        self.assertEqual(self.activo(AUTOR), 0)

    def test_autor_suspendido_pierde_su_sesion_abierta(self):
        autor = self.cliente(AUTOR)
        self.resolver(MODERADOR, self.crear_reporte('publicacion', PUBLICACION))
        respuesta = autor.get('/ajustes')
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/login'))


class PermisosDeSuspension(ModeracionBase):
    def assert_bloqueada(self, actor, objetivo, mensaje):
        reporte = self.crear_reporte('usuario', objetivo)
        html = self.resolver(actor, reporte).get_data(as_text=True)
        self.assertEqual(self.activo(objetivo), 1)
        self.assertEqual(self.estado_reporte(reporte), 'enviado')
        self.assertIn(mensaje, html)

    def test_moderador_no_suspende_a_admin(self):
        self.assert_bloqueada(MODERADOR, ADMIN, 'Solo un administrador')

    def test_moderador_no_suspende_a_otro_moderador(self):
        self.assert_bloqueada(MODERADOR, OTRO_MODERADOR, 'Solo un administrador')

    def test_moderador_no_se_suspende_a_si_mismo(self):
        self.assert_bloqueada(MODERADOR, MODERADOR, 'tu propia cuenta')

    def test_admin_no_se_suspende_a_si_mismo(self):
        self.assert_bloqueada(ADMIN, ADMIN, 'tu propia cuenta')

    def test_autor_protegido_tambien_por_su_contenido(self):
        self.ejecutar("UPDATE publicaciones SET autor_id = ? WHERE id = ?", ADMIN, PUBLICACION)
        reporte = self.crear_reporte('publicacion', PUBLICACION)
        self.resolver(MODERADOR, reporte)
        self.assertEqual(self.activo(ADMIN), 1)
        self.assertEqual(self.estado_reporte(reporte), 'enviado')

    def test_admin_si_suspende_a_moderador(self):
        reporte = self.crear_reporte('usuario', MODERADOR)
        self.resolver(ADMIN, reporte)
        self.assertEqual(self.activo(MODERADOR), 0)
        self.assertEqual(self.estado_reporte(reporte), 'resuelto')

    def test_rol_viejo_en_la_sesion_no_da_permisos(self):
        moderador = self.cliente(MODERADOR)
        with moderador.session_transaction() as s:
            s['rol'] = 'admin'
        reporte = self.crear_reporte('usuario', OTRO_MODERADOR)
        moderador.post(f'/moderacion/resolver/{reporte}', data={'accion': 'suspender'})
        self.assertEqual(self.activo(OTRO_MODERADOR), 1)

    def test_estudiante_no_puede_resolver(self):
        reporte = self.crear_reporte('usuario', TESTIGO)
        respuesta = self.cliente(AUTOR).post(f'/moderacion/resolver/{reporte}', data={'accion': 'suspender'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self.activo(TESTIGO), 1)
        self.assertEqual(self.estado_reporte(reporte), 'enviado')


class CasosLimite(ModeracionBase):
    def test_comentario_borrado_no_suspende_a_nadie(self):
        reporte = self.crear_reporte('comentario', COMENTARIO)
        self.ejecutar("DELETE FROM comentarios WHERE id = ?", COMENTARIO)
        html = self.resolver(MODERADOR, reporte).get_data(as_text=True)
        self.assertIn('ya no existe', html)
        self.assertEqual(self.activo(AUTOR), 1)
        self.assertEqual(self.activo(TESTIGO), 1)
        self.assertEqual(self.estado_reporte(reporte), 'enviado')

    def test_reporte_con_contenido_borrado_se_puede_ignorar(self):
        reporte = self.crear_reporte('comentario', COMENTARIO)
        self.ejecutar("DELETE FROM comentarios WHERE id = ?", COMENTARIO)
        self.resolver(MODERADOR, reporte, accion='ignorar')
        self.assertEqual(self.estado_reporte(reporte), 'resuelto')

    def test_reporte_cerrado_no_se_vuelve_a_aplicar(self):
        reporte = self.crear_reporte('usuario', TESTIGO, estado='resuelto')
        self.resolver(MODERADOR, reporte)
        self.assertEqual(self.activo(TESTIGO), 1)

    def test_accion_desconocida_no_cierra_el_reporte(self):
        reporte = self.crear_reporte('usuario', TESTIGO)
        self.resolver(MODERADOR, reporte, accion='banear')
        self.assertEqual(self.estado_reporte(reporte), 'enviado')

    def test_eliminar_publicacion_reportada(self):
        reporte = self.crear_reporte('publicacion', PUBLICACION)
        self.resolver(MODERADOR, reporte, accion='eliminar')
        fila = self.consulta("SELECT estado FROM publicaciones WHERE id = ?", PUBLICACION)
        self.assertEqual(fila['estado'], 'eliminado')
        self.assertEqual(self.activo(AUTOR), 1)
        self.assertEqual(self.estado_reporte(reporte), 'resuelto')

    def test_eliminar_comentario_reportado(self):
        self.resolver(MODERADOR, self.crear_reporte('comentario', COMENTARIO), accion='eliminar')
        self.assertIsNone(self.consulta("SELECT id FROM comentarios WHERE id = ?", COMENTARIO))

    def test_eliminar_no_aplica_a_reporte_de_usuario(self):
        reporte = self.crear_reporte('usuario', TESTIGO)
        self.resolver(MODERADOR, reporte, accion='eliminar')
        self.assertEqual(self.estado_reporte(reporte), 'enviado')


class CrearReporte(ModeracionBase):
    def enviar(self, tipo, contenido_id, motivo='spam'):
        return self.cliente(TESTIGO).post(
            '/reporte/nuevo', data={'tipo': tipo, 'contenido_id': contenido_id, 'motivo': motivo},
        )

    def test_tipos_validos(self):
        for tipo, referencia in (('publicacion', PUBLICACION), ('comentario', COMENTARIO), ('usuario', AUTOR)):
            with self.subTest(tipo=tipo):
                respuesta = self.enviar(tipo, referencia)
                self.assertEqual(respuesta.status_code, 200)
                self.assertTrue(respuesta.get_json()['ok'])

    def test_tipo_no_valido(self):
        for tipo in ('post', 'foro', ''):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.enviar(tipo, PUBLICACION).status_code, 400)
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM reportes")['n'], 0)

    def test_contenido_inexistente(self):
        for tipo in ('publicacion', 'comentario', 'usuario'):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.enviar(tipo, 999).status_code, 404)
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM reportes")['n'], 0)

    def test_no_permite_duplicar_un_reporte_abierto(self):
        self.enviar('publicacion', PUBLICACION)
        self.assertFalse(self.enviar('publicacion', PUBLICACION).get_json()['ok'])
        self.assertEqual(self.consulta("SELECT COUNT(*) AS n FROM reportes")['n'], 1)


class PantallaDeModeracion(ModeracionBase):
    def html(self):
        return self.cliente(MODERADOR).get('/moderacion').get_data(as_text=True)

    def test_muestra_reportes_abiertos_y_oculta_cerrados(self):
        self.crear_reporte('publicacion', PUBLICACION, estado='enviado')
        self.crear_reporte('comentario', COMENTARIO, estado='en_revision')
        self.crear_reporte('usuario', TESTIGO, estado='resuelto')
        html = self.html()
        self.assertEqual(html.count('class="reporte-card"'), 2)
        self.assertNotIn('Suspender usuario', html)

    def test_botones_de_contenido(self):
        self.crear_reporte('publicacion', PUBLICACION)
        html = self.html()
        self.assertIn('Eliminar contenido', html)
        self.assertIn('Suspender autor', html)

    def test_botones_de_usuario(self):
        self.crear_reporte('usuario', TESTIGO)
        html = self.html()
        self.assertNotIn('Eliminar contenido', html)
        self.assertIn('Suspender usuario', html)


if __name__ == '__main__':
    unittest.main()
