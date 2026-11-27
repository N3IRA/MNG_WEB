(function () {
    // =========================================================================
    // CONFIGURACIÓN EXPANDIDA DE ACCIONES Y TIPOS PARA NOTIFICACIONES DE BITÁCORA
    // =========================================================================
    const CONFIG_TOAST = {
      // ── Acciones de Negocio Principales ──
      reserva: {
        titulo: '¡Acción de Reserva!',
        colorTexto: '#1e4a2a',
        colorFondoIcono: 'rgba(44, 110, 60, 0.14)',
        colorIcono: '#2c6e3c',
        icono: 'bi-calendar2-check-fill',
        colorBarra: '#2c6e3c'
      },
      comprobante: {
        titulo: '¡Comprobante de Pago!',
        colorTexto: '#0f766e',
        colorFondoIcono: 'rgba(15, 118, 110, 0.14)',
        colorIcono: '#0f766e',
        icono: 'bi-receipt-cutoff',
        colorBarra: '#0f766e'
      },
      pago: {
        titulo: '¡Gestión de Pago!',
        colorTexto: '#1d4ed8',
        colorFondoIcono: 'rgba(13, 110, 253, 0.14)',
        colorIcono: '#0d6efd',
        icono: 'bi-credit-card-2-front-fill',
        colorBarra: '#0d6efd'
      },
      reembolso: {
        titulo: '¡Reembolso Bancario!',
        colorTexto: '#92400e',
        colorFondoIcono: 'rgba(217, 119, 6, 0.14)',
        colorIcono: '#d97706',
        icono: 'bi-cash-coin',
        colorBarra: '#d97706'
      },
      cancelacion: {
        titulo: '¡Cancelación de Reserva!',
        colorTexto: '#991b1b',
        colorFondoIcono: 'rgba(220, 53, 69, 0.14)',
        colorIcono: '#dc3545',
        icono: 'bi-x-circle-fill',
        colorBarra: '#dc3545'
      },
      exportar: {
        titulo: '¡Exportación de Datos!',
        colorTexto: '#0369a1',
        colorFondoIcono: 'rgba(2, 132, 199, 0.14)',
        colorIcono: '#0284c7',
        icono: 'bi-cloud-arrow-down-fill',
        colorBarra: '#0284c7'
      },
      descarga: {
        titulo: '¡Descarga de Reporte!',
        colorTexto: '#0369a1',
        colorFondoIcono: 'rgba(2, 132, 199, 0.14)',
        colorIcono: '#0284c7',
        icono: 'bi-file-earmark-arrow-down-fill',
        colorBarra: '#0284c7'
      },
      copiar: {
        titulo: '¡Copiado al Portapapeles!',
        colorTexto: '#6d28d9',
        colorFondoIcono: 'rgba(124, 58, 237, 0.14)',
        colorIcono: '#7c3aed',
        icono: 'bi-clipboard-check-fill',
        colorBarra: '#7c3aed'
      },
      guia: {
        titulo: '¡Gestión de Guía!',
        colorTexto: '#9a3412',
        colorFondoIcono: 'rgba(234, 88, 12, 0.14)',
        colorIcono: '#ea580c',
        icono: 'bi-person-badge-fill',
        colorBarra: '#ea580c'
      },
      usuario: {
        titulo: '¡Gestión de Usuario!',
        colorTexto: '#0e7490',
        colorFondoIcono: 'rgba(8, 145, 178, 0.14)',
        colorIcono: '#0891b2',
        icono: 'bi-person-check-fill',
        colorBarra: '#0891b2'
      },
      bitacora: {
        titulo: '¡Registro en Bitácora!',
        colorTexto: '#3730a3',
        colorFondoIcono: 'rgba(79, 70, 229, 0.14)',
        colorIcono: '#4f46e5',
        icono: 'bi-journal-check',
        colorBarra: '#4f46e5'
      },
      filtro: {
        titulo: '¡Búsqueda y Filtros!',
        colorTexto: '#334155',
        colorFondoIcono: 'rgba(71, 85, 105, 0.14)',
        colorIcono: '#475569',
        icono: 'bi-funnel-fill',
        colorBarra: '#475569'
      },
      paquete: {
        titulo: '¡Gestión de Paquete!',
        colorTexto: '#14532d',
        colorFondoIcono: 'rgba(44, 110, 60, 0.14)',
        colorIcono: '#2c6e3c',
        icono: 'bi-backpack-fill',
        colorBarra: '#2c6e3c'
      },
      categoria: {
        titulo: '¡Gestión de Categoría!',
        colorTexto: '#14532d',
        colorFondoIcono: 'rgba(21, 128, 61, 0.14)',
        colorIcono: '#15803d',
        icono: 'bi-tags-fill',
        colorBarra: '#15803d'
      },
      actividad: {
        titulo: '¡Gestión de Actividad!',
        colorTexto: '#0f766e',
        colorFondoIcono: 'rgba(13, 148, 136, 0.14)',
        colorIcono: '#0d9488',
        icono: 'bi-compass-fill',
        colorBarra: '#0d9488'
      },
      tarifa: {
        titulo: '¡Gestión de Tarifa!',
        colorTexto: '#15803d',
        colorFondoIcono: 'rgba(22, 163, 74, 0.14)',
        colorIcono: '#16a34a',
        icono: 'bi-currency-exchange',
        colorBarra: '#16a34a'
      },
      temporada: {
        titulo: '¡Gestión de Temporada!',
        colorTexto: '#0369a1',
        colorFondoIcono: 'rgba(2, 132, 199, 0.14)',
        colorIcono: '#0284c7',
        icono: 'bi-calendar3-range-fill',
        colorBarra: '#0284c7'
      },
      blog: {
        titulo: '¡Gestión de Blog!',
        colorTexto: '#3730a3',
        colorFondoIcono: 'rgba(79, 70, 229, 0.14)',
        colorIcono: '#4f46e5',
        icono: 'bi-journal-richtext',
        colorBarra: '#4f46e5'
      },
      promocion: {
        titulo: '¡Gestión de Promoción!',
        colorTexto: '#6b21a8',
        colorFondoIcono: 'rgba(168, 85, 247, 0.14)',
        colorIcono: '#9333ea',
        icono: 'bi-megaphone-fill',
        colorBarra: '#9333ea'
      },
      calificacion: {
        titulo: '¡Opinión y Calificación!',
        colorTexto: '#b45309',
        colorFondoIcono: 'rgba(245, 158, 11, 0.14)',
        colorIcono: '#d97706',
        icono: 'bi-star-fill',
        colorBarra: '#d97706'
      },
      pqrs: {
        titulo: '¡Atención y PQRS!',
        colorTexto: '#9f1239',
        colorFondoIcono: 'rgba(225, 29, 72, 0.14)',
        colorIcono: '#e11d48',
        icono: 'bi-chat-heart-fill',
        colorBarra: '#e11d48'
      },

      // ── Estados Genéricos del Sistema ──
      success: {
        titulo: '¡Operación Exitosa!',
        colorTexto: '#1e4a2a',
        colorFondoIcono: 'rgba(44, 110, 60, 0.12)',
        colorIcono: '#2c6e3c',
        icono: 'bi-check-circle-fill',
        colorBarra: '#2c6e3c'
      },
      error: {
        titulo: '¡Atención - Error!',
        colorTexto: '#991b1b',
        colorFondoIcono: 'rgba(220, 53, 69, 0.12)',
        colorIcono: '#dc3545',
        icono: 'bi-exclamation-octagon-fill',
        colorBarra: '#dc3545'
      },
      danger: {
        titulo: '¡Atención - Error!',
        colorTexto: '#991b1b',
        colorFondoIcono: 'rgba(220, 53, 69, 0.12)',
        colorIcono: '#dc3545',
        icono: 'bi-exclamation-octagon-fill',
        colorBarra: '#dc3545'
      },
      warning: {
        titulo: '¡Advertencia!',
        colorTexto: '#92400e',
        colorFondoIcono: 'rgba(245, 158, 11, 0.14)',
        colorIcono: '#d97706',
        icono: 'bi-exclamation-triangle-fill',
        colorBarra: '#f59e0b'
      },
      info: {
        titulo: 'Notificación del Sistema',
        colorTexto: '#075985',
        colorFondoIcono: 'rgba(2, 132, 199, 0.12)',
        colorIcono: '#0284c7',
        icono: 'bi-info-circle-fill',
        colorBarra: '#0284c7'
      },
      offline: {
        titulo: 'Sin conexión',
        colorTexto: '#991b1b',
        colorFondoIcono: 'rgba(220, 53, 69, 0.12)',
        colorIcono: '#dc3545',
        icono: 'bi-wifi-off',
        colorBarra: '#dc3545'
      },
      online: {
        titulo: 'Conexión restablecida',
        colorTexto: '#1e4a2a',
        colorFondoIcono: 'rgba(44, 110, 60, 0.12)',
        colorIcono: '#2c6e3c',
        icono: 'bi-wifi',
        colorBarra: '#2c6e3c'
      }
    };

    /**
     * Función global para crear y disparar un Toast superior derecho con temporizador
     * @param {string} tipo - Tipo de acción ('reserva', 'pago', 'comprobante', 'reembolso', 'cancelacion', 'exportar', 'copiar', 'usuario', 'success', 'error', etc.)
     * @param {string} titulo - Título opcional (si no se especifica, usa el título por defecto del tipo)
     * @param {string} mensaje - Mensaje descriptivo de la acción
     * @param {number} duracion - Duración en milisegundos (por defecto 5000)
     */
    window.mostrarToast = function (tipo, titulo, mensaje, duracion) {
      duracion = duracion || 5000;
      tipo = (tipo || 'info').toLowerCase();
      if (!CONFIG_TOAST[tipo]) tipo = 'info';

      const conf = CONFIG_TOAST[tipo];
      const tituloFinal = titulo || conf.titulo;
      const mensajeFinal = mensaje || '';

      // Obtener o crear contenedor
      let container = document.getElementById('monaguaToastContainer');
      if (!container) {
        container = document.createElement('div');
        container.id = 'monaguaToastContainer';
        container.className = 'toast-container position-fixed top-0 end-0 p-3';
        container.style.cssText = 'z-index: 99999; max-width: 420px; width: 100%; pointer-events: none;';
        document.body.appendChild(container);
      }

      // Crear elemento Toast
      const toastEl = document.createElement('div');
      toastEl.className = 'toast monagua-toast-item border-0 shadow-lg mb-3';
      toastEl.setAttribute('role', 'alert');
      toastEl.setAttribute('aria-live', 'assertive');
      toastEl.setAttribute('aria-atomic', 'true');
      toastEl.style.cssText = 'pointer-events: auto; border-radius: 16px; overflow: hidden; background: rgba(255, 255, 255, 0.98); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); border: 1px solid rgba(0, 0, 0, 0.08);';

      toastEl.innerHTML = `
        <div class="d-flex align-items-center p-3">
          <div class="me-3 d-flex align-items-center justify-content-center rounded-circle flex-shrink-0" style="width: 42px; height: 42px; background-color: ${conf.colorFondoIcono}; color: ${conf.colorIcono};">
            <i class="bi ${conf.icono} fs-5"></i>
          </div>
          <div class="flex-grow-1 text-dark pe-2">
            <div class="fw-bold mb-0 text-start" style="font-size: 0.95rem; color: ${conf.colorTexto};">${tituloFinal}</div>
            <div class="small text-secondary mt-1 text-start" style="line-height: 1.35; font-size: 0.85rem;">${mensajeFinal}</div>
          </div>
          <button type="button" class="btn-close ms-auto align-self-start" data-bs-dismiss="toast" aria-label="Cerrar" style="font-size: 0.75rem;"></button>
        </div>
        <div class="toast-progress-track" style="height: 4px; width: 100%; background: rgba(0, 0, 0, 0.05); overflow: hidden;">
          <div class="toast-progress-bar" style="height: 100%; width: 100%; animation: monaguaToastTimer ${duracion}ms linear forwards; background-color: ${conf.colorBarra};"></div>
        </div>
      `;

      container.appendChild(toastEl);

      if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
        const bsToast = new bootstrap.Toast(toastEl, {
          autohide: true,
          delay: duracion
        });

        toastEl.addEventListener('hidden.bs.toast', function () {
          toastEl.remove();
        });

        bsToast.show();
      } else {
        // Fallback básico si Bootstrap JS no ha cargado
        toastEl.classList.add('show');
        setTimeout(function () {
          toastEl.remove();
        }, duracion);
      }
    };

    /**
     * Alias semántico para registrar y mostrar acciones de bitácora
     * @param {string} accion - Tipo de acción ('reserva', 'pago', 'exportar', 'usuario', etc.)
     * @param {string} mensaje - Mensaje a mostrar
     * @param {object} opciones - { titulo, duracion }
     */
    window.notificarBitacora = function (accion, mensaje, opciones) {
      opciones = opciones || {};
      window.mostrarToast(accion, opciones.titulo, mensaje, opciones.duracion || 5000);
    };

    // =========================================================================
    // LISTENERS GLOBALES Y AUTO-CAPTURA DE ACCIONES DEL USUARIO (ADMIN Y TURISTA)
    // =========================================================================
    document.addEventListener('DOMContentLoaded', function () {
      // 1. Inicializar Toasts provenientes del servidor (Django Messages)
      const serverToasts = document.querySelectorAll('#monaguaToastContainer .toast');
      serverToasts.forEach(function (toastEl) {
        if (typeof bootstrap !== 'undefined' && bootstrap.Toast) {
          const bsToast = new bootstrap.Toast(toastEl, {
            autohide: true,
            delay: 5000
          });
          toastEl.addEventListener('hidden.bs.toast', function () {
            toastEl.remove();
          });
          bsToast.show();
        }
      });

      // 2. Monitoreo del estado de conexión a Internet
      window.addEventListener('offline', function () {
        window.mostrarToast('offline', 'Sin conexión', 'En este momento has perdido la conexión a internet.', 6000);
      });

      window.addEventListener('online', function () {
        window.mostrarToast('online', 'Conexión restablecida', 'Se ha restablecido la conexión a internet correctamente.', 5000);
      });

      // 3. Listener para eventos personalizados de Bitácora (usados por HTMX o JS del proyecto)
      document.addEventListener('mostrarNotificacionBitacora', function (evt) {
        const data = evt.detail || {};
        window.mostrarToast(
          data.tipo || 'info',
          data.titulo || null,
          data.mensaje || data.texto || 'Acción registrada en la plataforma.',
          data.duracion || 5000
        );
      });

      document.addEventListener('bitacora:accion', function (evt) {
        const data = evt.detail || {};
        window.mostrarToast(
          data.tipo || data.accion || 'info',
          data.titulo || null,
          data.mensaje || 'Acción registrada en bitácora.',
          data.duracion || 5000
        );
      });

      // 4. Captura automática de acciones en botones de Exportación (Excel, PDF, Imprimir)
      document.addEventListener('click', function (e) {
        const target = e.target.closest(
          '.btn-export-excel-trigger, .btn-export-pdf-trigger, .btn-export-print-trigger, ' +
          '.buttons-excel, .buttons-pdf, .buttons-print, [data-export]'
        );
        if (!target) return;

        const isExcel = target.classList.contains('btn-export-excel-trigger') ||
                        target.classList.contains('buttons-excel') ||
                        target.dataset.export === 'excel' ||
                        target.innerText.toLowerCase().includes('excel');

        const isPdf = target.classList.contains('btn-export-pdf-trigger') ||
                      target.classList.contains('buttons-pdf') ||
                      target.dataset.export === 'pdf' ||
                      target.innerText.toLowerCase().includes('pdf');

        const isPrint = target.classList.contains('btn-export-print-trigger') ||
                        target.classList.contains('buttons-print') ||
                        target.dataset.export === 'print' ||
                        target.innerText.toLowerCase().includes('imprimir');

        if (isExcel) {
          window.mostrarToast('exportar', 'Exportando a Excel', 'Generando y preparando el archivo .xlsx con los registros...', 3500);
        } else if (isPdf) {
          window.mostrarToast('exportar', 'Generando Documento PDF', 'Compilando informe oficial en PDF para su descarga...', 3500);
        } else if (isPrint) {
          window.mostrarToast('exportar', 'Impresión de Reporte', 'Abriendo la vista de impresión con formato institucional...', 3000);
        }
      });

      // 5. Captura automática para botones con data-bitacora-toast o data-copiar
      document.addEventListener('click', function (e) {
        // Elementos con data-bitacora-toast
        const btnToast = e.target.closest('[data-bitacora-toast]');
        if (btnToast) {
          const tipo = btnToast.getAttribute('data-bitacora-tipo') || 'info';
          const titulo = btnToast.getAttribute('data-bitacora-titulo') || null;
          const mensaje = btnToast.getAttribute('data-bitacora-toast');
          window.mostrarToast(tipo, titulo, mensaje, 4000);
          return;
        }

        // Elementos de copia al portapapeles
        const btnCopiar = e.target.closest('[data-copiar], .btn-copiar, .btn-copy');
        if (btnCopiar) {
          const texto = btnCopiar.getAttribute('data-copiar') || btnCopiar.dataset.texto || '';
          if (texto && navigator.clipboard) {
            navigator.clipboard.writeText(texto).then(function () {
              window.mostrarToast('copiar', 'Copiado al Portapapeles', 'El valor "' + texto + '" fue copiado exitosamente.', 3000);
            }).catch(function () {});
          } else {
            window.mostrarToast('copiar', 'Copiado al Portapapeles', 'Información copiada con éxito.', 3000);
          }
        }

        // Botón de restablecer o limpiar filtros
        const btnResetFiltro = e.target.closest('a[href*="listar_"][title*="Limpiar"], .btn-reset-filtros, a.btn-outline-secondary:has(.bi-arrow-clockwise)');
        if (btnResetFiltro) {
          window.mostrarToast('filtro', 'Filtros Restablecidos', 'Cargando listado completo sin filtros aplicados...', 2500);
        }
      });

      // 6. Monitoreo y feedback inteligente en envíos de formularios clave
      document.addEventListener('submit', function (e) {
        const form = e.target;
        if (!form) return;

        const formId = form.id || '';
        const action = form.getAttribute('action') || '';

        // Formulario de revisión de comprobante
        if (formId === 'formRevisarComprobante' || action.includes('revisar')) {
          const decision = form.querySelector('input[name="estado_transaccion"]:checked')?.value;
          if (decision === 'aprobado') {
            window.mostrarToast('comprobante', 'Procesando Aprobación', 'Validando comprobante y confirmando la reserva asociada...', 4500);
          } else if (decision === 'rechazado') {
            window.mostrarToast('comprobante', 'Procesando Rechazo', 'Registrando rechazo de comprobante y notificando al cliente...', 4500);
          }
        }
        // Formulario de dictamen de cancelación
        else if (formId === 'formEditarCancelacion' || action.includes('cancelacion')) {
          const dictamen = form.querySelector('#selectEstadoCancelacion')?.value;
          if (dictamen === 'aprobada') {
            window.mostrarToast('cancelacion', 'Dictamen de Cancelación', 'Aprobando cancelación y procesando cálculo financiero...', 4500);
          } else if (dictamen === 'rechazada') {
            window.mostrarToast('cancelacion', 'Dictamen de Cancelación', 'Registrando rechazo de solicitud y reactivando reserva...', 4500);
          }
        }
        // Formulario de desembolso / transferencia de reembolso
        else if (action.includes('reembolso')) {
          window.mostrarToast('reembolso', 'Registrando Transferencia', 'Guardando comprobante bancario en bitácora de desembolsos...', 4500);
        }
        // Formulario de envío de comprobante del turista
        else if (action.includes('enviar_comprobante') || formId === 'formEnviarComprobante') {
          window.mostrarToast('pago', 'Enviando Comprobante', 'Subiendo soporte de pago para revisión administrativa...', 5000);
        }
      });

      // 7. Integración con HTMX para capturar errores de servidor o desconexión
      document.addEventListener('htmx:responseError', function (evt) {
        const xhr = evt.detail && evt.detail.xhr;
        const status = xhr ? xhr.status : 500;
        window.mostrarToast('error', 'Error en el Servidor (' + status + ')', 'No fue posible completar la solicitud. Por favor intenta nuevamente.', 5000);
      });

      document.addEventListener('htmx:sendError', function () {
        window.mostrarToast('offline', 'Error de Comunicación', 'No se pudo conectar con el servidor. Revisa tu conexión a internet.', 5000);
      });
    });
})();
