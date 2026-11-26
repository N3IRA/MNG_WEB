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
            'response': 'Has enviado muchos mensajes en poco tiempo. Por favor espera un momento antes de continuar consultando a Cóndy.',
            'reply': 'Has enviado muchos mensajes en poco tiempo. Por favor espera un momento antes de continuar consultando a Cóndy.',
            'status': 'rate_limited'
        }, status=429)

    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
            mensaje = data.get('message', '')
            
            resultado = procesar_mensaje(mensaje, request)
            return JsonResponse(resultado)
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Formato JSON inválido', 'response': 'Formato de mensaje inválido.'}, status=400)
        except Exception as e:
            return JsonResponse({
                'response': 'Hubo un inconveniente al procesar tu mensaje. Puedes intentar nuevamente o comunicarte a nuestro WhatsApp oficial +57 322 3465191.',
                'options': ['¿Qué tours ofrecen?', 'Regulaciones ambientales', 'Radicar PQRS']
            }, status=200)
    
    if request.method == 'GET':
        resultado = procesar_mensaje('', request)
        return JsonResponse(resultado)
    
    return JsonResponse({'error': 'Método no permitido'}, status=405)
