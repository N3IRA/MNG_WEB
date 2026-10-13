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
                columns: exportColumns
            },
            customize: function (xlsx) {
                const worksheetXml = xlsx.xl.worksheets['sheet1.xml'];
                const titleRow = '<row r="1"><c r="A1" t="inlineStr"><is><t>MONAGUA</t></is></c></row>';
                const subtitleRow = '<row r="2"><c r="A2" t="inlineStr"><is><t>' + title + '</t></is></c></row>';
                const dateRow = '<row r="3"><c r="A3" t="inlineStr"><is><t>Generado: ' + fechaReporte + '</t></is></c></row>';
                const emptyRow = '<row r="4"></row>';

                xlsx.xl.worksheets['sheet1.xml'] = worksheetXml.replace(/<sheetData>[\s\S]*?<\/sheetData>/, function (match) {
                    const inner = match.replace(/^<sheetData>|<\/sheetData>$/g, '');
                    return '<sheetData>' + titleRow + subtitleRow + dateRow + emptyRow + inner + '</sheetData>';
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
                columns: exportColumns
            },
            customize: function (doc) {
                doc.pageMargins = [20, 30, 20, 25];
                doc.defaultStyle = {
                    font: 'Roboto',
                    fontSize: 9,
                    color: '#1a261f'
                };
                doc.styles = Object.assign({}, doc.styles || {}, {
                    tableHeader: {
                        fillColor: [44, 110, 60], // Verde Monagua (#2c6e3c)
                        textColor: [255, 255, 255],
                        fontSize: 9,
                        bold: true,
                        alignment: 'center'
                    },
                    tableBodyEven: { fillColor: [240, 246, 242] },
                    tableBodyOdd: { fillColor: [255, 255, 255] }
                });

                // Cabecera institucional estructurada para PDF compatible con pdfmake
                doc.content.unshift({
                    table: {
                        widths: ['*', 'auto'],
                        body: [
                            [
                                {
                                    stack: [
                                        { text: 'MONAGUA', fontSize: 20, bold: true, color: '#005215', margin: [0, 0, 0, 2] },
                                        { text: title, fontSize: 11, bold: true, color: '#406d46' }
                                    ]
                                },
                                {
                                    text: 'Generado: ' + fechaReporte,
                                    fontSize: 10,
                                    bold: true,
                                    color: '#1a261f',
                                    alignment: 'right',
                                    margin: [0, 8, 0, 0]
                                }
                            ]
                        ]
                    },
                    layout: {
                        hLineWidth: function (i, node) { return (i === node.table.body.length) ? 3 : 0; },
                        hLineColor: function (i, node) { return '#2c6e3c'; },
                        paddingLeft: function (i, node) { return 0; },
                        paddingRight: function (i, node) { return 0; },
                        paddingTop: function (i, node) { return 4; },
                        paddingBottom: function (i, node) { return 8; }
                    },
                    margin: [0, 0, 0, 15]
                });
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
                columns: exportColumns
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