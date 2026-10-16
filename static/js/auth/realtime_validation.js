/**
 * realtime_validation.js - Módulo de validación de registro Monagua.
 * Las validaciones asíncronas en tiempo real son gestionadas de forma declarativa,
 * reactiva y segura por HTMX (hx-get / hx-trigger / hx-target) con protección
 * de Rate Limiting OWASP en el servidor Django.
 */

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('formularioRegistro');
  if (form) {
    form.addEventListener('submit', function (e) {
      // Prevenir envío si existen mensajes de error visibles activos
      const invalidFeedbacks = Array.from(
        form.querySelectorAll('.invalid-feedback.d-block')
      ).filter(fb => fb.textContent.trim().length > 0 && fb.style.display !== 'none');

      if (invalidFeedbacks.length > 0) {
        e.preventDefault();
        e.stopPropagation();
        const parentInput = invalidFeedbacks[0].closest('.mb-3')?.querySelector('input');
        if (parentInput) {
          parentInput.focus();
        }
        return false;
      }
    });
  }
});
