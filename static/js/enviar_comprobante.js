document.addEventListener('DOMContentLoaded', function() {
    // ── 1. Vista previa interactiva y responsive del comprobante (Imagen o PDF) ──
    const imgComprobante = document.getElementById('id_imagen_comprobante');
    if (imgComprobante) {
        imgComprobante.addEventListener('change', function(event) {
            let previewContainer = document.getElementById('previewContainer');
            if (!previewContainer) {
                previewContainer = document.createElement('div');
                previewContainer.id = 'previewContainer';
                previewContainer.className = 'mt-3 d-none';
                event.target.closest('.border-dashed, .border')?.parentNode?.appendChild(previewContainer) || event.target.parentNode.appendChild(previewContainer);
            }

            const file = event.target.files && event.target.files[0];
            if (file) {
                const isPdf = file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
                const fileSizeMb = (file.size / (1024 * 1024)).toFixed(2);

                if (isPdf) {
                    previewContainer.innerHTML = `
                        <div class="p-3 bg-light rounded-4 border d-flex align-items-center justify-content-between gap-3 shadow-sm">
                            <div class="d-flex align-items-center gap-3">
                                <div class="bg-danger bg-opacity-10 text-danger rounded-3 p-2.5 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px;">
                                    <i class="bi bi-file-earmark-pdf-fill fs-3"></i>
                                </div>
                                <div class="overflow-hidden">
                                    <span class="fw-bold text-dark d-block text-truncate small">${file.name}</span>
                                    <span class="text-muted small">${fileSizeMb} MB · Documento PDF listo para validar</span>
                                </div>
                            </div>
                            <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25 rounded-pill px-3 py-1.5 small fw-semibold">
                                <i class="bi bi-check-circle me-1"></i>Adjuntado
                            </span>
                        </div>
                    `;
                    previewContainer.classList.remove('d-none');
                } else {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewContainer.innerHTML = `
                            <div class="p-3 bg-light rounded-4 border shadow-sm">
                                <div class="d-flex align-items-center justify-content-between mb-2">
                                    <span class="small text-dark fw-bold"><i class="bi bi-eye text-success me-1"></i>Vista previa del comprobante:</span>
                                    <span class="badge bg-light text-muted border rounded-pill px-2.5 py-1 small">${fileSizeMb} MB</span>
                                </div>
                                <div class="rounded-3 border bg-white d-flex align-items-center justify-content-center p-2 overflow-hidden position-relative mx-auto text-center" style="max-height: 280px; width: 100%;">
                                    <img id="previewImagen" src="${e.target.result}" class="rounded-2 shadow-sm img-fluid" style="max-height: 260px; max-width: 100%; object-fit: contain;" alt="Vista previa del comprobante">
                                </div>
                                <small class="text-muted d-block mt-2 text-center"><i class="bi bi-info-circle me-1 text-success"></i>Verifica que el número de referencia, fecha y valor sean completamente legibles.</small>
                            </div>
                        `;
                        previewContainer.classList.remove('d-none');
                    };
                    reader.readAsDataURL(file);
                }
            } else {
                previewContainer.innerHTML = '';
                previewContainer.classList.add('d-none');
            }
        });
    }

    // ── 2. Sugerencias dinámicas según Banco seleccionado ──
    const bancoOrigen = document.getElementById('id_banco_origen');
    if (bancoOrigen) {
        bancoOrigen.addEventListener('change', function() {
            const descField = document.getElementById('id_descripcion');
            if (descField) {
                if (this.value === 'Otro') {
                    descField.setAttribute('placeholder', 'Especifica el nombre de tu banco o medio de pago utilizado...');
                    descField.focus();
                } else {
                    descField.setAttribute('placeholder', 'Indica observaciones adicionales, titular de la cuenta o detalles del depósito...');
                }
            }
        });
    }

    // ── 3. Sincronización de Reserva Seleccionada y Valor Visual (Sin casilla de formulario) ──
    const reservaSelect = document.getElementById('id_reserva');
    const montoDisplay = document.getElementById('id_monto_display');
    const reservaLabel = document.getElementById('id_reserva_label');
    const montoValorTexto = document.getElementById('monto_valor_texto');
    const montoBadgeTipo = document.getElementById('monto_badge_tipo');
    const montoDetalleTexto = document.getElementById('monto_detalle_texto');
    const montoCardDisplay = document.getElementById('monto_card_display');

    if (reservaSelect) {
        const setPlaceholderText = function() {
            const explicitTipo = (reservaSelect.dataset.selectedTipo || '').toLowerCase();
            const tipo = explicitTipo === 'penalidad' ? 'penalidad' : 'reserva';
            const placeholderOpt = reservaSelect.options[0];
            if (placeholderOpt) {
                placeholderOpt.textContent = `— Selecciona la ${tipo} —`;
            }
        };

        const selectInitialOption = function() {
            const explicitTipo = (reservaSelect.dataset.selectedTipo || '').toLowerCase();
            const selectedId = (reservaSelect.dataset.selectedId || '').toString();
            setPlaceholderText();

            if (explicitTipo === 'penalidad') {
                const penaltyOpt = Array.from(reservaSelect.options).find(option => option.dataset.tipo === 'penalidad');
                if (penaltyOpt) {
                    reservaSelect.value = penaltyOpt.value;
                }
            } else if (selectedId) {
                const matchingOpt = Array.from(reservaSelect.options).find(option => option.value === selectedId);
                if (matchingOpt) {
                    reservaSelect.value = matchingOpt.value;
                }
            }
        };

        const updateMontoDisplay = function() {
            const explicitTipo = (reservaSelect.dataset.selectedTipo || '').toLowerCase();
            const selectedOpt = reservaSelect.options[reservaSelect.selectedIndex];
            const optionTipo = (selectedOpt && selectedOpt.dataset.tipo) ? selectedOpt.dataset.tipo.toLowerCase() : explicitTipo;
            const esPenalidad = optionTipo === 'penalidad';
            const tipo = esPenalidad ? 'Penalidad' : 'Reserva';

            if (selectedOpt && selectedOpt.dataset.monto) {
                const monto = selectedOpt.dataset.monto;
                const paquete = selectedOpt.dataset.paquete || '';
                const detalle = selectedOpt.dataset.detalle || '';

                // Actualizar input oculto para compatibilidad
                if (montoDisplay) {
                    montoDisplay.value = monto;
                }

                // Actualizar label de reserva
                if (reservaLabel) {
                    reservaLabel.innerHTML = `<i class="bi bi-calendar-check text-success me-1"></i>${tipo} a Vincular <span class="text-danger">*</span>`;
                }

                // Actualizar tarjeta visual destacada (NO casilla de formulario)
                if (montoValorTexto) {
                    montoValorTexto.textContent = monto;
                }
                if (montoBadgeTipo) {
                    montoBadgeTipo.textContent = esPenalidad ? 'Monto de la Penalidad' : 'Monto de la Reserva';
                }
                if (montoDetalleTexto) {
                    montoDetalleTexto.textContent = paquete ? `${paquete}${detalle ? ' · ' + detalle : ''}` : detalle || `${tipo} seleccionada`;
                }
                if (montoCardDisplay) {
                    montoCardDisplay.classList.remove('bg-light', 'border-secondary');
                    montoCardDisplay.classList.add('bg-success', 'bg-opacity-10', 'border-success', 'border-opacity-25');
                }
            } else {
                if (montoDisplay) {
                    montoDisplay.value = '';
                }
                if (reservaLabel) {
                    reservaLabel.innerHTML = `<i class="bi bi-calendar-check text-success me-1"></i>${tipo} a Vincular <span class="text-danger">*</span>`;
                }
                if (montoValorTexto) {
                    montoValorTexto.textContent = 'COP $0';
                }
                if (montoBadgeTipo) {
                    montoBadgeTipo.textContent = esPenalidad ? 'Monto de la Penalidad' : 'Monto de la Reserva';
                }
                if (montoDetalleTexto) {
                    montoDetalleTexto.textContent = 'Selecciona una reserva para visualizar el valor exacto';
                }
                if (montoCardDisplay) {
                    montoCardDisplay.classList.remove('bg-success', 'bg-opacity-10', 'border-success', 'border-opacity-25');
                    montoCardDisplay.classList.add('bg-light');
                }
            }
        };

        reservaSelect.addEventListener('change', updateMontoDisplay);
        selectInitialOption();
        updateMontoDisplay();
    }
});
