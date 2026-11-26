import io
import logging
from django.shortcuts import render
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from xhtml2pdf import pisa
from App.utils import get_image_base64

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
    Genera y sirve el documento PDF del Manual de Usuario y Guía de Ayuda de Monagua.
    Si se pasa ?ver=1 en la URL se muestra inline en el navegador; de lo contrario se descarga.
    """
    logo_base64 = get_image_base64('static/img/logo_monagua.webp')
    
    context = {
        'fecha_generacion': timezone.now().strftime('%d/%m/%Y'),
        'logo_base64': logo_base64,
        'anio': timezone.now().year,
    }
    
    try:
        html_string = render_to_string('usuario/soporte/manual_usuario_pdf.html', context)
        pdf_temp = io.BytesIO()
        pisa_status = pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), pdf_temp)
        
        if pisa_status.err:
            logger.error("Error al renderizar el manual de usuario PDF con xhtml2pdf")
            return HttpResponse("Error al generar el manual en PDF. Intente nuevamente.", status=500)
            
        pdf_bytes = pdf_temp.getvalue()
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        
        disposicion = 'inline' if request.GET.get('ver') == '1' else 'attachment'
        response['Content-Disposition'] = f'{disposicion}; filename="Manual_Usuario_Monagua.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error generando el manual de usuario PDF: {e}", exc_info=True)
        return HttpResponse("No fue posible generar el documento en este momento.", status=500)
