import re
from django.http import HttpResponse
from django.views.decorators.http import require_GET
from django_ratelimit.decorators import ratelimit
from better_profanity import profanity
from App.models import Usuario

# Cargar palabras censuradas de better-profanity e incorporar términos en español
profanity.load_censor_words()
profanity.add_censor_words([
    'puta', 'puto', 'putas', 'putos', 'mierda', 'mierdas', 'gonorrea', 'gonorreas',
    'malparido', 'malparida', 'pirobo', 'piroba', 'marica', 'maricon', 'carechimba',
    'pendejo', 'pendeja', 'cabron', 'cabrona', 'verga', 'culo', 'chinga', 'zorra',
    'perra', 'idiota', 'imbecil', 'estupido', 'huevon', 'guevon', 'nazi', 'hitler'
])

HTML_RATELIMIT_EXCEEDED = """
<div class="text-warning small ms-3 mt-1">
  <i class="bi bi-shield-exclamation me-1"></i>Has realizado muchas comprobaciones seguidas. Por favor espera un momento por seguridad.
</div>
"""


@require_GET
@ratelimit(key='ip', rate='30/m', block=False)
def verificar_apodo_htmx(request):
    """
    Validación reactiva con HTMX del nombre de usuario (apodo).
    Aplica controles OWASP:
    - Rate limiting anti-enumeración de usuarios y anti-fuerza bruta.
    - Prevención de caracteres peligrosos (/()=?, espacios, inyecciones).
    - Filtro de lenguaje ofensivo con better-profanity.
    - Comprobación de unicidad en la base de datos.
    Retorna fragmentos HTML limpios listos para insertar en el DOM.
    """
    if getattr(request, 'limited', False):
        return HttpResponse(HTML_RATELIMIT_EXCEEDED, status=429)

    valor = request.GET.get('username', '').strip()
    if not valor:
        return HttpResponse('')

    # 1. Longitud
    if len(valor) < 4:
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-exclamation-circle me-1"></i>El apodo debe tener al menos 4 caracteres.'
            '</div>'
        )
    if len(valor) > 30:
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-exclamation-circle me-1"></i>El apodo no puede exceder los 30 caracteres.'
            '</div>'
        )

    # 2. Detección específica de caracteres conflictivos (/()=?)
    simbolos_prohibidos = re.findall(r'[/()=?]', valor)
    if simbolos_prohibidos:
        simb = " ".join(sorted(set(simbolos_prohibidos)))
        return HttpResponse(
            f'<div class="invalid-feedback d-block ms-3 mt-1">'
            f'<i class="bi bi-x-circle me-1"></i>El apodo contiene símbolos no permitidos ({simb}). No se permiten / ( ) = ?.'
            f'</div>'
        )

    # 3. Conjunto estricto de caracteres (solo letras, números y guión bajo)
    if not re.match(r'^[A-Za-z0-9_]+$', valor):
        if ' ' in valor:
            return HttpResponse(
                '<div class="invalid-feedback d-block ms-3 mt-1">'
                '<i class="bi bi-x-circle me-1"></i>El apodo no puede contener espacios. Usa guiones bajos (_).'
                '</div>'
            )
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-x-circle me-1"></i>Solo se permiten letras, números y guión bajo (_).'
            '</div>'
        )

    # 4. Filtro de groserías con better-profanity
    if profanity.contains_profanity(valor) or profanity.contains_profanity(valor.replace('_', ' ')):
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-slash-circle me-1"></i>El apodo contiene expresiones no permitidas. Por favor elige uno respetuoso.'
            '</div>'
        )

    # 5. Unicidad en la base de datos
    if Usuario.objects.filter(username__iexact=valor).exists():
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-person-x me-1"></i>Este nombre de usuario ya está registrado. Elige otro.'
            '</div>'
        )

    # Apodo 100% válido y disponible
    return HttpResponse(
        '<div class="valid-feedback d-block text-success ms-3 mt-1">'
        '<i class="bi bi-check-circle-fill me-1"></i>¡Apodo disponible y seguro!'
        '</div>'
    )


@require_GET
@ratelimit(key='ip', rate='30/m', block=False)
def verificar_email_htmx(request):
    """Verificación reactiva con HTMX de correo electrónico y anti-duplicados."""
    if getattr(request, 'limited', False):
        return HttpResponse(HTML_RATELIMIT_EXCEEDED, status=429)

    valor = request.GET.get('email', '').strip().lower()
    if not valor:
        return HttpResponse('')

    regex_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(regex_email, valor):
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-envelope-exclamation me-1"></i>Ingresa un correo electrónico válido (ejemplo: usuario@correo.com).'
            '</div>'
        )

    if Usuario.objects.filter(email__iexact=valor).exists():
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-envelope-x me-1"></i>Este correo ya se encuentra registrado.'
            '</div>'
        )

    return HttpResponse(
        '<div class="valid-feedback d-block text-success ms-3 mt-1">'
        '<i class="bi bi-check-circle-fill me-1"></i>Correo disponible.'
        '</div>'
    )


@require_GET
@ratelimit(key='ip', rate='30/m', block=False)
def verificar_documento_htmx(request):
    """Verificación reactiva con HTMX del número de documento."""
    if getattr(request, 'limited', False):
        return HttpResponse(HTML_RATELIMIT_EXCEEDED, status=429)

    valor = request.GET.get('numero_documento', '').strip()
    if not valor:
        return HttpResponse('')

    if not re.match(r'^[0-9]{6,10}$', valor):
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-card-text me-1"></i>El documento debe tener entre 6 y 10 dígitos numéricos.'
            '</div>'
        )

    if Usuario.objects.filter(numero_documento=valor).exists():
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-x-circle me-1"></i>Este número de documento ya está registrado.'
            '</div>'
        )

    return HttpResponse(
        '<div class="valid-feedback d-block text-success ms-3 mt-1">'
        '<i class="bi bi-check-circle-fill me-1"></i>Documento disponible.'
        '</div>'
    )


@require_GET
@ratelimit(key='ip', rate='30/m', block=False)
def verificar_telefono_htmx(request):
    """Verificación reactiva con HTMX del teléfono celular."""
    if getattr(request, 'limited', False):
        return HttpResponse(HTML_RATELIMIT_EXCEEDED, status=429)

    valor = request.GET.get('telefono', '').strip()
    if not valor:
        return HttpResponse('')

    if not re.match(r'^\+?[0-9]{7,15}$', valor):
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-telephone-exclamation me-1"></i>Ingresa un número de celular válido (7 a 15 dígitos).'
            '</div>'
        )

    if Usuario.objects.filter(telefono=valor).exists():
        return HttpResponse(
            '<div class="invalid-feedback d-block ms-3 mt-1">'
            '<i class="bi bi-telephone-x me-1"></i>Este número de teléfono ya está registrado.'
            '</div>'
        )

    return HttpResponse(
        '<div class="valid-feedback d-block text-success ms-3 mt-1">'
        '<i class="bi bi-check-circle-fill me-1"></i>Teléfono disponible.'
        '</div>'
    )
