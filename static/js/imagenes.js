/* imagenes.js — Validación en el navegador de las imágenes que se suben.
   La validación REAL se hace en el servidor (app.py → guardar_imagen);
   esto solo evita enviar archivos que se sabe que serán rechazados. */
const MAX_IMG_BYTES = 2 * 1024 * 1024;                       // 2 MB
const TIPOS_IMG     = ['image/jpeg', 'image/png', 'image/webp'];

function validarImagen(input) {
  const archivo = input.files && input.files[0];
  const aviso   = input.parentElement.querySelector('.img-error');
  if (aviso) aviso.textContent = '';
  if (!archivo) return true;

  let msg = '';
  if (!TIPOS_IMG.includes(archivo.type)) msg = 'Solo se permiten imágenes JPG, PNG o WebP.';
  else if (archivo.size > MAX_IMG_BYTES)  msg = 'La imagen supera el límite de 2 MB.';

  if (msg) {
    input.value = '';
    if (aviso) aviso.textContent = msg; else alert(msg);
    return false;
  }
  return true;
}