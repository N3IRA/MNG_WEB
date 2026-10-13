function buildMonaguaExportButtons(title, slug) {
    const fechaReporte = new Date().toLocaleDateString('es-CO', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });

    
    const exportColumns = 'th:not(:last-child)';

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
                columns: exportColumns // Excluye acciones
            },
            customize: function (xlsx) {
                const sheet = xlsx.xl.worksheets['sheet1.xml'];
                let xmlString;

                if (typeof sheet === 'string') {
                    xmlString = sheet;
                } else if (typeof XMLSerializer !== 'undefined') {
                    xmlString = new XMLSerializer().serializeToString(sheet);
                } else {
                    xmlString = sheet.xml;
                }

                if (xmlString) {
                    const titleRow = '<row r="1"><c r="A1" t="inlineStr"><is><t>MONAGUA</t></is></c></row>';
                    const subtitleRow = '<row r="2"><c r="A2" t="inlineStr"><is><t>' + title + '</t></is></c></row>';

                    xmlString = xmlString.replace(/<sheetData>[\s\S]*?<\/sheetData>/, function (match) {
                        const inner = match.replace(/^<sheetData>|<\/sheetData>$/g, '');
                        return '<sheetData>' + titleRow + subtitleRow + inner + '</sheetData>';
                    });

                    if (typeof sheet === 'string') {
                        xlsx.xl.worksheets['sheet1.xml'] = xmlString;
                    } else {
                        xlsx.xl.worksheets['sheet1.xml'] = new DOMParser().parseFromString(xmlString, 'text/xml');
                    }
                }
            }
        },
       {
            extend: 'pdfHtml5',
            text: '<i class="bi bi-file-earmark-pdf-fill text-dark fs-5"></i>',
            titleAttr: 'Exportar a PDF',
            title: title,
            filename: slug + '-' + new Date().toISOString().slice(0, 10),
            className: 'btn btn-light rounded-circle shadow-sm border-0 mx-1 d-flex align-items-center justify-content-center p-0',
            attr: { style: 'width:48px;height:48px; flex-shrink: 0;' },
            exportOptions: { columns: exportColumns },
            customize: function (doc) {
                doc.pageMargins = [15, 35, 15, 20];
                
                // Usamos 'Roboto' que es la fuente nativa integrada en todas las versiones de pdfmake
                doc.defaultStyle = {
                    font: 'Roboto',
                    fontSize: 9,
                    color: '#1a261f'
                };
                
                doc.styles = Object.assign({}, doc.styles || {}, {
                    tableHeader: {
                        fillColor: [44, 110, 60],
                        textColor: [255, 255, 255],
                        fontSize: 9,
                        bold: true,
                        alignment: 'center'
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
                columns: exportColumns // Excluye acciones en la impresión
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
