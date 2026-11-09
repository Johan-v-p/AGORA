// ── Filtro de categoría ──────────────────────────────
function filtrar(cat) {
  const url = new URL(window.location.href);
  url.searchParams.set('f', cat);
  window.location.href = url.toString();
}

// ── Modal nueva publicación ──────────────────────────
function abrirModal() {
  document.getElementById('modal-post').classList.add('visible');
  document.getElementById('titulo').focus();
}
function cerrarModal() {
  document.getElementById('modal-post').classList.remove('visible');
}

// Cerrar al hacer clic fuera del box
document.getElementById('modal-post').addEventListener('click', function(e) {
  if (e.target === this) cerrarModal();
});

// Cerrar con Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') cerrarModal();
});

// Contadores de caracteres
function contarTitulo(el) {
  const cnt = document.getElementById('cnt-titulo');
  const n = el.value.length;
  cnt.textContent = n + ' / 120';
  cnt.classList.toggle('over', n >= 110);
}
function contarContenido(el) {
  const cnt = document.getElementById('cnt-contenido');
  const n = el.value.length;
  cnt.textContent = n + ' / 2000';
  cnt.classList.toggle('over', n >= 1900);
}

delegar('input', '[data-contar-titulo]', contarTitulo);
delegar('input', '[data-contar-contenido]', contarContenido);

delegar('click', '[data-filtrar]', function (el) {
  filtrar(el.dataset.filtrar);
});

delegar('click', '[data-abrir-publicacion]', abrirModal);
delegar('click', '[data-cerrar-publicacion]', cerrarModal);
