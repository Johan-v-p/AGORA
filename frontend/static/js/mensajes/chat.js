/* ══════════════════════════════════════════════════
   CHAT — Socket.IO en tiempo real
   ══════════════════════════════════════════════════ */

const datosChat = document.currentScript.dataset;
const ME       = Number(datosChat.usuarioId);
const OTRO_ID  = Number(datosChat.otroId);
const CONV_ID  = Number(datosChat.convId);
const URL_ENVIAR = datosChat.urlEnviar;
const URL_MENSAJES = datosChat.urlMensajes;
const NOMBRE_OTRO = datosChat.otroNombre;

const contenedor  = document.getElementById('chat-mensajes');
const inputMsg    = document.getElementById('inp-msg');
const btnEnviar   = document.getElementById('btn-enviar');
const labelEscrib = document.getElementById('escribiendo-label');
const dotEstado   = document.getElementById('dot-conectado');
const labelEstado = document.getElementById('label-estado');

let escribiendoTimer = null;

/* ── Scroll al fondo ── */
function scrollFondo(smooth = false) {
  contenedor.scrollTo({
    top: contenedor.scrollHeight,
    behavior: smooth ? 'smooth' : 'auto'
  });
}
scrollFondo();   // al cargar

/* ── Crear burbuja DOM ── */
function crearBurbuja(data, esMio) {
  // Quitar vacío si existe
  const vacio = document.getElementById('chat-vacio');
  if (vacio) vacio.remove();

  // Separador de fecha (hoy)
  const hoy = new Date().toISOString().slice(0, 10);
  const ultimaSep = [...contenedor.querySelectorAll('.msg-fecha-sep')].pop();
  if (!ultimaSep || ultimaSep.textContent !== hoy) {
    const sep = document.createElement('div');
    sep.className   = 'msg-fecha-sep';
    sep.textContent = hoy;
    contenedor.appendChild(sep);
  }

  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap ' + (esMio ? 'propio' : 'otro');
  wrap.id        = 'msg-' + data.msg_id;

  const burbuja = document.createElement('div');
  burbuja.className   = 'msg-burbuja';
  burbuja.textContent = data.contenido;

  const meta = document.createElement('div');
  meta.className   = 'msg-meta';
  meta.textContent = data.hora + (esMio ? ' · ✓' : '');

  wrap.appendChild(burbuja);
  wrap.appendChild(meta);
  contenedor.appendChild(wrap);

  scrollFondo(true);
}

/* ── Enviar mensaje por fetch (sin recargar) ── */
async function enviarMensaje() {
  const texto = inputMsg.value.trim();
  if (!texto) return;

  btnEnviar.classList.add('enviando');
  inputMsg.disabled = true;

  try {
    const res = await fetch(URL_ENVIAR, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body:    'contenido=' + encodeURIComponent(texto)
    });

    if (res.ok) {
      inputMsg.value = '';
      // La burbuja la agrega el socket.on('mensaje_nuevo') cuando rebota del servidor
    } else {
      alert('Error al enviar. Intenta de nuevo.');
    }
  } catch (e) {
    alert('Sin conexión.');
  } finally {
    btnEnviar.classList.remove('enviando');
    inputMsg.disabled = false;
    inputMsg.focus();
  }
}

/* ── Enter para enviar ── */
inputMsg.addEventListener('keydown', function (e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    enviarMensaje();
  }
});

/* ── Notificar "escribiendo…" al otro ── */
inputMsg.addEventListener('input', function () {
  socket.emit('escribiendo', { conv_id: CONV_ID, autor_id: ME });
  clearTimeout(escribiendoTimer);
  escribiendoTimer = setTimeout(() => {
    socket.emit('dejo_escribir', { conv_id: CONV_ID, autor_id: ME });
  }, 1800);
});


/* ══ SOCKET.IO ══════════════════════════════════════ */
const socket = io({ transports: ['websocket', 'polling'] });

socket.on('connect', function () {
  dotEstado.classList.add('online');
  labelEstado.textContent = 'en línea';
});

socket.on('disconnect', function () {
  dotEstado.classList.remove('online');
  labelEstado.textContent = 'desconectado';
});

/* ── Recibir mensaje nuevo ── */
socket.on('mensaje_nuevo', function (data) {
  // Solo procesar si pertenece a esta conversación
  if (data.conv_id !== CONV_ID) return;

  const esMio    = (data.autor_id === ME);
  const msgExist = document.getElementById('msg-' + data.msg_id);

  if (!msgExist) {
    crearBurbuja(data, esMio);
  }

  // Si el mensaje es del otro → marcar como leído en BD silenciosamente
  if (!esMio) {
    fetch(URL_MENSAJES, { method: 'HEAD' }).catch(() => {});
    // El scroll ya ocurre en crearBurbuja
  }
});

/* ── Indicador de escritura ── */
socket.on('escribiendo', function (data) {
  if (data.conv_id !== CONV_ID || data.autor_id === ME) return;
  labelEscrib.textContent = NOMBRE_OTRO + ' está escribiendo…';
});

socket.on('dejo_escribir', function (data) {
  if (data.conv_id !== CONV_ID || data.autor_id === ME) return;
  labelEscrib.textContent = '';
});

delegar('click', '[data-enviar-mensaje]', enviarMensaje);
