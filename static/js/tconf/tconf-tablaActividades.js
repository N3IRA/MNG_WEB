$(document).ready(function() {
    $('#tablaActividades').DataTable({
        order: [],
        // Estructura DOM corregida para asegurar que el buscador ('f') mantenga los eventos de foco y tipeo
        dom: "<'row mb-3 align-items-center'<'col-md-6 mb-2 mb-md-0'B><'col-md-6 d-flex justify-content-md-end justify-content-start'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 mb-2 mb-md-0'i><'col-md-7 d-flex justify-content-md-end justify-content-start'p>>",

        buttons: buildMonaguaExportButtons('Actividades', 'actividades'),

        language: {
            sProcessing:    "Procesando...",
            sLengthMenu:    "Mostrar _MENU_ registros",
            sZeroRecords: "<div class='text-center p-4 text-muted'><i class='bi bi-search fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>No se encontraron resultados para tu búsqueda.</span></div>",
            sEmptyTable: "<div class='text-center p-4 text-muted'><i class='bi bi-inbox fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>Aún no hay registros disponibles.</span></div>",
            sInfo:          "Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros",
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

        responsive: false,
        autoWidth: true,
        scrollX: false,
        scrollCollapse: false
    });
});
