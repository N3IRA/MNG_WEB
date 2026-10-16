(function ($, window) {
    const tablasConExportacion = [];

    function ajustarVisibilidadExportaciones() {
        tablasConExportacion.forEach(function (table) {
            if (!table.isConnected) return;

            const tableContainer = table.closest('.table-responsive');
            const card = table.closest('.card');
            const buttons = table.closest('.dt-container, .dataTables_wrapper');
            const buttonContainer = buttons && buttons.querySelector('.dt-buttons');
            if (!tableContainer || !card || !buttonContainer) return;

            // Si los botones están configurados como ocultos (usados por dropdown externo), no mover ni mostrar
            if (buttonContainer.querySelector('.d-none') || buttonContainer.closest('.d-none')) {
                buttonContainer.style.display = 'none';
                return;
            }

            if (!buttonContainer.monaguaOriginalParent) {
                buttonContainer.monaguaOriginalParent = buttonContainer.parentNode;
            }

            if (window.getComputedStyle(tableContainer).display === 'none') {
                if (buttonContainer.parentNode !== card) {
                    card.insertBefore(buttonContainer, tableContainer);
                }
            } else if (buttonContainer.parentNode !== buttonContainer.monaguaOriginalParent) {
                buttonContainer.monaguaOriginalParent.appendChild(buttonContainer);
            }
        });
    }

    $(document).on('init.dt', function (event, settings) {
        if (!settings || !settings.nTable) return;

        tablasConExportacion.push(settings.nTable);
        window.requestAnimationFrame(ajustarVisibilidadExportaciones);
    });

    window.addEventListener('resize', ajustarVisibilidadExportaciones);

    window.buildMonaguaExportButtons = function (title, slug, hidden) {
        const fechaReporte = new Date().toLocaleDateString('es-CO', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        const filename = slug + '-' + new Date().toISOString().slice(0, 10);
        const exportColumns = ':visible:not(:last-child)';
        const buttonClass = 'btn btn-light rounded-circle shadow-sm border-0 mx-1 d-flex align-items-center justify-content-center p-0';
        const buttonStyle = 'width:48px;height:48px;flex-shrink:0;';
        const className = function (type) {
            return hidden
                ? 'd-none btn-export-' + type + '-hidden'
                : buttonClass;
        };

        return [
            {
                extend: 'excelHtml5',
                text: '<i class="bi bi-file-earmark-excel-fill text-success fs-5"></i>',
                titleAttr: 'Exportar a Excel',
                title: title,
                messageTop: 'MONAGUA - Generado: ' + fechaReporte,
                filename: filename,
                className: className('excel'),
                attr: { style: buttonStyle },
                exportOptions: { columns: exportColumns }
            },
            {
                extend: 'pdfHtml5',
                text: '<i class="bi bi-file-earmark-pdf-fill text-dark fs-5"></i>',
                titleAttr: 'Exportar a PDF',
                title: title,
                filename: filename,
                className: className('pdf'),
                attr: { style: buttonStyle },
                exportOptions: { columns: exportColumns },
                customize: function (doc) {
                    doc.pageMargins = [15, 35, 15, 20];
                    doc.defaultStyle = {
                        font: 'Roboto',
                        fontSize: 9,
                        color: '#1a261f'
                    };
                    doc.styles = Object.assign({}, doc.styles || {}, {
                        tableHeader: {
                            fillColor: [44, 110, 60],
                            color: '#ffffff',
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
                className: className('print'),
                attr: { style: buttonStyle },
                exportOptions: { columns: exportColumns },
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
    };
})(jQuery, window);
