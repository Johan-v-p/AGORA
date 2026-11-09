// Cerrar modal al hacer clic fuera
const modalPreg = document.getElementById('modal-nueva-preg');
modalPreg.addEventListener('click', function(e) {
  if (e.target === this) this.classList.remove('visible');
});
// Cerrar con Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') modalPreg.classList.remove('visible');
});
