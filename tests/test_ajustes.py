"""
Pruebas de los ajustes de cuenta que exigen confirmar la contraseña.
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Usan una base de datos temporal; no tocan agora.db.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

from werkzeug.security import check_password_hash, generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import aplicacion as agora  # noqa: E402

CORREO = 'ana@test.edu'
PASSWORD = 'clave-de-prueba'


class AjustesCuentaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = agora.DB
        agora.DB = os.path.join(self.tmp.name, 'test.db')
        agora.app.config['TESTING'] = True

        conn = sqlite3.connect(agora.DB)
        conn.execute("""
            CREATE TABLE usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE, password TEXT NOT NULL,
                carrera TEXT, universidad TEXT, bio TEXT, avatar_url TEXT,
                rol TEXT NOT NULL DEFAULT 'estudiante',
                activo INTEGER NOT NULL DEFAULT 1
            )
        """)
        conn.execute(
            "INSERT INTO usuarios (nombre, correo, password, carrera, universidad) VALUES (?,?,?,?,?)",
            ('Ana', CORREO, generate_password_hash(PASSWORD), 'Sistemas', 'Univalle'),
        )
        conn.commit()
        conn.close()

        self.client = agora.app.test_client()
        self.client.post('/login', data={'correo': CORREO, 'password': PASSWORD})

    def tearDown(self):
        agora.DB = self.db_original
        self.tmp.cleanup()

    def _usuario(self):
        conn = agora.get_db()
        usuario = conn.execute("SELECT * FROM usuarios WHERE id = 1").fetchone()
        conn.close()
        return usuario

    def test_cambia_el_correo_con_la_contrasena_correcta(self):
        respuesta = self.client.post(
            '/ajustes/correo',
            data={'correo': 'nueva@test.edu', 'password_conf': PASSWORD},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self._usuario()['correo'], 'nueva@test.edu')

    def test_no_cambia_el_correo_con_contrasena_incorrecta(self):
        self.client.post(
            '/ajustes/correo',
            data={'correo': 'nueva@test.edu', 'password_conf': 'otra-clave'},
        )
        self.assertEqual(self._usuario()['correo'], CORREO)

    def test_cambia_la_contrasena(self):
        respuesta = self.client.post(
            '/ajustes/password',
            data={
                'password_actual': PASSWORD,
                'password_nueva': 'clave-nueva',
                'password_conf': 'clave-nueva',
            },
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(check_password_hash(self._usuario()['password'], 'clave-nueva'))

    def test_guarda_la_preferencia_de_tema(self):
        respuesta = self.client.post('/ajustes/tema', data={'tema': 'light'})
        self.assertEqual(respuesta.status_code, 204)
        self.assertEqual(self._usuario()['tema'], 'light')

    def test_rechaza_una_preferencia_de_tema_invalida(self):
        respuesta = self.client.post('/ajustes/tema', data={'tema': 'blue'})
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(self._usuario()['tema'], 'system')


if __name__ == '__main__':
    unittest.main()
