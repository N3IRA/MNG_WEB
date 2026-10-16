$(document).ready(function () {
    $('#tablaCancelaciones').DataTable({
        order: [],
        // 1. ESTRUCTURA VISUAL: Mantiene botones ocultos en DOM y buscador alineado a la derecha
        dom: "<'row mb-3 align-items-center'<'d-none'B><'col-12 d-flex justify-content-end'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 text-center text-md-start'i><'col-md-7 d-flex justify-content-md-end justify-content-center'p>>",

        // 2. BOTONES DE EXPORTACIÓN (Ocultos para ser disparados por el dropdown nativo)
        buttons: buildMonaguaExportButtons('Cancelaciones', 'cancelaciones', true),

        language: {
            sSearch: "Buscar:",
            sLengthMenu: "Mostrar _MENU_ registros",
            sInfo: "Mostrando _START_ a _END_ de _TOTAL_ registros",
            sZeroRecords: "<div class='text-center p-4 text-muted'><i class='bi bi-search fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>No se encontraron resultados para tu búsqueda.</span></div>",
            sEmptyTable: "<div class='text-center p-4 text-muted'><i class='bi bi-inbox fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>Aún no hay cancelaciones disponibles.</span></div>"
        },

        responsive: false,
        autoWidth: true,
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