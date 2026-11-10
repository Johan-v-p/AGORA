"""
Pruebas de las imágenes en publicaciones (crear, editar, quitar y mostrar).
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

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
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


class ImagenPublicacionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_original = agora.DB
        self.subidas_original = imagenes.DIRECTORIO_SUBIDAS
        agora.DB = os.path.join(self.tmp.name, 'test.db')
        imagenes.DIRECTORIO_SUBIDAS = Path(self.tmp.name) / 'static' / 'uploads'
        agora.app.config['TESTING'] = True

        conn = sqlite3.connect(agora.DB)
        conn.executescript((RAIZ / 'scripts' / 'esquema.sql').read_text(encoding='utf-8'))
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

    def _imagen(self, post_id=1):
        conn = agora.get_db()
        fila = conn.execute(
            "SELECT imagen_url FROM publicaciones WHERE id = ?", (post_id,)).fetchone()
        conn.close()
        return fila['imagen_url'] if fila else None

    def _total_posts(self):
        conn = agora.get_db()
        total = conn.execute("SELECT COUNT(*) AS n FROM publicaciones").fetchone()['n']
        conn.close()
        return total

    def _existe(self, ruta):
        return (imagenes.DIRECTORIO_SUBIDAS.parent / ruta).exists()

    def _archivos_subidos(self):
        carpeta = imagenes.DIRECTORIO_SUBIDAS / 'publicaciones'
        return list(carpeta.iterdir()) if carpeta.exists() else []

    def _crear(self, archivo=None, **extra):
        datos = {'titulo': 'Hola', 'contenido': 'Contenido de prueba', 'categoria': 'general'}
        datos.update(extra)
        if archivo is not None:
            datos['imagen'] = (archivo, 'foto.png')
        return self.client.post(
            '/nueva-publicacion', data=datos, content_type='multipart/form-data')

    def _editar(self, archivo=None, **extra):
        datos = {'titulo': 'Hola', 'contenido': 'Contenido editado', 'categoria': 'general'}
        datos.update(extra)
        if archivo is not None:
            datos['imagen'] = (archivo, 'foto.png')
        return self.client.post(
            '/editar/1', data=datos, content_type='multipart/form-data')

    def test_crea_la_publicacion_con_imagen_y_miniatura(self):
        self.assertEqual(self._crear(png()).status_code, 302)
        ruta = self._imagen()
        self.assertTrue(ruta.startswith('uploads/publicaciones/'))
        self.assertTrue(self._existe(ruta))
        self.assertTrue(self._existe(imagenes.ruta_miniatura(ruta)))

    def test_crea_la_publicacion_sin_imagen(self):
        self._crear()
        self.assertEqual(self._total_posts(), 1)
        self.assertIsNone(self._imagen())

    def test_el_feed_muestra_la_miniatura_y_el_detalle_la_imagen_completa(self):
        self._crear(png())
        ruta = self._imagen()
        feed = self.client.get('/feed')
        self.assertEqual(feed.status_code, 200)
        self.assertIn(imagenes.ruta_miniatura(ruta).encode(), feed.data)
        detalle = self.client.get('/post/1')
        self.assertEqual(detalle.status_code, 200)
        self.assertIn(ruta.encode(), detalle.data)

    def test_un_archivo_falso_no_crea_la_publicacion(self):
        self._crear(io.BytesIO(b'<?php system($_GET[0]); ?>'))
        self.assertEqual(self._total_posts(), 0)
        self.assertEqual(self._archivos_subidos(), [])

    def test_un_formulario_invalido_no_deja_imagenes_huerfanas(self):
        self._crear(png(), titulo='')
        self.assertEqual(self._total_posts(), 0)
        self.assertEqual(self._archivos_subidos(), [])

    def test_editar_con_otra_imagen_borra_la_anterior(self):
        self._crear(png())
        primera = self._imagen()
        self._editar(png(400, 400))
        segunda = self._imagen()
        self.assertNotEqual(primera, segunda)
        self.assertFalse(self._existe(primera))
        self.assertFalse(self._existe(imagenes.ruta_miniatura(primera)))
        self.assertTrue(self._existe(segunda))

    def test_editar_sin_archivo_conserva_la_imagen(self):
        self._crear(png())
        ruta = self._imagen()
        self._editar()
        self.assertEqual(self._imagen(), ruta)
        self.assertTrue(self._existe(ruta))

    def test_quitar_la_imagen_borra_los_archivos(self):
        self._crear(png())
        ruta = self._imagen()
        self._editar(quitar_imagen='1')
        self.assertIsNone(self._imagen())
        self.assertFalse(self._existe(ruta))
        self.assertFalse(self._existe(imagenes.ruta_miniatura(ruta)))

    def test_editar_con_archivo_falso_conserva_la_imagen(self):
        self._crear(png())
        ruta = self._imagen()
        self._editar(io.BytesIO(b'no soy una imagen'))
        self.assertEqual(self._imagen(), ruta)
        self.assertTrue(self._existe(ruta))


if __name__ == '__main__':
    unittest.main()