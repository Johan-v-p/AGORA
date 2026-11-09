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
