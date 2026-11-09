/* ── Votar respuesta (AJAX) ────────────────────────── */
async function votar(respId, valor, btnClicado) {
  try {
    const res  = await fetch(`/foros/respuesta/${respId}/votar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ valor })
    });
    const data = await res.json();
    if (!data.ok) return;

    /* Actualiza el contador */
    document.getElementById(`votos-${respId}`).textContent = data.total;

    /* Actualiza clases activas en los dos botones del grupo */
    const card  = btnClicado.closest('.resp-card');
    const upBtn = card.querySelector('.voto-btn.up');
    const dnBtn = card.querySelector('.voto-btn.down');
    upBtn.classList.toggle('activo', data.mi_voto === 1);
    dnBtn.classList.toggle('activo', data.mi_voto === -1);
  } catch(e) {
    console.error('Error al votar:', e);
  }
}

delegar('click', '[data-votar-respuesta]', function (el) {
  votar(Number(el.dataset.votarRespuesta), Number(el.dataset.voto), el);
});
