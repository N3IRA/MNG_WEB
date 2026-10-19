/* Formateador COP */
const formatCOP = v => 'COP $' + Math.round(v).toLocaleString('es-CO');

/* Calcula un paso de escala limpio basado en el máximo real */
function calcStepSize(data) {
  const max = Math.max(...data, 180); /* mínimo 180 para que no quede vacío */
  const raw = max / 5;
  const magnitude = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = Math.ceil(raw / magnitude) * magnitude;
  return step;
}

document.addEventListener('DOMContentLoaded', function() {
    /* Fecha actual formateada */
    const dateElement = document.getElementById('currentDate');
    if (dateElement) {
        dateElement.textContent = new Date().toLocaleDateString('es-CO', { weekday:'short', year:'numeric', month:'short', day:'numeric' });
    }

    /* Paleta de colores de alto contraste y viveza */
    const C = {
      emerald: '#059669',
      emeraldDark: '#047857',
      emeraldLight: 'rgba(16, 185, 129, 0.18)',
      amber: '#f59e0b',
      amberDark: '#d97706',
      rose: '#ef4444',
      roseDark: '#dc2626',
      slateDark: '#0f172a',
      slateText: '#334155',
      slateMuted: '#475569',
      gridColor: '#f1f5f9'
    };

    /* Gráfica 1 — Ingresos mensuales */
    const canvasIngresos = document.getElementById('chartIngresos');
    if (canvasIngresos && typeof ingresosData !== 'undefined') {
        const stepIngresos = calcStepSize(ingresosData);
        const maxIngresos  = stepIngresos * 6; /* 6 pasos arriba del máximo */
        const ctx = canvasIngresos.getContext('2d');

        /* Gradiente vibrante para el área bajo la curva */
        const fillGradient = ctx.createLinearGradient(0, 0, 0, 260);
        fillGradient.addColorStop(0, 'rgba(16, 185, 129, 0.35)');
        fillGradient.addColorStop(0.7, 'rgba(16, 185, 129, 0.08)');
        fillGradient.addColorStop(1, 'rgba(16, 185, 129, 0.00)');

        new Chart(canvasIngresos, {
          type: 'line',
          data: {
            labels: ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'],
            datasets: [{
              label: 'Ingresos (COP $)',
              data: ingresosData,
              borderColor: C.emerald,
              backgroundColor: fillGradient,
              borderWidth: 3,
              tension: 0.38,
              fill: true,
              pointBackgroundColor: C.emerald,
              pointBorderColor: '#ffffff',
              pointBorderWidth: 2,
              pointRadius: 4.5,
              pointHoverRadius: 7.5,
              pointHoverBackgroundColor: C.emeraldDark,
              pointHoverBorderColor: '#ffffff',
              pointHoverBorderWidth: 3
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: C.slateDark,
                titleColor: '#34d399',
                bodyColor: '#ffffff',
                titleFont: { weight: 'bold', size: 12 },
                bodyFont: { weight: 'bold', size: 13 },
                padding: 10,
                cornerRadius: 8,
                boxPadding: 4,
                callbacks: {
                  label: c => ' ' + formatCOP(c.parsed.y)
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: {
                  font: { size: 12, weight: '600' },
                  color: C.slateMuted
                }
              },
              y: {
                min: 0,
                max: maxIngresos,
                grid: { color: C.gridColor, drawBorder: false },
                ticks: {
                  stepSize: stepIngresos,
                  font: { size: 11, weight: '600' },
                  color: C.slateMuted,
                  callback: v => formatCOP(v)
                }
              }
            }
          }
        });
    }

    /* Gráfica 2 — Estado reservas (donut) */
    const canvasEstado = document.getElementById('chartEstado');
    if (canvasEstado && typeof reservasConf !== 'undefined') {
        const tot = reservasConf + reservasPend + reservasCan;
        new Chart(canvasEstado, {
          type: 'doughnut',
          data: {
            labels: ['Confirmadas','Pendientes','Canceladas'],
            datasets: [{
              data: tot > 0 ? [reservasConf, reservasPend, reservasCan] : [1],
              backgroundColor: tot > 0 ? ['#10b981', '#f59e0b', '#ef4444'] : ['#e2e8f0'],
              borderColor: '#ffffff',
              borderWidth: 3,
              hoverOffset: tot > 0 ? 8 : 0
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
              legend: { display: false },
              tooltip: {
                enabled: tot > 0,
                backgroundColor: C.slateDark,
                titleColor: '#f8fafc',
                bodyColor: '#f1f5f9',
                titleFont: { weight: 'bold', size: 12 },
                bodyFont: { weight: 'bold', size: 13 },
                padding: 10,
                cornerRadius: 8,
                callbacks: {
                  label: c => ' ' + c.label + ': ' + c.parsed + ' reservas'
                }
              }
            }
          }
        });
    }

    /* Gráfica 3 — Reservas esta semana */
    const canvasSemana = document.getElementById('chartSemana');
    if (canvasSemana && typeof dataSemana !== 'undefined') {
        const maxS = Math.max(...dataSemana) || 1;
        new Chart(canvasSemana, {
          type: 'bar',
          data: {
            labels: ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'],
            datasets: [{
              label: 'Reservas',
              data: dataSemana,
              backgroundColor: dataSemana.map(v => v === maxS && v > 0 ? '#059669' : 'rgba(16, 185, 129, 0.4)'),
              hoverBackgroundColor: '#047857',
              borderRadius: 6,
              borderSkipped: false
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: C.slateDark,
                titleColor: '#34d399',
                bodyColor: '#ffffff',
                titleFont: { weight: 'bold', size: 12 },
                bodyFont: { weight: 'bold', size: 13 },
                padding: 8,
                cornerRadius: 8,
                callbacks: {
                  label: c => ' ' + c.parsed.y + ' reservas'
                }
              }
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: {
                  font: { size: 11, weight: '600' },
                  color: C.slateMuted
                }
              },
              y: {
                display: false,
                min: 0
              }
            }
          }
        });
    }

    /* Exportar PDF */
    const btnExportPdf = document.getElementById('btnExportPdf');
    if (btnExportPdf) {
        btnExportPdf.addEventListener('click', async function () {
          const btn = this;
          btn.disabled = true;
          btn.innerHTML = '<i class="bi bi-hourglass-split"></i> Generando…';
          try {
            const target = document.getElementById('mainContent') || document.body;
            const canvas = await html2canvas(target, {
              scale: 2, useCORS: true, backgroundColor: '#f8f9fa',
              logging: false, scrollY: -window.scrollY,
              windowWidth: target.scrollWidth, windowHeight: target.scrollHeight
            });
            const { jsPDF } = window.jspdf;
            const pdf = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' });
            const pW = pdf.internal.pageSize.getWidth();
            const pH = pdf.internal.pageSize.getHeight();
            const ratio = pW / canvas.width;
            const totalH = canvas.height * ratio;
            let posY = 0, pg = 1;
            const totalPages = Math.ceil(totalH / pH);
            let loopLimit = 0;

            const header = (n, t) => {
              pdf.setFillColor(15, 23, 42); pdf.rect(0, 0, pW, 10, 'F');
              pdf.setTextColor(255, 255, 255); pdf.setFontSize(8); pdf.setFont('helvetica', 'bold');
              pdf.text('MONAGUA — Tablero de Rendimiento', 8, 6.5);
              pdf.text('Generado: ' + new Date().toLocaleDateString('es-CO', { year: 'numeric', month: 'long', day: 'numeric' }) + '   Pág ' + n + '/' + t, pW - 8, 6.5, { align: 'right' });
            };

            while (posY < totalH - 1 && loopLimit < 50) {
              if (pg > 1) pdf.addPage();
              header(pg, totalPages);
              const sliceH = Math.min(pH - 10, totalH - posY);
              if (sliceH <= 0) break;
              const sc = document.createElement('canvas');
              sc.width = canvas.width;
              sc.height = Math.round(sliceH / ratio);
              sc.getContext('2d').drawImage(canvas, 0, Math.round(posY / ratio), canvas.width, sc.height, 0, 0, sc.width, sc.height);
              pdf.addImage(sc.toDataURL('image/jpeg', .92), 'JPEG', 0, 10, pW, sliceH);
              posY += sliceH; pg++; loopLimit++;
            }
            pdf.save('monagua-dashboard-' + new Date().toISOString().slice(0, 10) + '.pdf');
          } catch (e) {
            console.error(e);
            if (typeof window.mostrarToast === 'function') {
              window.mostrarToast('error', 'Error de exportación', 'Ocurrió un error al generar el archivo PDF.', 5000);
            }
          } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-file-earmark-pdf-fill"></i> Exportar PDF';
          }
        });
    }
});
