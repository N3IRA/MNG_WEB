/* otp.js - Lógica exclusiva para la verificación OTP, Restringe el input a solo números y muestra un spinner al enviar.*/

document.addEventListener('DOMContentLoaded', function () {
    var otpInput = document.getElementById('otp_input');
    var btnVerificar = document.getElementById('btn_verificar');
    var btnReenviar = document.getElementById('btn_reenviar_otp');
    var cuentaRegresiva = document.getElementById('cuenta_regresiva');
    var textoReenviar = document.getElementById('texto_reenviar');

    // Restricción: solo números en el campo OTP
    if (otpInput) {
        otpInput.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9]/g, '');
        });
    }

    // Spinner de carga al enviar el formulario OTP y prevenir doble envío
    if (otpInput && btnVerificar) {
        var form = otpInput.closest('form');
        if (form) {
            var enviandoOtp = false;
            form.addEventListener('submit', function (e) {
                if (enviandoOtp) {
                    e.preventDefault();
                    return false;
                }
                enviandoOtp = true;
                setTimeout(function () {
                    btnVerificar.disabled = true;
                    btnVerificar.classList.add('disabled');
                    btnVerificar.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status"></span>Verificando...';
                }, 0);
            });
        }
    }

    // Temporizador de enfriamiento para el botón de reenviar OTP
    if (btnReenviar && cuentaRegresiva) {
        var segundos = parseInt(btnReenviar.getAttribute('data-cooldown') || '0', 10);
        if (segundos > 0) {
            var intervalo = setInterval(function () {
                segundos--;
                if (segundos <= 0) {
                    clearInterval(intervalo);
                    btnReenviar.classList.remove('text-muted', 'pe-none');
                    btnReenviar.classList.add('link-success');
                    if (textoReenviar) {
                        textoReenviar.textContent = 'Reenviar código';
                    }
                } else {
                    cuentaRegresiva.textContent = segundos;
                }
            }, 1000);
        }
    }

    // Prevenir múltiples clics al reenviar código OTP
    if (btnReenviar) {
        btnReenviar.addEventListener('click', function (e) {
            if (btnReenviar.classList.contains('pe-none')) {
                e.preventDefault();
                return false;
            }
            btnReenviar.classList.add('text-muted', 'pe-none');
            btnReenviar.classList.remove('link-success');
            if (textoReenviar) {
                textoReenviar.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" style="width: 0.8rem; height: 0.8rem;"></span>Enviando...';
            }
        });
    }
});
