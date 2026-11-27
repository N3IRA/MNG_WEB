import logging
from pathlib import Path
from django.conf import settings
from django.shortcuts import render
from django.http import FileResponse, Http404
from django.utils import timezone

logger = logging.getLogger(__name__)


def soporte_ayuda_view(request):
    """
    Vista principal del Centro de Soporte y Ayuda para usuarios y visitantes.
    Ofrece preguntas frecuentes (FAQ), guías paso a paso, canales de atención directa
    y acceso al Manual Oficial de Usuario en formato PDF.
    """
    context = {
        'titulo': 'Centro de Ayuda y Soporte — Monagua',
        'fecha_actual': timezone.now(),
    }
    return render(request, 'usuario/soporte/soporte_ayuda.html', context)


def manual_usuario_view(request):
    """
    Vista interactiva del Manual de Usuario oficial de Monagua Turismo (ADSO SENA).
    Permite navegar por capítulos, filtrar por roles (Visitante, Turista, Guía, Administrador),
    buscar temas en tiempo real y descargar o visualizar el documento en PDF.
    """
    context = {
        'titulo': 'Manual de Usuario Oficial — Monagua Turismo',
        'anio': timezone.now().year,
        'fecha_actual': timezone.now(),
    }
    return render(request, 'usuario/soporte/manual_usuario.html', context)


def manual_usuario_pdf_view(request):
    """
    Sirve el documento PDF oficial del Manual de Usuario de Monagua Turismo.
    Si se pasa ?ver=1 en la URL se muestra inline en el navegador; de lo contrario se descarga.
    """
    pdf_path = Path(settings.BASE_DIR) / 'static' / 'docs' / 'Manual_de_Usuario_Monagua_Turismo.pdf'
    if not pdf_path.is_file():
        logger.error("No se encontró el archivo PDF del manual de usuario en: %s", pdf_path)
        raise Http404("El archivo del Manual de Usuario en PDF no se encuentra disponible.")

    ver_en_navegador = request.GET.get('ver') == '1'
    return FileResponse(
        pdf_path.open('rb'),
        as_attachment=not ver_en_navegador,
        filename='Manual_de_Usuario_Monagua_Turismo.pdf',
        content_type='application/pdf',
    )
