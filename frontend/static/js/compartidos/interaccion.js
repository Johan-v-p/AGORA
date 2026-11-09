/* Comportamiento común declarado con atributos data-* en las plantillas.
   Se carga en <head>: los eventos delegados funcionan aunque el HTML aún no exista. */

function delegar(evento, selector, manejador) {
  document.addEventListener(evento, function (e) {
    const elemento = e.target.closest(selector);
    if (elemento) manejador(elemento, e);
  });
}

/* ── Modales ── */
delegar('click', '[data-abrir-modal]', function (el) {
  document.getElementById(el.dataset.abrirModal).classList.add('visible');
});

delegar('click', '[data-cerrar-modal]', function (el) {
  document.getElementById(el.dataset.cerrarModal).classList.remove('visible');
});

/* ── Confirmaciones ── */
delegar('click', 'a[data-confirmar], button[data-confirmar]', function (el, e) {
  if (!confirm(el.dataset.confirmar)) e.preventDefault();
});

delegar('submit', 'form[data-confirmar]', function (el, e) {
  if (!confirm(el.dataset.confirmar)) e.preventDefault();
});

/* ── Avatares rotos: el evento error no burbujea, se captura ── */
document.addEventListener('error', function (e) {
  const img = e.target;
  if (!(img instanceof HTMLImageElement) || !img.dataset.avatarAlterno) return;
  const alterno = img.dataset.avatarAlterno === 'siguiente'
    ? img.nextElementSibling
    : document.getElementById(img.dataset.avatarAlterno);
  img.style.display = 'none';
  if (alterno) alterno.style.display = 'flex';
}, true);

/* ── Barras cuyo ancho calcula el servidor ── */
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('[data-ancho]').forEach(function (el) {
    el.style.width = el.dataset.ancho + '%';
  });
});

/* ── Imágenes: avisar de tipo o tamaño no válido antes de enviar ──
   El servidor vuelve a validar; esto solo evita esperar a que suba un archivo inútil. */
delegar('change', 'input[type="file"][data-validar-imagen]', function (el) {
  const TIPOS = ['image/jpeg', 'image/png', 'image/webp'];
  const MAX_BYTES = 2 * 1024 * 1024;

  let aviso = el.parentElement.querySelector('.img-error');
  if (!aviso) {
    aviso = document.createElement('div');
    aviso.className = 'img-error';
    el.insertAdjacentElement('afterend', aviso);
  }
  aviso.textContent = '';

  const archivo = el.files[0];
  if (!archivo) return;

  let error = '';
  if (!TIPOS.includes(archivo.type)) {
    error = 'Formato no permitido. Usa JPG, PNG o WebP.';
  } else if (archivo.size > MAX_BYTES) {
    error = 'La imagen supera los 2 MB.';
  }
  if (error) {
    aviso.textContent = error;
    el.value = '';
  }
});
