// ── Validación en tiempo real: contraseñas ──────────
const pass     = document.getElementById('password');
const confirmar = document.getElementById('confirmar');
const msg      = document.getElementById('msg-pass');
const btnCrear = document.getElementById('btn-crear');

function validarPasswords() {
  // Solo muestra error si el campo confirmar tiene algo escrito
  const hayContenido = confirmar.value.length > 0;
  const coinciden    = pass.value === confirmar.value;

  msg.style.display      = (hayContenido && !coinciden) ? 'block' : 'none';
  btnCrear.disabled      = hayContenido && !coinciden;
}

pass.addEventListener('input', validarPasswords);
confirmar.addEventListener('input', validarPasswords);
