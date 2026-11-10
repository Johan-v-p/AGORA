(() => {
  const script = document.currentScript;
  const usuarioAutenticado = script?.dataset.temaUsuario === 'true';
  const controles = document.querySelectorAll('[data-selector-tema]');
  const preferenciaInicial = script?.dataset.temaInicial || 'system';

  function temaAplicado(preferencia) {
    return preferencia === 'system'
      ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
      : preferencia;
  }

  function aplicarTema(preferencia) {
    document.documentElement.dataset.theme = temaAplicado(preferencia);
  }

  function actualizarControles(preferencia) {
    controles.forEach(control => {
      control.checked = control.type === 'radio' && control.value === preferencia;
      if (control.tagName === 'SELECT') control.value = preferencia;
    });
  }

  async function guardarTema(preferencia) {
    localStorage.setItem('agora-theme', preferencia);
    if (!usuarioAutenticado) return;
    const respuesta = await fetch('/ajustes/tema', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: new URLSearchParams({tema: preferencia}),
    });
    if (!respuesta.ok) {
      throw new Error(`No se pudo guardar el tema (${respuesta.status})`);
    }
  }

  const preferencia = usuarioAutenticado ? preferenciaInicial : (localStorage.getItem('agora-theme') || 'system');
  actualizarControles(preferencia);
  aplicarTema(preferencia);

  controles.forEach(control => {
    control.addEventListener('change', () => {
      const nuevaPreferencia = control.value;
      actualizarControles(nuevaPreferencia);
      aplicarTema(nuevaPreferencia);
      guardarTema(nuevaPreferencia).catch(error => console.error(error));
    });
  });

  window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
    const actual = document.querySelector('[data-selector-tema]:checked')?.value
      || document.querySelector('[data-selector-tema]')?.value;
    if (actual === 'system') aplicarTema(actual);
  });
})();
