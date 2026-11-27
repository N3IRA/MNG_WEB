/**
 * realtime_validation.js - Módulo de validación y protección de envío para el registro Monagua.
 * - Previene envíos múltiples accidentales (doble clic o clics repetidos en "Crear Cuenta").
 * - Muestra estado de carga interactivo con spinner y deshabilita el botón mientras se despacha el correo OTP.
 * - Previene envío si existen campos inválidos o mensajes de error activos en pantalla.
 */

document.addEventListener('DOMContentLoaded', function () {
  const form = document.getElementById('formularioRegistro');
  const btnSubmit = document.getElementById('btnRegistrarse');
  let enviando = false;

  if (form) {
    form.addEventListener('submit', function (e) {
      // Si ya se está enviando la petición, abortar de inmediato cualquier clic posterior
      if (enviando) {
        e.preventDefault();
        e.stopPropagation();
        return false;
      }

      // 1. Prevenir envío si existen mensajes de error visibles activos de HTMX o validación previa
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

      // 2. Verificar la validez de inputs HTML5 estándar
      if (!form.checkValidity()) {
        return;
      }

      // 3. Activar bloqueo de envío múltiple
      enviando = true;

      if (btnSubmit) {
        // Usar setTimeout para permitir que el evento de submit termine su propagación en el navegador
        setTimeout(function () {
          btnSubmit.disabled = true;
          btnSubmit.classList.add('disabled');
          btnSubmit.style.pointerEvents = 'none';
          btnSubmit.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
            <span>Generando código de seguridad...</span>
          `;
        }, 0);
      }

      // 4. Temporizador de seguridad (15s): si la navegación no ocurre por error de red, restaurar el botón
      setTimeout(function () {
        enviando = false;
        if (btnSubmit) {
          btnSubmit.disabled = false;
          btnSubmit.classList.remove('disabled');
          btnSubmit.style.pointerEvents = 'auto';
          btnSubmit.innerHTML = 'Crear Cuenta';
        }
      }, 15000);
    });
  }
});
