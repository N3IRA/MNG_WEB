document.addEventListener('DOMContentLoaded', function() {
    const inicioInput = document.getElementById('id_fecha_inicio');
    const finInput = document.getElementById('id_fecha_fin');
    let fpFin = null;
    let fpInicio = null;

    // Fecha de inicio: permite hasta 1 semana antes de la fecha actual
    const fechaMinimaInicio = new Date();
    fechaMinimaInicio.setDate(fechaMinimaInicio.getDate() - 7);
    const minInicioBaseStr = fechaMinimaInicio.getFullYear() + '-' + 
                             String(fechaMinimaInicio.getMonth() + 1).padStart(2, '0') + '-' + 
                             String(fechaMinimaInicio.getDate()).padStart(2, '0');

    // Fecha de finalización: no puede ser antes ni el mismo día actual (mínimo mañana)
    const fechaMinimaFin = new Date();
    fechaMinimaFin.setDate(fechaMinimaFin.getDate() + 1);
    const minFinBaseStr = fechaMinimaFin.getFullYear() + '-' + 
                          String(fechaMinimaFin.getMonth() + 1).padStart(2, '0') + '-' + 
                          String(fechaMinimaFin.getDate()).padStart(2, '0');

    const initialInicio = inicioInput ? inicioInput.value : null;
    const initialFin = finInput ? finInput.value : null;

    // En edición, si ya existían fechas históricas previas, respetarlas para visualización
    const minInicio = (initialInicio && initialInicio < minInicioBaseStr) ? initialInicio : minInicioBaseStr;
    const minFin = (initialFin && initialFin < minFinBaseStr) ? initialFin : minFinBaseStr;

    function calcularMinFin(inicioStr) {
        if (!inicioStr) return minFin;
        const partes = inicioStr.split('-').map(Number);
        const diaDespuesInicio = new Date(partes[0], partes[1] - 1, partes[2] + 1);
        const diaDespuesStr = diaDespuesInicio.getFullYear() + '-' + 
                              String(diaDespuesInicio.getMonth() + 1).padStart(2, '0') + '-' + 
                              String(diaDespuesInicio.getDate()).padStart(2, '0');
        return diaDespuesStr > minFinBaseStr ? diaDespuesStr : minFinBaseStr;
    }

    if (finInput) {
        const minInicialFin = calcularMinFin(initialInicio);
        fpFin = flatpickr(finInput, {
            locale: 'es',
            dateFormat: 'Y-m-d',
            allowInput: true,
            minDate: minInicialFin
        });
    }

    if (inicioInput) {
        fpInicio = flatpickr(inicioInput, {
            locale: 'es',
            dateFormat: 'Y-m-d',
            allowInput: true,
            minDate: minInicio,
            onChange: function(selectedDates, dateStr) {
                if (fpFin && dateStr) {
                    const dynamicMinFin = calcularMinFin(dateStr);
                    fpFin.set('minDate', dynamicMinFin);
                    if (finInput && finInput.value && finInput.value < dynamicMinFin) {
                        fpFin.setDate(dynamicMinFin);
                    }
                }
            }
        });
    }
});
