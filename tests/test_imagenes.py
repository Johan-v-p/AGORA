"""
Pruebas de la subida de imágenes (backend/nucleo/imagenes.py).
Ejecutar desde la raíz del proyecto: python -m unittest discover -s tests -v

Guardan en una carpeta temporal; no tocan frontend/static/uploads.
"""

import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from werkzeug.datastructures import FileStorage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.nucleo import imagenes  # noqa: E402


def crear_archivo(ancho=100, alto=60, formato='PNG', nombre='foto.png', ruido=False):
    """Devuelve un FileStorage con una imagen generada en memoria."""
    if ruido:
        img = Image.frombytes('RGB', (ancho, alto), os.urandom(ancho * alto * 3))
    else:
        img = Image.new('RGB', (ancho, alto), (200, 30, 30))
    buffer = io.BytesIO()
    img.save(buffer, formato)
    buffer.seek(0)
    return FileStorage(stream=buffer, filename=nombre)


def tamano(ruta_archivo):
    """Tamaño (ancho, alto) de una imagen guardada, cerrando el archivo."""
    with Image.open(ruta_archivo) as img:
        return img.size


def archivo_con_bytes(contenido, nombre):
    return FileStorage(stream=io.BytesIO(contenido), filename=nombre)


class GuardarImagenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = imagenes.DIRECTORIO_SUBIDAS
        imagenes.DIRECTORIO_SUBIDAS = Path(self.tmp.name) / 'static' / 'uploads'

    def tearDown(self):
        imagenes.DIRECTORIO_SUBIDAS = self.original
        self.tmp.cleanup()

    def _archivos(self, carpeta):
        destino = imagenes.DIRECTORIO_SUBIDAS / carpeta
        return sorted(p.name for p in destino.iterdir()) if destino.exists() else []

    def test_sin_archivo_devuelve_none(self):
        self.assertIsNone(imagenes.guardar_imagen(None, 'publicaciones', 1280, 480))
        vacio = FileStorage(stream=io.BytesIO(b''), filename='')
        self.assertIsNone(imagenes.guardar_imagen(vacio, 'publicaciones', 1280, 480))

    def test_guarda_imagen_y_miniatura_con_nombre_aleatorio(self):
        ruta = imagenes.guardar_imagen(
            crear_archivo(nombre='../../evil name.php.jpg'), 'publicaciones', 1280, 480)
        self.assertTrue(ruta.startswith('uploads/publicaciones/'))
        self.assertTrue(ruta.endswith('.webp'))
        self.assertNotIn('evil', ruta)
        self.assertNotIn('php', ruta)
        self.assertEqual(len(self._archivos('publicaciones')), 2)

    def test_redimensiona_sin_ampliar(self):
        ruta = imagenes.guardar_imagen(crear_archivo(3000, 2000), 'publicaciones', 1280, 480)
        self.assertEqual(max(tamano(imagenes.DIRECTORIO_SUBIDAS.parent / ruta)), 1280)
        chica = imagenes.guardar_imagen(crear_archivo(100, 60), 'publicaciones', 1280, 480)
        self.assertEqual(tamano(imagenes.DIRECTORIO_SUBIDAS.parent / chica), (100, 60))

    def test_avatar_se_recorta_cuadrado_y_genera_miniatura(self):
        ruta = imagenes.guardar_imagen(
            crear_archivo(900, 600), 'avatares', 400, 96, cuadrada=True)
        estaticos = imagenes.DIRECTORIO_SUBIDAS.parent
        self.assertEqual(tamano(estaticos / ruta), (400, 400))
        self.assertEqual(tamano(estaticos / imagenes.ruta_miniatura(ruta)), (96, 96))

    def test_rechaza_texto_disfrazado_de_imagen(self):
        falso = archivo_con_bytes(b'<?php system($_GET[0]); ?>', 'foto.jpg')
        with self.assertRaises(imagenes.ImagenInvalida):
            imagenes.guardar_imagen(falso, 'publicaciones', 1280, 480)
        self.assertEqual(self._archivos('publicaciones'), [])

    def test_rechaza_formato_no_permitido_aunque_se_llame_png(self):
        with self.assertRaises(imagenes.ImagenInvalida):
            imagenes.guardar_imagen(
                crear_archivo(formato='GIF', nombre='a.png'), 'publicaciones', 1280, 480)

    def test_rechaza_archivo_vacio(self):
        with self.assertRaises(imagenes.ImagenInvalida):
            imagenes.guardar_imagen(archivo_con_bytes(b'', 'v.png'), 'publicaciones', 1280, 480)

    def test_rechaza_imagen_de_mas_de_2_mb(self):
        pesada = crear_archivo(1200, 1200, ruido=True)
        with self.assertRaises(imagenes.ImagenInvalida) as contexto:
            imagenes.guardar_imagen(pesada, 'publicaciones', 1280, 480)
        self.assertIn('2 MB', str(contexto.exception))

    def test_rechaza_imagen_con_demasiados_pixeles(self):
        enorme = crear_archivo(6000, 6000)
        with self.assertRaises(imagenes.ImagenInvalida) as contexto:
            imagenes.guardar_imagen(enorme, 'publicaciones', 1280, 480)
        self.assertIn('píxeles', str(contexto.exception))

    def test_carpeta_desconocida_no_es_un_error_de_usuario(self):
        with self.assertRaises(ValueError) as contexto:
            imagenes.guardar_imagen(crear_archivo(), 'otra', 1280, 480)
        self.assertNotIsInstance(contexto.exception, imagenes.ImagenInvalida)


class BorrarImagenTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original = imagenes.DIRECTORIO_SUBIDAS
        imagenes.DIRECTORIO_SUBIDAS = Path(self.tmp.name) / 'static' / 'uploads'

    def tearDown(self):
        imagenes.DIRECTORIO_SUBIDAS = self.original
        self.tmp.cleanup()

    def test_borra_imagen_y_miniatura(self):
        ruta = imagenes.guardar_imagen(crear_archivo(), 'proyectos', 1280, 480)
        estaticos = imagenes.DIRECTORIO_SUBIDAS.parent
        imagenes.borrar_imagen(ruta)
        self.assertFalse((estaticos / ruta).exists())
        self.assertFalse((estaticos / imagenes.ruta_miniatura(ruta)).exists())

    def test_ignora_none_y_urls_externas(self):
        imagenes.borrar_imagen(None)
        imagenes.borrar_imagen('')
        imagenes.borrar_imagen('https://ejemplo.com/foto.jpg')

    def test_no_borra_archivos_fuera_de_uploads(self):
        estaticos = imagenes.DIRECTORIO_SUBIDAS.parent
        imagenes.DIRECTORIO_SUBIDAS.mkdir(parents=True)
        intocable = estaticos / 'importante.txt'
        intocable.write_text('no me borres')
        imagenes.borrar_imagen('uploads/../importante.txt')
        self.assertTrue(intocable.exists())


if __name__ == '__main__':
    unittest.main()
