"""
Pruebas de la foto de perfil en /ajustes/perfil.
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Usan una base de datos y una carpeta de subidas temporales; no tocan data/ ni frontend/static.
"""

import io
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend import aplicacion as agora  # noqa: E402
from backend.nucleo import imagenes  # noqa: E402

CORREO = 'ana@test.edu'
PASSWORD = 'clave-de-prueba'


def png(ancho=300, alto=200):
    """Devuelve un flujo en memoria con una imagen PNG válida."""
    buffer = io.BytesIO()
    Image.new('RGB', (ancho, alto), (30, 120, 200)).save(buffer, 'PNG')
    buffer.seek(0)
    return buffer


class FotoPerfilTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = agora.DB
        self.subidas_original = imagenes.DIRECTORIO_SUBIDAS
        agora.DB = os.path.join(self.tmp.name, 'test.db')
        imagenes.DIRECTORIO_SUBIDAS = Path(self.tmp.name) / 'static' / 'uploads'
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
            "INSERT INTO usuarios (nombre, correo, password) VALUES (?,?,?)",
            ('Ana', CORREO, generate_password_hash(PASSWORD)),
        )
        conn.commit()
        conn.close()

        self.client = agora.app.test_client()
        self.client.post('/login', data={'correo': CORREO, 'password': PASSWORD})

    def tearDown(self):
        agora.DB = self.db_original
        imagenes.DIRECTORIO_SUBIDAS = self.subidas_original
        self.tmp.cleanup()

    def _avatar(self):
        conn = agora.get_db()
        fila = conn.execute("SELECT avatar_url FROM usuarios WHERE id = 1").fetchone()
        conn.close()
        return fila['avatar_url']

    def _existe(self, ruta):
        return (imagenes.DIRECTORIO_SUBIDAS.parent / ruta).exists()

    def _guardar_perfil(self, archivo=None, **extra):
        datos = {'nombre': 'Ana'}
        datos.update(extra)
        if archivo is not None:
            datos['avatar'] = (archivo, 'foto.png')
        return self.client.post('/ajustes/perfil', data=datos, content_type='multipart/form-data')

    def test_sube_la_foto_y_crea_la_miniatura(self):
        respuesta = self._guardar_perfil(png())
        self.assertEqual(respuesta.status_code, 302)
        ruta = self._avatar()
        self.assertTrue(ruta.startswith('uploads/avatares/'))
        self.assertTrue(self._existe(ruta))
        self.assertTrue(self._existe(imagenes.ruta_miniatura(ruta)))

    def test_la_pagina_de_ajustes_muestra_la_foto(self):
        self._guardar_perfil(png())
        respuesta = self.client.get('/ajustes')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b'/static/uploads/avatares/', respuesta.data)

    def test_reemplazar_la_foto_borra_la_anterior(self):
        self._guardar_perfil(png())
        primera = self._avatar()
        self._guardar_perfil(png(400, 400))
        segunda = self._avatar()
        self.assertNotEqual(primera, segunda)
        self.assertFalse(self._existe(primera))
        self.assertFalse(self._existe(imagenes.ruta_miniatura(primera)))
        self.assertTrue(self._existe(segunda))

    def test_guardar_sin_archivo_conserva_la_foto(self):
        self._guardar_perfil(png())
        ruta = self._avatar()
        self._guardar_perfil()
        self.assertEqual(self._avatar(), ruta)
        self.assertTrue(self._existe(ruta))

    def test_quitar_la_foto_borra_los_archivos(self):
        self._guardar_perfil(png())
        ruta = self._avatar()
        self._guardar_perfil(quitar_avatar='1')
        self.assertIsNone(self._avatar())
        self.assertFalse(self._existe(ruta))
        self.assertFalse(self._existe(imagenes.ruta_miniatura(ruta)))

    def test_rechaza_un_archivo_que_no_es_imagen(self):
        falso = io.BytesIO(b'<?php system($_GET[0]); ?>')
        respuesta = self._guardar_perfil(falso)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIsNone(self._avatar())
        carpeta = imagenes.DIRECTORIO_SUBIDAS / 'avatares'
        self.assertFalse(carpeta.exists() and any(carpeta.iterdir()))

    def test_una_peticion_demasiado_grande_redirige_con_aviso(self):
        enorme = io.BytesIO(os.urandom(4 * 1024 * 1024))
        respuesta = self._guardar_perfil(enorme)
        self.assertEqual(respuesta.status_code, 302)
        self.assertIsNone(self._avatar())


if __name__ == '__main__':
    unittest.main()