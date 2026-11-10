"""
Pruebas de la captura opcional en proyectos del portafolio.
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


class ImagenProyectoTest(unittest.TestCase):
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

    def _imagen(self, proyecto_id=1):
        conn = agora.get_db()
        fila = conn.execute(
            "SELECT imagen_url FROM proyectos WHERE id = ?", (proyecto_id,)).fetchone()
        conn.close()
        return fila['imagen_url'] if fila else None

    def _total_proyectos(self):
        conn = agora.get_db()
        total = conn.execute("SELECT COUNT(*) AS n FROM proyectos").fetchone()['n']
        conn.close()
        return total

    def _existe(self, ruta):
        return (imagenes.DIRECTORIO_SUBIDAS.parent / ruta).exists()

    def _archivos_subidos(self):
        carpeta = imagenes.DIRECTORIO_SUBIDAS / 'proyectos'
        return list(carpeta.iterdir()) if carpeta.exists() else []

    def _crear(self, archivo=None, **extra):
        datos = {'titulo': 'Mi proyecto', 'descripcion': 'Descripción', 'estado': 'en_desarrollo'}
        datos.update(extra)
        if archivo is not None:
            datos['imagen'] = (archivo, 'captura.png')
        return self.client.post(
            '/nuevo-proyecto', data=datos, content_type='multipart/form-data')

    def test_crea_el_proyecto_con_captura_y_miniatura(self):
        self.assertEqual(self._crear(png()).status_code, 302)
        ruta = self._imagen()
        self.assertTrue(ruta.startswith('uploads/proyectos/'))
        self.assertTrue(self._existe(ruta))
        self.assertTrue(self._existe(imagenes.ruta_miniatura(ruta)))

    def test_crea_el_proyecto_sin_captura(self):
        self._crear()
        self.assertEqual(self._total_proyectos(), 1)
        self.assertIsNone(self._imagen())

    def test_el_portafolio_muestra_la_miniatura(self):
        self._crear(png())
        ruta = self._imagen()
        respuesta = self.client.get('/portafolio')
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(imagenes.ruta_miniatura(ruta).encode(), respuesta.data)

    def test_un_archivo_falso_no_crea_el_proyecto(self):
        self._crear(io.BytesIO(b'<?php system($_GET[0]); ?>'))
        self.assertEqual(self._total_proyectos(), 0)
        self.assertEqual(self._archivos_subidos(), [])

    def test_un_formulario_invalido_no_deja_imagenes_huerfanas(self):
        self._crear(png(), titulo='')
        self.assertEqual(self._total_proyectos(), 0)
        self.assertEqual(self._archivos_subidos(), [])


if __name__ == '__main__':
    unittest.main()