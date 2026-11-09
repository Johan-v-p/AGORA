function toggleIns(id, inscrito) {
  const btn = document.getElementById('btn-ins');
  btn.disabled = true;
  fetch(`/eventos/${id}/inscribir`, {method:'POST'})
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { alert(data.error||'Error'); btn.disabled=false; return; }
      inscrito = data.inscrito;
      btn.textContent = inscrito ? 'Cancelar inscripción' : 'Inscribirse';
      btn.className = 'btn-inscribir' + (inscrito ? ' cancelar' : '');
      btn.disabled = false;
      btn.onclick = () => toggleIns(id, inscrito);
    })
    .catch(() => { btn.disabled=false; });
}
