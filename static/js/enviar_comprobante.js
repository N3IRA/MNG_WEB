document.addEventListener('DOMContentLoaded', function() {
    const imgComprobante = document.getElementById('id_imagen_comprobante');
    if (imgComprobante) {
        imgComprobante.addEventListener('change', function(event) {
            let previewContainer = document.getElementById('previewContainer');
            if (!previewContainer) {
                previewContainer = document.createElement('div');
                previewContainer.id = 'previewContainer';
                previewContainer.className = 'mt-3 d-none';
                previewContainer.innerHTML = `
                    <p class="small text-muted mb-2 fw-semibold"><i class="bi bi-eye text-success me-1"></i>Vista previa del comprobante cargado:</p>
                    <div class="rounded-4 border bg-dark bg-opacity-10 d-flex align-items-center justify-content-center p-2 shadow-sm overflow-hidden position-relative" style="height: 280px; max-width: 360px;">
                        <img id="previewImagen" class="rounded-3 shadow-sm" style="max-width: 100%; max-height: 100%; object-fit: contain;" alt="Vista previa de comprobante">
                    </div>
                    <small class="text-muted d-block mt-1">Verifica que la referencia, fecha y monto sean nítidos antes de enviar.</small>
                `;
                event.target.parentNode.appendChild(previewContainer);
            }
            const previewImage = document.getElementById('previewImagen');
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    previewImage.src = e.target.result;
                    previewContainer.classList.remove('d-none');
                }
                reader.readAsDataURL(file);
            } else {
                previewImage.src = '';
                previewContainer.classList.add('d-none');
            }
        });
    }

    const bancoOrigen = document.getElementById('id_banco_origen');
    if (bancoOrigen) {
        bancoOrigen.addEventListener('change', function() {
            const descField = document.getElementById('id_descripcion');
            if (descField) {
                if (this.value === 'Otro') {
                    descField.setAttribute('placeholder', 'Especifica tu banco o medio de pago aquí...');
                    descField.focus();
                } else {
                    descField.setAttribute('placeholder', 'Notas o Detalles Adicionales');
                }
            }
        });
    }

    const reservaSelect = document.getElementById('id_reserva');
    const montoDisplay = document.getElementById('id_monto_display');
    const reservaLabel = document.getElementById('id_reserva_label');
    const montoLabel = document.getElementById('id_monto_label');
    if (reservaSelect && montoDisplay) {
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
            const tipo = optionTipo === 'penalidad' ? 'Penalidad' : 'Reserva';

            if (selectedOpt && selectedOpt.dataset.monto) {
                montoDisplay.value = selectedOpt.dataset.monto;
                if (reservaLabel) {
                    reservaLabel.textContent = `${tipo} a Vincular *`;
                }
                if (montoLabel) {
                    montoLabel.textContent = `Monto de la ${tipo}`;
                }
            } else if (explicitTipo === 'penalidad') {
                montoDisplay.value = '';
                if (reservaLabel) {
                    reservaLabel.textContent = 'Penalidad a Vincular *';
                }
                if (montoLabel) {
                    montoLabel.textContent = 'Monto de la Penalidad';
                }
            } else {
                montoDisplay.value = '';
                if (reservaLabel) {
                    reservaLabel.textContent = 'Reserva a Vincular *';
                }
                if (montoLabel) {
                    montoLabel.textContent = 'Monto de la Reserva';
                }
            }
        };

        reservaSelect.addEventListener('change', updateMontoDisplay);
        selectInitialOption();
        updateMontoDisplay();
    }
});
