function toggleSeguir(usuarioId, yaSiguiendo, btn) {
  const ruta = yaSiguiendo ? `/dejar-seguir/${usuarioId}` : `/seguir/${usuarioId}`;
  btn.disabled = true;

  fetch(ruta, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { btn.disabled = false; return; }

      yaSiguiendo       = data.siguiendo;
      btn.textContent   = data.siguiendo ? 'Siguiendo' : '+ Seguir';
      btn.className     = 'btn-seg' + (data.siguiendo ? ' siguiendo' : '');
      btn.disabled      = false;
      btn.onclick       = () => toggleSeguir(usuarioId, yaSiguiendo, btn);
    })
    .catch(() => { btn.disabled = false; });
}
