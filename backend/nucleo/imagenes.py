"""Subida segura de imágenes: valida, vuelve a codificar, redimensiona y guarda."""

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
DIRECTORIO_SUBIDAS = RAIZ_PROYECTO / 'frontend' / 'static' / 'uploads'

CARPETAS = ('avatares', 'publicaciones', 'proyectos')
MAX_BYTES = 2 * 1024 * 1024        # límite por imagen: 2 MB
MAX_PIXELES = 25_000_000           # evita imágenes "bomba" (p. ej. 20000x20000)
FORMATOS_PERMITIDOS = {'JPEG', 'PNG', 'WEBP'}  # formato REAL detectado por Pillow


class ImagenInvalida(ValueError):
    """La imagen subida no cumple las reglas; el mensaje se muestra al usuario."""


def ruta_miniatura(ruta):
    """'uploads/posts/abc.webp' -> 'uploads/posts/abc_thumb.webp'."""
    return ruta.rsplit('.', 1)[0] + '_thumb.webp'


def guardar_imagen(archivo, carpeta, max_lado, thumb_lado, cuadrada=False):
    """Valida, re-codifica y guarda una imagen subida por el usuario.

    - Devuelve None si no se envió archivo.
    - Lanza ImagenInvalida (con mensaje para el usuario) si no es válida.
    - Comprueba el formato REAL con Pillow, no la extensión ni el Content-Type,
      y vuelve a codificar la imagen: así se eliminan el EXIF y cualquier
      contenido extra escondido en el archivo.
    - Nunca usa el nombre original: genera uno aleatorio (uuid4).
    - Guarda la imagen redimensionada y una miniatura '<nombre>_thumb.webp'.
    - Devuelve la ruta relativa a la carpeta static, ej. 'uploads/publicaciones/ab12.webp'.
    """
    if carpeta not in CARPETAS:
        raise ValueError(f'Carpeta de subidas desconocida: {carpeta}')
    if archivo is None or not archivo.filename:
        return None

    datos = archivo.read(MAX_BYTES + 1)
    if not datos:
        raise ImagenInvalida('El archivo está vacío.')
    if len(datos) > MAX_BYTES:
        raise ImagenInvalida('La imagen supera el límite de 2 MB.')

    mensaje_tipo = 'El archivo no es una imagen válida. Usa JPG, PNG o WebP.'
    try:
        img = Image.open(io.BytesIO(datos))
        if img.format not in FORMATOS_PERMITIDOS:
            raise ImagenInvalida(mensaje_tipo)
        if img.width * img.height > MAX_PIXELES:
            raise ImagenInvalida('La imagen tiene demasiados píxeles.')
        img.load()                       # decodifica de verdad (detecta archivos corruptos)
        img = ImageOps.exif_transpose(img)
        img = img.convert('RGBA' if img.mode in ('RGBA', 'LA', 'P') else 'RGB')
    except ImagenInvalida:
        raise
    except Exception:
        raise ImagenInvalida(mensaje_tipo)

    if cuadrada:                         # recorte centrado, para avatares
        lado = min(img.width, img.height)
        izquierda = (img.width - lado) // 2
        arriba = (img.height - lado) // 2
        img = img.crop((izquierda, arriba, izquierda + lado, arriba + lado))

    img.thumbnail((max_lado, max_lado), Image.LANCZOS)    # solo reduce, nunca amplía
    miniatura = img.copy()
    miniatura.thumbnail((thumb_lado, thumb_lado), Image.LANCZOS)

    nombre = uuid.uuid4().hex
    destino = DIRECTORIO_SUBIDAS / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    img.save(destino / f'{nombre}.webp', 'WEBP', quality=85)
    miniatura.save(destino / f'{nombre}_thumb.webp', 'WEBP', quality=80)
    return f'uploads/{carpeta}/{nombre}.webp'


def borrar_imagen(ruta):
    """Borra una imagen subida y su miniatura. Ignora URLs externas y rutas raras."""
    if not ruta or not ruta.startswith('uploads/'):
        return
    estaticos = DIRECTORIO_SUBIDAS.parent
    raiz_subidas = DIRECTORIO_SUBIDAS.resolve()
    for relativa in (ruta, ruta_miniatura(ruta)):
        completa = (estaticos / relativa).resolve()
        if raiz_subidas in completa.parents and completa.is_file():
            try:
                completa.unlink()
            except OSError:
                pass