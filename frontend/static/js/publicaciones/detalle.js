// ── Reacción AJAX (toggle sin recargar página) ──────────
async function reaccionar(postId) {
  const btn = document.getElementById('btn-reaccion');
  const total = document.getElementById('total-reacciones');

  try {
    const res = await fetch(`/reaccionar/${postId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const data = await res.json();

    if (data.ok) {
      total.textContent = data.total;
      btn.classList.toggle('activa', data.activa);
    }
  } catch (e) {
    console.error('Error al reaccionar:', e);
  }
}

// ── Cerrar modal de eliminación al hacer clic fuera ──────
const modalEliminar = document.getElementById('modal-eliminar-post');
if (modalEliminar) {
  modalEliminar.addEventListener('click', function(e) {
    if (e.target === this) this.classList.remove('visible');
  });
}

// Cerrar con Escape
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape' && modalEliminar) {
    modalEliminar.classList.remove('visible');
  }
});

delegar('click', '[data-reaccionar]', function (el) {
  reaccionar(Number(el.dataset.reaccionar));
});
