async function aplaudir(proyId) {
  const btn = document.getElementById('btn-aplaudir');
  const num = document.getElementById('num-aplausos');

  try {
    const res  = await fetch(`/portafolio/${proyId}/aplaudir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    const data = await res.json();
    if (!data.ok) return;

    // Actualizar UI
    num.textContent  = data.total;
    btn.classList.toggle('activo', data.accion === 'aplaudido');
  } catch (e) {
    console.error('Error al aplaudir:', e);
  }
}

delegar('click', '[data-aplaudir]', function (el) {
  aplaudir(Number(el.dataset.aplaudir));
});
