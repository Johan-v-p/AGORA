function toggleSeguir(usuarioId, yaSigniendo) {
  const btn    = document.getElementById('btn-seguir');
  const texto  = document.getElementById('btn-seguir-texto');
  const cont   = document.getElementById('contador-seguidores');
  const ruta   = yaSigniendo
    ? `/dejar-seguir/${usuarioId}`
    : `/seguir/${usuarioId}`;

  btn.disabled = true;

  fetch(ruta, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { btn.disabled = false; return; }

      yaSigniendo = data.siguiendo;
      texto.textContent      = data.siguiendo ? 'Siguiendo' : '+ Seguir';
      cont.textContent       = data.total_seguidores;
      btn.className          = 'btn-seguir' + (data.siguiendo ? ' siguiendo' : '');
      btn.disabled           = false;

      // Re-bind para el próximo click
      btn.onclick = () => toggleSeguir(usuarioId, yaSigniendo);
    })
    .catch(() => { btn.disabled = false; });
}
