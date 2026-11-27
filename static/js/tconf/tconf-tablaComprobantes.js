var _comprobantesDtState = {
    search: '',
    page: 0
};

function initTablaComprobantes(savedState) {
    var $tabla = $('#tablaComprobantes');
    if (!$tabla.length) return;

    if ($.fn.DataTable.isDataTable('#tablaComprobantes')) {
        $('#tablaComprobantes').DataTable().destroy();
    }

    var dt = $tabla.DataTable({
        order: [],
        autoWidth: false,
        columnDefs: [
            { orderable: false, targets: [0, 7] }, // No ordenar imagen ni acciones
            { className: "text-center", targets: [0, 3, 4, 5, 6, 7] }
        ],
        // 1. ESTRUCTURA VISUAL: Mantiene botones y buscador alineados
        dom: "<'row mb-3 align-items-center'<'d-none'B><'col-12 d-flex justify-content-end'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 text-center text-md-start'i><'col-md-7 d-flex justify-content-md-end justify-content-center'p>>",

        // 2. BOTONES DE EXPORTACIÓN
        buttons: buildMonaguaExportButtons('Comprobantes', 'comprobantes', true),

        // 3. TRADUCCIÓN COMPLETA DE TU PROYECTO MONAGUA
        language: {
            sProcessing:     "Procesando...",
            sLengthMenu:     "Mostrar _MENU_ registros",
            sZeroRecords: "<div class='text-center p-4 text-muted'><i class='bi bi-search fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>No se encontraron resultados para tu búsqueda.</span></div>",
            sEmptyTable: "<div class='text-center p-4 text-muted'><i class='bi bi-inbox fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>Aún no hay registros disponibles.</span></div>",
            sInfo:           "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
            sInfoEmpty:      "Mostrando registros del 0 al 0 de un total de 0 registros",
            sInfoFiltered:   "(filtrado de un total de _MAX_ registros)",
            sInfoPostFix:    "",
            sSearch:         "Buscar:",
            sUrl:            "",
            sInfoThousands:  ",",
            sLoadingRecords: "Cargando...",
            oPaginate: {
                sFirst:    "Primero",
                sLast:     "Último",
                sNext:     "Siguiente",
                sPrevious: "Anterior"
            },
            oAria: {
                sSortAscending:  ": Activar para ordenar la columna de manera ascendente",
                sSortDescending: ": Activar para ordenar la columna de manera descendente"
            }
        },

        // 4. CONFIGURACIÓN DE AJUSTES Y RESPONSIVE
        responsive: false,
        scrollX: false,
        scrollCollapse: false
    });

    // Restaurar búsqueda y página si venimos de una actualización HTMX
    if (savedState) {
        if (savedState.search) {
            dt.search(savedState.search);
        }
        if (savedState.page && savedState.page > 0) {
            var info = dt.page.info();
            var targetPage = Math.min(savedState.page, Math.max(info.pages - 1, 0));
            dt.page(targetPage);
        }
        dt.draw(false);
    }
}

$(document).ready(function() {
    initTablaComprobantes(null);
});

// Preservar estado de DataTables SOLO si HTMX realmente va a reemplazar el DOM (ignorar 204 No Content)
document.body.addEventListener('htmx:beforeSwap', function(evt) {
    if (!evt.detail || !evt.detail.shouldSwap) return;
    if (evt.detail.xhr && evt.detail.xhr.status === 204) return;
    if (evt.detail.target && evt.detail.target.id === 'admin-comprobantes-container') {
        var $tabla = $('#tablaComprobantes');
        if ($tabla.length && $.fn.DataTable.isDataTable($tabla)) {
            var dt = $tabla.DataTable();
            _comprobantesDtState.search = dt.search() || '';
            _comprobantesDtState.page = dt.page() || 0;
            dt.destroy();
        }
    }
});

// Reinicializar DataTables tras actualización asíncrona de HTMX
document.body.addEventListener('htmx:afterSettle', function(evt) {
    if (evt.detail && evt.detail.xhr && evt.detail.xhr.status === 204) return;
    if (document.getElementById('tablaComprobantes') && !$.fn.DataTable.isDataTable('#tablaComprobantes')) {
        initTablaComprobantes(_comprobantesDtState);
    }
});

// Vincular botones del Dropdown nativo Bootstrap 5 con las acciones de exportación de DataTables
$(document).on('click', '#btn-export-excel', function(e) {
    e.preventDefault();
    $('.btn-export-excel-hidden').trigger('click');
});

$(document).on('click', '#btn-export-pdf', function(e) {
    e.preventDefault();
    $('.btn-export-pdf-hidden').trigger('click');
});

$(document).on('click', '#btn-export-print', function(e) {
    e.preventDefault();
    $('.btn-export-print-hidden').trigger('click');
});

// Ajuste automático de columnas en caso de redimensión de pantalla o cambio de orientación
$(window).on('resize orientationchange', function() {
    if ($.fn.DataTable.isDataTable('#tablaComprobantes')) {
        $('#tablaComprobantes').DataTable().columns.adjust();
    }
});
