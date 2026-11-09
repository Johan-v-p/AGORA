/* ── Preview de avatar en tiempo real ─── */
function previsualizarAvatar(url) {
  const wrap   = document.getElementById('avatar-preview');
  const img    = document.getElementById('avatar-img');
  const inicial = document.getElementById('avatar-inicial');

  if (!url) {
    // Sin URL → mostrar inicial
    if (img) img.style.display = 'none';
    inicial.style.display = 'flex';
    return;
  }

  // Si el img ya existe, actualizar src; si no, crearlo
  if (img) {
    img.src = url;
    img.style.display = 'block';
    inicial.style.display = 'none';
  } else {
    const newImg = document.createElement('img');
    newImg.id  = 'avatar-img';
    newImg.src = url;
    newImg.alt = 'Avatar';
    newImg.className = 'avatar-img-previa';
    newImg.onerror = () => {
      newImg.style.display = 'none';
      inicial.style.display = 'flex';
    };
    newImg.onload = () => { inicial.style.display = 'none'; };
    wrap.prepend(newImg);
  }
}

/* ── Validar coincidencia de passwords ── */
function validarPasswordsMatch() {
  const nueva  = document.getElementById('password_nueva').value;
  const conf   = document.getElementById('password_conf2').value;
  const msg    = document.getElementById('password-match-msg');
  const btn    = document.getElementById('btn-cambiar-pwd');

  if (!conf) { msg.style.display = 'none'; return; }

  msg.style.display = 'block';

  if (nueva === conf) {
    msg.textContent  = '✓ Las contraseñas coinciden';
    msg.style.color  = '#6fcf6f';
    btn.disabled     = false;
  } else {
    msg.textContent  = '✗ Las contraseñas no coinciden';
    msg.style.color  = '#cf6f6f';
    btn.disabled     = true;
  }
}

delegar('change', '[data-previsualizar-avatar]', function (el) {
  const archivo = el.files[0];
  const img = document.getElementById('avatar-img');
  // Guardamos la foto actual para poder volver a ella si se cancela la selección
  if (img && !img.dataset.original) img.dataset.original = img.getAttribute('src');
  previsualizarAvatar(archivo ? URL.createObjectURL(archivo) : (img ? img.dataset.original : ''));
});

delegar('input', '[data-validar-password]', validarPasswordsMatch);
