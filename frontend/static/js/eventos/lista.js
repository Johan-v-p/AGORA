/* ── Cerrar modal ── */
const modalEv = document.getElementById('modal-nuevo-evento');
modalEv.addEventListener('click', e => {
  if (e.target === modalEv) modalEv.classList.remove('visible');
});
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') modalEv.classList.remove('visible');
});

/* ── Inscribirse / cancelar inscripción (AJAX) ── */
async function inscribirse(eventoId, btn) {
  try {
    const res  = await fetch(`/eventos/${eventoId}/inscribir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!data.ok) return;

    btn.classList.toggle('inscrito', data.inscrito);
    btn.querySelector('.lbl-normal').textContent =
      data.inscrito ? '✓ Inscrito' : 'Inscribirse';

    /* Actualiza cupos libres si están en el DOM */
    const cuposEl = btn.closest('.evento-accion').querySelector('.evento-cupos strong');
    if (cuposEl && data.cupos_libres !== undefined) {
      cuposEl.textContent = data.cupos_libres;
    }
  } catch(e) { console.error('Error al inscribirse:', e); }
}

delegar('click', '[data-inscribir-evento]', function (el) {
  inscribirse(Number(el.dataset.inscribirEvento), el);
});
