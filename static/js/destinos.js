document.addEventListener('DOMContentLoaded', function () {
    const cards = Array.from(document.querySelectorAll('.tarjeta-tour'));
    const button = document.getElementById('btn-ver-mas-tours');

    if (!cards.length || !button) {
        return;
    }

    const pageSize = 6;
    let visibleCount = pageSize;

    // Si hay filtros activos en la URL, mostrar todas las tarjetas
    const params = new URLSearchParams(window.location.search);
    const hayFiltros = params.has('q') || params.has('precio_max') || params.has('apto_menores') || params.has('categoria');

    if (hayFiltros) {
        visibleCount = cards.length;
        button.classList.add('d-none');
    }

    const applyVisibility = () => {
        cards.forEach((card, index) => {
            const shouldShow = index < visibleCount;
            card.classList.toggle('is-hidden', !shouldShow);
            card.style.display = shouldShow ? '' : 'none';
        });

        if (visibleCount >= cards.length) {
            button.classList.add('d-none');
            button.innerHTML = '<i class="bi bi-check-circle me-2"></i>Mostrando todos';
        } else {
            button.classList.remove('d-none');
            button.innerHTML = '<i class="bi bi-chevron-down me-2"></i>Ver más';
        }
    };

    if (!hayFiltros) {
        cards.forEach((card, index) => {
            if (index >= pageSize) {
                card.classList.add('is-hidden');
                card.style.display = 'none';
            }
        });
    }

    button.addEventListener('click', function () {
        if (visibleCount + pageSize >= cards.length) {
            visibleCount = cards.length;
        } else {
            visibleCount += pageSize;
        }

        applyVisibility();
    });

    applyVisibility();
});
