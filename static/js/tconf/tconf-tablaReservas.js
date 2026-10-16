$(document).ready(function() {
    $('#tablaReservas').DataTable({
        order: [],
        autoWidth: false,
        columnDefs: [
            { orderable: false, targets: 5 }, // No ordenar columna de acciones
            { className: "text-center", targets: [2, 3, 4, 5] }
        ],
        // 1. ESTRUCTURA VISUAL: Mantiene botones ocultos en DOM y buscador alineado a la derecha
        dom: "<'row mb-3 align-items-center'<'d-none'B><'col-12 d-flex justify-content-end'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 text-center text-md-start'i><'col-md-7 d-flex justify-content-md-end justify-content-center'p>>",

        // 2. BOTONES DE EXPORTACIÓN (Ocultos para ser disparados por el dropdown nativo)
        buttons: buildMonaguaExportButtons('Reservas', 'reservas', true),

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
});

// Vincular botones del Dropdown nativo Bootstrap 5 con las acciones de exportación de DataTables
$(document).on('click', '.btn-export-excel-trigger, #btn-export-excel', function(e) {
    e.preventDefault();
    $('.btn-export-excel-hidden').trigger('click');
});

$(document).on('click', '.btn-export-pdf-trigger, #btn-export-pdf', function(e) {
    e.preventDefault();
    $('.btn-export-pdf-hidden').trigger('click');
});

$(document).on('click', '.btn-export-print-trigger, #btn-export-print', function(e) {
    e.preventDefault();
    $('.btn-export-print-hidden').trigger('click');
});
