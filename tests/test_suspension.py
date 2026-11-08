"""
Pruebas del issue #5: las cuentas suspendidas no pueden entrar ni seguir usando su sesión.
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Usan una base de datos temporal; no tocan agora.db.
"""

import os
import sqlite3
import sys
import tempfile
import unittest

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as agora  # noqa: E402

MENSAJE_SUSPENDIDA = 'Tu cuenta está suspendida'
MENSAJE_CREDENCIALES = 'Correo o contraseña incorrectos'
CORREO = 'ana@test.edu'
PASSWORD = 'clave-de-prueba'


class SuspensionTest(unittest.TestCase):
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

    def tearDown(self):
        agora.DB = self.db_original
        self.tmp.cleanup()

    def _actualizar(self, columna, valor):
        conn = sqlite3.connect(agora.DB)
        conn.execute(f"UPDATE usuarios SET {columna} = ? WHERE correo = ?", (valor, CORREO))
        conn.commit()
        conn.close()

    def _login(self, password=PASSWORD):
        return self.client.post('/login', data={'correo': CORREO, 'password': password})

    def _user_id_en_sesion(self):
        with self.client.session_transaction() as s:
            return s.get('user_id')

    def test_cuenta_activa_puede_entrar(self):
        respuesta = self._login()
        self.assertEqual(respuesta.status_code, 302)
        self.assertIsNotNone(self._user_id_en_sesion())

    def test_login_rechaza_cuenta_suspendida(self):
        self._actualizar('activo', 0)
        respuesta = self._login()
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(MENSAJE_SUSPENDIDA, respuesta.get_data(as_text=True))
        self.assertIsNone(self._user_id_en_sesion())

    def test_password_incorrecta_no_revela_la_suspension(self):
        self._actualizar('activo', 0)
        html = self._login(password='otra-clave').get_data(as_text=True)
        self.assertIn(MENSAJE_CREDENCIALES, html)
        self.assertNotIn(MENSAJE_SUSPENDIDA, html)

    def test_sesion_abierta_se_expulsa_al_suspender(self):
        self._login()
        self.assertEqual(self.client.get('/ajustes').status_code, 200)

        self._actualizar('activo', 0)
        respuesta = self.client.get('/ajustes')

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.location.endswith('/login'))
        self.assertIsNone(self._user_id_en_sesion())
        self.assertIn(MENSAJE_SUSPENDIDA, self.client.get('/login').get_data(as_text=True))

    def test_sesion_sigue_expulsada_tras_reactivar_sin_nuevo_login(self):
        self._login()
        self._actualizar('activo', 0)
        self.client.get('/ajustes')
        self._actualizar('activo', 1)
        self.assertEqual(self.client.get('/ajustes').status_code, 302)

    def test_rol_de_la_sesion_se_actualiza(self):
        self._login()
        self._actualizar('rol', 'moderador')
        self.client.get('/ajustes')
        with self.client.session_transaction() as s:
            self.assertEqual(s.get('rol'), 'moderador')

    def test_socketio_rechaza_cuenta_suspendida(self):
        self._login()
        self._actualizar('activo', 0)
        socket = agora.socketio.test_client(agora.app, flask_test_client=self.client)
        self.assertFalse(socket.is_connected())

    def test_socketio_acepta_cuenta_activa(self):
        self._login()
        socket = agora.socketio.test_client(agora.app, flask_test_client=self.client)
        self.assertTrue(socket.is_connected())
        socket.disconnect()


if __name__ == '__main__':
    unittest.main()
