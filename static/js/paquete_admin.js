/**
 * paquete_admin.js
 * Lógica modular externa para la administración de paquetes turísticos en Monagua.
 * - Configura el token CSRF para peticiones asíncronas con HTMX.
 * - Gestiona la previsualización local segura de imágenes en el navegador antes de enviarlas al servidor.
 * - Toda la lógica de cálculo (días <-> noches) y renderizado de la tarjeta de vista previa
 *   se delega al servidor mediante HTMX para prevenir manipulación del cliente e inyecciones de código.
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Configuración de seguridad CSRF para HTMX
    document.body.addEventListener('htmx:configRequest', function (evt) {
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            evt.detail.headers['X-CSRFToken'] = csrfToken;
        }
    });

    // 2. Previsualización local de imagen mediante FileReader API
    initImagePreview();
});

function formatearTamanoArchivo(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const dm = 1;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function initImagePreview() {
    const inputImagen = document.querySelector('input[type="file"][name="imagen"]') || document.getElementById('id_imagen');
    if (!inputImagen) return;

    const previewPlaceholder = document.getElementById('preview-placeholder');
    const previewContainer = document.getElementById('preview-container');
    const imgDestinoPreview = document.getElementById('img-destino-preview');
    const previewImgName = document.getElementById('preview-img-name');
    const previewImgSize = document.getElementById('preview-img-size');
    const previewImgDim = document.getElementById('preview-img-dim');
    const badgeEstado = document.getElementById('badge-estado-img');
    const btnQuitar = document.getElementById('btn-quitar-imagen');

    // Elementos de edición (presentes en editar_paquete.html)
    const newImgInfo = document.getElementById('new-img-info');
    const inlineBox = document.getElementById('inline-preview-box');
    const inlineImg = document.getElementById('inline-preview-img');
    const inlineName = document.getElementById('inline-preview-name');
    const btnInlineRemove = document.getElementById('btn-inline-remove');
    const originalImgUrl = imgDestinoPreview ? imgDestinoPreview.getAttribute('data-original-url') || '' : '';

    function resetearPreviewCrear() {
        if (inputImagen) inputImagen.value = '';
        if (previewPlaceholder) previewPlaceholder.classList.remove('d-none');
        if (previewContainer) previewContainer.classList.add('d-none');
        if (badgeEstado) {
            badgeEstado.className = 'badge bg-secondary bg-opacity-10 text-secondary rounded-pill small px-2 py-1';
            badgeEstado.textContent = 'Sin archivo';
        }
    }

    function restaurarOriginalEditar() {
        if (inputImagen) inputImagen.value = '';
        if (originalImgUrl) {
            if (imgDestinoPreview) {
                imgDestinoPreview.src = originalImgUrl;
                imgDestinoPreview.classList.remove('d-none');
            }
            if (previewPlaceholder) previewPlaceholder.classList.add('d-none');
            if (badgeEstado) {
                badgeEstado.className = 'badge bg-secondary bg-opacity-10 text-secondary rounded-pill small px-2 py-1';
                badgeEstado.textContent = 'Actual';
            }
        } else {
            if (imgDestinoPreview) imgDestinoPreview.classList.add('d-none');
            if (previewPlaceholder) previewPlaceholder.classList.remove('d-none');
            if (badgeEstado) {
                badgeEstado.className = 'badge bg-secondary bg-opacity-10 text-secondary rounded-pill small px-2 py-1';
                badgeEstado.textContent = 'Sin imagen';
            }
        }
        if (previewImgSize) previewImgSize.classList.add('d-none');
        if (newImgInfo) newImgInfo.classList.add('d-none');
        if (inlineBox) inlineBox.classList.add('d-none');
    }

    inputImagen.addEventListener('change', function () {
        const file = this.files && this.files[0];
        if (file) {
            // Validación estricta de tipo MIME
            if (!file.type.startsWith('image/')) {
                alert('Por favor selecciona un archivo de imagen válido (JPG, PNG, WebP, etc.).');
                if (originalImgUrl !== undefined && originalImgUrl !== '') {
                    restaurarOriginalEditar();
                } else {
                    resetearPreviewCrear();
                }
                return;
            }

            const reader = new FileReader();
            reader.onload = function (event) {
                const dataUrl = event.target.result;

                if (imgDestinoPreview) {
                    imgDestinoPreview.src = dataUrl;
                    imgDestinoPreview.classList.remove('d-none');
                }
                if (previewPlaceholder) previewPlaceholder.classList.add('d-none');
                if (previewContainer) previewContainer.classList.remove('d-none');
                if (inlineImg) inlineImg.src = dataUrl;

                if (previewImgName) {
                    previewImgName.textContent = file.name;
                    previewImgName.title = file.name;
                }
                if (inlineName) {
                    inlineName.textContent = file.name;
                    inlineName.title = file.name;
                }
                if (previewImgSize) {
                    previewImgSize.textContent = formatearTamanoArchivo(file.size);
                    previewImgSize.classList.remove('d-none');
                }
                if (newImgInfo) newImgInfo.classList.remove('d-none');

                const imgObj = new Image();
                imgObj.onload = function () {
                    if (previewImgDim) previewImgDim.textContent = this.width + ' × ' + this.height + ' px';
                };
                imgObj.src = dataUrl;

                if (inlineBox) inlineBox.classList.remove('d-none');
                if (badgeEstado) {
                    badgeEstado.className = 'badge bg-success bg-opacity-10 text-success rounded-pill small px-2 py-1';
                    badgeEstado.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i>' + (originalImgUrl ? 'Nueva foto' : 'Seleccionada');
                }
            };
            reader.readAsDataURL(file);
        } else {
            if (originalImgUrl) {
                restaurarOriginalEditar();
            } else {
                resetearPreviewCrear();
            }
        }
    });

    if (btnQuitar) btnQuitar.addEventListener('click', resetearPreviewCrear);
    if (btnInlineRemove) btnInlineRemove.addEventListener('click', restaurarOriginalEditar);
}
