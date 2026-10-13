$(document).ready(function () {
    $('#tablaBlogs').DataTable({
        order: [],
        columnDefs: [
            { orderable: false, targets: 2 },
            { className: 'text-center', targets: [1, 2] }
        ],
        dom: "<'row mb-3 align-items-center'<'col-md-6'B><'col-md-6 d-flex justify-content-end'f>>" +
            "<'row'<'col-sm-12'tr>>" +
            "<'row mt-3'<'col-md-5'i><'col-md-7 d-flex justify-content-end'p>>",
        buttons: buildMonaguaExportButtons('Blogs', 'blogs'),
        language: {
            sProcessing: 'Procesando...',
            sLengthMenu: 'Mostrar _MENU_ registros',
            sZeroRecords: 'No se encontraron blogs para tu búsqueda.',
            sEmptyTable: 'No hay blogs registrados.',
            sInfo: 'Mostrando registros del _START_ al _END_ de un total de _TOTAL_ registros',
            sInfoEmpty: 'Mostrando registros del 0 al 0 de un total de 0 registros',
            sInfoFiltered: '(filtrado de un total de _MAX_ registros)',
            sSearch: 'Buscar:',
            sLoadingRecords: 'Cargando...',
            oPaginate: {
                sFirst: 'Primero',
                sLast: 'Último',
                sNext: 'Siguiente',
                sPrevious: 'Anterior'
            }
        },
        responsive: false,
        autoWidth: false,
        scrollX: false,
        scrollCollapse: false
    });
});
