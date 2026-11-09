/* ── Cerrar modal ── */
const modalProy = document.getElementById('modal-nuevo-proy');
modalProy.addEventListener('click', e => {
  if (e.target === modalProy) modalProy.classList.remove('visible');
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') modalProy.classList.remove('visible');
});

/* ── Aplaudir proyecto (AJAX) ── */
async function aplaudir(proyId, btn) {
  try {
    const res  = await fetch(`/portafolio/${proyId}/aplaudir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!data.ok) return;
    document.getElementById(`aplausos-${proyId}`).textContent = data.total;
    /* Actualiza todos los botones de ese proyecto (puede aparecer 2 veces) */
    document.querySelectorAll(`[data-aplaudir="${proyId}"]`).forEach(b => {
      b.classList.toggle('activo', data.activo);
    });
  } catch(e) { console.error('Error al aplaudir:', e); }
}

delegar('click', '[data-aplaudir]', function (el) {
  aplaudir(Number(el.dataset.aplaudir), el);
});
