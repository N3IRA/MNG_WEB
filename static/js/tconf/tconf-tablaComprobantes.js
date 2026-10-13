function buildMonaguaExportButtons(title, slug) {
    const fechaReporte = new Date().toLocaleDateString('es-CO', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    return [
        {
            extend: 'excelHtml5',
            text: '<i class="bi bi-file-earmark-excel-fill text-success fs-5"></i>',
            titleAttr: 'Exportar a Excel',
            title: title,
            filename: slug + '-' + new Date().toISOString().slice(0, 10),
            className: 'btn btn-light rounded-circle shadow-sm border-0 mx-1 d-flex align-items-center justify-content-center p-0',
            attr: {
                style: 'width:48px;height:48px;flex-shrink: 0;'
            },
            exportOptions: {
                columns: ':visible'
            },
            customize: function (xlsx) {
                const worksheetXml = xlsx.xl.worksheets['sheet1.xml'];
                const titleRow = '<row r="1"><c r="A1" t="inlineStr"><is><t>MONAGUA</t></is></c></row>';
                const subtitleRow = '<row r="2"><c r="A2" t="inlineStr"><is><t>' + title + '</t></is></c></row>';

                xlsx.xl.worksheets['sheet1.xml'] = worksheetXml.replace(/<sheetData>[\s\S]*?<\/sheetData>/, function (match) {
                    const inner = match.replace(/^<sheetData>|<\/sheetData>$/g, '');
                    return '<sheetData>' + titleRow + subtitleRow + inner + '</sheetData>';
                });
            }
        },
        {
            extend: 'pdfHtml5',
            text: '<i class="bi bi-file-earmark-pdf-fill text-dark fs-5"></i>',
            titleAttr: 'Exportar a PDF',
            title: title,
            filename: slug + '-' + new Date().toISOString().slice(0, 10),
            className: 'btn btn-light rounded-circle shadow-sm border-0 mx-1 d-flex align-items-center justify-content-center p-0',
            attr: {
                style: 'width:48px;height:48px; flex-shrink: 0;'
            },
            exportOptions: {
                columns: ':visible'
            },
            customize: function (doc) {
                doc.pageMargins = [15, 35, 15, 20];
                doc.defaultStyle = {
                    font: 'helvetica',
                    fontSize: 9,
                    color: '#1a261f'
                };
                doc.styles = Object.assign({}, doc.styles || {}, {
                    tableHeader: {
                        fillColor: [44, 110, 60],
                        textColor: [255, 255, 255],
                        fontSize: 9,
                        bold: true,
                        halign: 'center'
                    },
                    tableBodyEven: { fillColor: [240, 246, 242] },
                    tableBodyOdd: { fillColor: [255, 255, 255] }
                });

                doc.content.unshift(
                    { text: 'MONAGUA', fontSize: 18, bold: true, color: '#005215', margin: [0, 0, 0, 2] },
                    { text: title, fontSize: 12, bold: true, color: '#1a261f', margin: [0, 0, 0, 5] },
                    { text: 'Generado: ' + fechaReporte, fontSize: 8, color: '#406d46', margin: [0, 0, 0, 10] }
                );
            }
        },
        {
            extend: 'print',
            text: '<i class="bi bi-printer-fill text-dark fs-5"></i>',
            titleAttr: 'Imprimir',
            title: title,
            className: 'btn btn-light rounded-circle shadow-sm border-0 mx-1 d-flex align-items-center justify-content-center p-0',
            attr: {
                style: 'width:48px;height:48px; flex-shrink: 0;'
            },
            exportOptions: {
                columns: ':visible'
            },
            customize: function (win) {
                $(win.document.body).prepend(
                    '<div class="monagua-print-header" style="display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 20px;border-bottom:4px solid #2c6e3c;background:linear-gradient(135deg,#d1e7dd,#ffffff);margin-bottom:20px;border-radius:14px 14px 0 0;">' +
                    '<div style="display:flex;align-items:center;gap:12px;">' +
                    '<img src="/static/img/logo_monagua.webp" alt="Monagua" style="height:46px;width:auto;object-fit:contain;">' +
                    '<div>' +
                    '<div style="font-size:22px;font-weight:800;letter-spacing:0.04em;color:#005215;">MONAGUA</div>' +
                    '<div style="font-size:12px;color:#406d46;">' + title + '</div>' +
                    '</div>' +
                    '</div>' +
                    '<div style="font-size:11px;font-weight:600;color:#1a261f;">' + fechaReporte + '</div>' +
                    '</div>'
                );

                $(win.document.body).find('table').css({
                    'border-collapse': 'collapse',
                    'width': '100%',
                    'font-size': '12px',
                    'color': '#1a261f'
                });

                $(win.document.body).find('thead th').css({
                    'background-color': '#2c6e3c',
                    'color': '#ffffff',
                    'font-weight': '700',
                    'padding': '10px 8px',
                    'border': '1px solid #1a261f'
                });

                $(win.document.body).find('tbody td').css({
                    'padding': '8px',
                    'border': '1px solid #dfe7df'
                });
            }
        }
    ];
}

$(document).ready(function() {
    $('#tablaComprobantes').DataTable({
        order: [],
        autoWidth: false,
        columnDefs: [
            { orderable: false, targets: [0, 7] }, // No ordenar imagen ni acciones
            { className: "text-center", targets: [0, 3, 4, 5, 6, 7] }
        ],
        // 1. ESTRUCTURA VISUAL: Mantiene botones y buscador alineados en la misma fila
        dom: "<'row mb-3 align-items-center'<'col-md-6'B><'col-md-6 d-flex justify-content-md-end justify-content-center mt-2 mt-md-0'f>>" +
             "<'row'<'col-sm-12'tr>>" +
             "<'row mt-3 align-items-center'<'col-md-5 text-center text-md-start'i><'col-md-7 d-flex justify-content-md-end justify-content-center'p>>",

        // 2. BOTONES DE EXPORTACIÓN
        buttons: buildMonaguaExportButtons('Comprobantes', 'comprobantes'),

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

