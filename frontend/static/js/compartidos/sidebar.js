(function () {
  const usuarioId = Number(document.currentScript.dataset.usuarioId);
  const notifBadge = document.getElementById('notif-badge');
  const msgsBadge  = document.getElementById('msgs-badge');
  let conteoNotif  = 0;
  let conteoMsgs   = 0;

  const socket = io({ transports: ['websocket', 'polling'] });

  /* ── Al conectar: cargar conteos iniciales ── */
  socket.on('connect', function () {
    // Badge notificaciones
    fetch('/notificaciones/no-leidas')
      .then(r => r.json())
      .then(d => setBadgeNotif(d.total))
      .catch(() => {});

    // Badge mensajes
    fetch('/mensajes/no-leidos')
      .then(r => r.json())
      .then(d => setBadgeMsgs(d.total))
      .catch(() => {});
  });

  /* ── Notificación genérica (like, comentario, etc.) ── */
  socket.on('notificacion', function (data) {
    conteoNotif++;
    setBadgeNotif(conteoNotif);
    mostrarToast('🔔 ' + data.mensaje, data.url);
  });

  /* ── Mensaje privado nuevo ── */
  socket.on('mensaje_nuevo', function (data) {
    // Solo incrementar si no estoy ya en esa conversación
    const enChat = window.location.pathname.startsWith('/mensajes/');
    const mismoConv = enChat && window.location.pathname.includes('/' + data.otro_id);
    if (!mismoConv && data.autor_id !== usuarioId) {
      conteoMsgs++;
      setBadgeMsgs(conteoMsgs);
    }
  });

  function setBadgeNotif(n) {
    conteoNotif = n;
    notifBadge.textContent   = n > 99 ? '99+' : n;
    notifBadge.style.display = n > 0 ? 'flex' : 'none';
  }

  function setBadgeMsgs(n) {
    conteoMsgs = n;
    msgsBadge.textContent   = n > 99 ? '99+' : n;
    msgsBadge.style.display = n > 0 ? 'flex' : 'none';
  }

  function mostrarToast(texto, url) {
    const t = document.createElement('a');
    t.href  = url || '#';
    t.style.cssText = [
      'position:fixed', 'bottom:80px', 'right:24px', 'z-index:9999',
      'background:var(--panel)', 'border:1px solid var(--borde)',
      'border-left:3px solid #6fcf6f', 'padding:12px 16px',
      'font-size:11px', 'color:var(--texto)', 'text-decoration:none',
      'max-width:280px', 'line-height:1.4', 'cursor:pointer'
    ].join(';');
    t.textContent = texto;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 4000);
  }

  /* Limpiar badge de notifics al entrar a /notificaciones */
  if (window.location.pathname === '/notificaciones') setBadgeNotif(0);

  /* Limpiar badge de mensajes al entrar a /mensajes o /mensajes/* */
  if (window.location.pathname.startsWith('/mensajes')) setBadgeMsgs(0);
})();
