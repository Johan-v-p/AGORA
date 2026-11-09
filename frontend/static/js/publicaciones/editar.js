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
