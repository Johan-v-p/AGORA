(function () {
  const usuarioId = Number(document.currentScript.dataset.usuarioId);
  const socket = io({ transports: ['websocket', 'polling'] });

  // ── Cuando llega un mensaje nuevo, actualiza el preview en esta lista ──
  socket.on('mensaje_nuevo', function (data) {
    const conv_id  = data.conv_id;
    const item     = document.getElementById('conv-' + conv_id);
    const preview  = document.getElementById('preview-' + conv_id);
    const badge    = document.getElementById('badge-' + conv_id);
    const tiempo   = document.getElementById('tiempo-' + conv_id);
    const lista    = document.getElementById('conv-lista');

    if (item && preview) {
      // Actualiza preview y hora
      preview.textContent = data.contenido;
      if (tiempo) tiempo.textContent = 'ahora';

      // Si no soy el autor → marcar como no leído y subir al top
      if (data.autor_id !== usuarioId) {
        item.classList.add('no-leido');
        preview.style.fontWeight = '500';
        preview.style.color = 'var(--texto)';
        // Incrementar badge
        const cur = parseInt(badge.textContent) || 0;
        badge.textContent = cur + 1;
        badge.style.display = 'inline-flex';
        // Subir al tope de la lista
        if (lista && item.parentNode === lista) {
          lista.insertBefore(item, lista.firstChild);
        }
        // Actualizar badge global
        actualizarBadgeTotal();
      }
    }
  });

  function actualizarBadgeTotal() {
    const todos = document.querySelectorAll('.conv-badge');
    let total = 0;
    todos.forEach(b => { if (getComputedStyle(b).display !== 'none') total += parseInt(b.textContent) || 0; });
    const gb = document.getElementById('msgs-total-badge');
    if (gb) {
      gb.textContent = total;
      gb.style.display = total > 0 ? 'inline' : 'none';
    }
  }

  // Inicializar badge total al cargar
  actualizarBadgeTotal();
})();

delegar('click', '[data-archivar-conversacion]', function (form, e) {
  e.preventDefault();
  if (confirm('¿Archivar esta conversación?')) form.submit();
});
