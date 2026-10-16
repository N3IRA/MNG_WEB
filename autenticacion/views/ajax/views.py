import re
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from better_profanity import profanity
from App.models import Usuario

profanity.load_censor_words()
profanity.add_censor_words([
    'puta', 'puto', 'putas', 'putos', 'mierda', 'mierdas', 'gonorrea', 'gonorreas',
    'malparido', 'malparida', 'pirobo', 'piroba', 'marica', 'maricon', 'carechimba',
    'pendejo', 'pendeja', 'cabron', 'cabrona', 'verga', 'culo', 'chinga', 'zorra',
    'perra', 'idiota', 'imbecil', 'estupido', 'huevon', 'guevon', 'nazi', 'hitler'
])


@require_GET
def verificar_campo_ajax(request):
    """
    Verifica en tiempo real si un dato (username, email, numero_documento, telefono)
    cumple con las restricciones de formato, groserías y unicidad para la validación
    interactiva del registro.
    """
    campo = request.GET.get('campo', '').strip()
    valor = request.GET.get('valor', '').strip()

    if not campo or not valor:
        return JsonResponse({'error': 'Parámetros inválidos'}, status=400)

    disponible = True
    mensaje = ""

    if campo == 'username':
        if len(valor) < 4:
            disponible = False
            mensaje = "El apodo debe tener al menos 4 caracteres."
        elif len(valor) > 30:
            disponible = False
            mensaje = "El apodo no puede exceder los 30 caracteres."
        elif not re.match(r'^[A-Za-z0-9_]+$', valor):
            disponible = False
            mensaje = "El apodo solo puede contener letras, números y guión bajo (_). No se permiten espacios ni símbolos como / ( ) = ?."
        elif profanity.contains_profanity(valor) or profanity.contains_profanity(valor.replace('_', ' ')):
            disponible = False
            mensaje = "El apodo contiene palabras no permitidas. Por favor elige un apodo respetuoso."
        elif Usuario.objects.filter(username__iexact=valor).exists():
            disponible = False
            mensaje = "Este nombre de usuario ya está registrado."

    elif campo == 'email':
        exists = Usuario.objects.filter(email__iexact=valor).exists()
        if exists:
            disponible = False
            mensaje = "Este correo electrónico ya está registrado."

    elif campo == 'numero_documento':
        exists = Usuario.objects.filter(numero_documento=valor).exists()
        if exists:
            disponible = False
            mensaje = "Este número de documento ya está registrado."

    elif campo == 'telefono':
        exists = Usuario.objects.filter(telefono=valor).exists()
        if exists:
            disponible = False
            mensaje = "Este número de teléfono ya está registrado."

    return JsonResponse({
        'disponible': disponible,
        'mensaje': mensaje
    })
