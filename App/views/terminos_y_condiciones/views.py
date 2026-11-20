from django.shortcuts import render


def terminos_view(request):
    """Renderiza la plantilla de Términos y Condiciones."""
    return render(request, 'usuario/terminos/terminos.html', {
        'titulo': 'Términos y Condiciones — Monagua'
    })


def nosotros_view(request):
    """Renderiza la plantilla de información corporativa Sobre Nosotros."""
    return render(request, 'nosotros.html', {
        'titulo': 'Sobre Nosotros — Monagua'
    })


def derechos_autor_view(request):
    """Renderiza la plantilla de Derechos de Autor, Propiedad Intelectual y Atribuciones."""
    return render(request, 'usuario/terminos/derechos_autor.html', {
        'titulo': 'Derechos de Autor y Créditos — Monagua'
    })
