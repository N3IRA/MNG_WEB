function initTablaPagosRechazados() {
    var $tabla = $('#tablaPagosRechazados');
    if (!$tabla.length) return;

    if ($.fn.DataTable.isDataTable('#tablaPagosRechazados')) {
        $('#tablaPagosRechazados').DataTable().destroy();
    }

    $tabla.DataTable({
        order: [],
        autoWidth: false,
        columnDefs: [
            { orderable: false, targets: [0, 7] }, // No ordenar imagen (0) ni acciones (7)
            { className: "text-center", targets: [0, 3, 4, 6, 7] },
            { className: "text-start", targets: [1, 2, 5] }
        ],
        // 1. ESTRUCTURA VISUAL: Buscador alineado a la derecha
        dom: "<'row mb-3 align-items-center'<'col-12 d-flex justify-content-end'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 text-center text-md-start'i><'col-md-7 d-flex justify-content-md-end justify-content-center'p>>",

        // 2. BOTONES DE EXPORTACIÓN (Conectados al dropdown nativo Bootstrap 5)
        buttons: [
            {
                extend: 'excelHtml5',
                className: 'd-none btn-export-excel-hidden'
            },
            {
                extend: 'pdfHtml5',
                className: 'd-none btn-export-pdf-hidden'
            },
            {
                extend: 'print',
                className: 'd-none btn-export-print-hidden'
            }
        ],

        // 3. TRADUCCIÓN COMPLETA DE MONAGUA
        language: {
            sProcessing:     "Procesando...",
            sLengthMenu:     "Mostrar _MENU_ registros",
            sZeroRecords: "<div class='text-center p-4 text-muted'><i class='bi bi-search fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>No se encontraron pagos rechazados con ese criterio.</span></div>",
            sEmptyTable: "<div class='text-center p-4 text-muted'><i class='bi bi-shield-check fs-2 d-block mb-2 text-success'></i><span class='small fw-semibold'>No hay pagos rechazados registrados en el sistema.</span></div>",
            sInfo:           "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ pagos rechazados",
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
}

$(document).ready(function() {
    initTablaPagosRechazados();
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
