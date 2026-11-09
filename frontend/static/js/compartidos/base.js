// Auto-desaparece los toasts después de 3.5 segundos
const toasts = document.querySelectorAll('.toast');
toasts.forEach(toast => {
  setTimeout(() => {
    toast.classList.add('toast--hide');
    // Elimina el nodo del DOM tras la animación
    setTimeout(() => toast.remove(), 400);
  }, 3500);
});
