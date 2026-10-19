import json
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django_ratelimit.decorators import ratelimit
from .condy_nlp import procesar_mensaje


@ratelimit(key='ip', rate='30/m', block=False)
@ensure_csrf_cookie
def condy_chat_api(request):
    """
    Endpoint del asistente virtual Condy.
    Protegido contra inundación de peticiones mediante rate-limiting.
    """
    if getattr(request, 'limited', False):
        return JsonResponse({
            'reply': 'Has enviado muchos mensajes en poco tiempo. Por favor espera un momento antes de continuar consultando a Condy.',
            'status': 'rate_limited'
        }, status=429)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mensaje = data.get('message', '')
            
            if not mensaje:
                return JsonResponse({'error': 'Mensaje vacío'}, status=400)
            
            resultado = procesar_mensaje(mensaje, request)
            return JsonResponse(resultado)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Formato JSON inválido'}, status=400)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)
