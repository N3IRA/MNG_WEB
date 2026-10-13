$(document).ready(function () {
    $('#tablaCancelaciones').DataTable({
         order: [],
        // CONFIGURACIÓN CLAVE: Colocamos botones (B) y buscador (f) en la misma línea
        dom: "<'row mb-3 align-items-center'<'col-md-6'B><'col-md-6 d-flex justify-content-end'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3'<'col-md-5'i><'col-md-7 d-flex justify-content-end'p>>",

       buttons: buildMonaguaExportButtons('Cancelaciones', 'cancelaciones'),

        language: {
            sSearch: "Buscar:",
            sLengthMenu: "Mostrar _MENU_ registros",
            sInfo: "Mostrando _START_ a _END_ de _TOTAL_ registros",
            sZeroRecords: "<div class='text-center p-4 text-muted'><i class='bi bi-search fs-2 d-block mb-2 text-secondary'></i><span class='small fw-semibold'>No se encontraron resultados para tu búsqueda.</span></div>",
            sEmptyTable: "No hay datos disponibles"
        },

        responsive: false,
        autoWidth: true,
        scrollX: false,
        scrollCollapse: false
    });
});