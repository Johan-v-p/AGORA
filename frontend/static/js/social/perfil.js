// ── Modal logout ────────────────────────────────────
function abrirLogout() {
  document.getElementById('modal-logout').classList.add('visible');
}
function cerrarModal() {
  document.getElementById('modal-logout').classList.remove('visible');
}
document.getElementById('modal-logout').addEventListener('click', function(e) {
  if (e.target === this) cerrarModal();
});

// ── Modal eliminar ───────────────────────────────────
// Se usa data-id y data-titulo en lugar de onclick con comillas anidadas
document.querySelectorAll('.js-eliminar').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var postId  = this.dataset.id;
    var titulo  = this.dataset.titulo;
    document.getElementById('eliminar-titulo-preview').textContent = '"' + titulo + '"';
    document.getElementById('form-eliminar').action = '/eliminar/' + postId;
    document.getElementById('modal-eliminar').classList.add('visible');
  });
});

function cerrarEliminar() {
  document.getElementById('modal-eliminar').classList.remove('visible');
}
document.getElementById('modal-eliminar').addEventListener('click', function(e) {
  if (e.target === this) cerrarEliminar();
});

// Cerrar ambos modales con Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') { cerrarModal(); cerrarEliminar(); }
});
