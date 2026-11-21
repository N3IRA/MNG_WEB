import os
import re
import json
import urllib.request
import urllib.error
import unicodedata
from django.conf import settings
from django.utils import timezone


def remove_accents(input_str):
    """Elimina tildes y caracteres diacríticos para normalización fonética."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def normalizar_texto(texto):
    """Limpia caracteres especiales, espacios y acentos."""
    texto = remove_accents(texto.lower().strip())
    texto = re.sub(r'\s+', ' ', texto)
    return texto


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONSULTA DINÁMICA A LA BASE DE DATOS (GROUNDING EN TIEMPO REAL)
# ══════════════════════════════════════════════════════════════════════════════

def obtener_tours_destacados():
    """Consulta los paquetes activos en la base de datos."""
    try:
        from App.models import Paquete
        tours = list(Paquete.objects.filter(estado=True).order_by('id')[:4])
        if tours:
            nombres = [f"• **{t.nombre}** ({t.dias_duracion} día{'s' if t.dias_duracion > 1 else ''})" for t in tours]
            return "\n".join(nombres)
    except Exception:
        pass
    return "• **Mongua Mágico** (senderos de páramo)\n• **Ruta del Páramo de Ocetá**\n• **Aventura Laguna Negra**"


def obtener_promociones_activas():
    """Consulta las promociones vigentes en la base de datos."""
    try:
        from App.models import Promocion
        hoy = timezone.now().date()
        promos = list(Promocion.objects.filter(activa=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy)[:3])
        if promos:
            detalles = []
            for p in promos:
                cupon_txt = f" (Cupón: `{p.codigo_cupon}`)" if p.codigo_cupon else ""
                detalles.append(f"• **{p.nombre}**: {p.porcentaje_descuento}% de descuento{cupon_txt}")
            return "\n".join(detalles)
    except Exception:
        pass
    return "• **Descuento de Temporada**: 10% de ahorro en tours seleccionados.\n• **Promo Especial**: Consulta en el catálogo de ofertas."


def obtener_resumen_reservas(user):
    """Consulta las reservas del usuario autenticado."""
    if not user or not user.is_authenticated:
        return None
    try:
        from App.models import Reserva
        reservas = list(Reserva.objects.filter(usuario=user).order_by('-id')[:2])
        if reservas:
            lineas = []
            for r in reservas:
                paquete_nombre = getattr(r.paquete, 'nombre', 'Tour')
                lineas.append(f"• Reserva #{r.id} ({paquete_nombre}) — Estado: **{r.estado_reserva.capitalize()}**")
            return "\n".join(lineas)
    except Exception:
        pass
    return None


def obtener_resumen_pqrs(user):
    """Consulta las solicitudes PQRS del usuario autenticado."""
    if not user or not user.is_authenticated:
        return None
    try:
        from App.models import PQRS
        pqrs_list = list(PQRS.objects.filter(usuario=user).order_by('-fecha')[:2])
        if pqrs_list:
            lineas = []
            for p in pqrs_list:
                lineas.append(f"• Solicitud #{p.id} ('{p.asunto[:30]}...') — Estado: **{p.estado.capitalize()}**")
            return "\n".join(lineas)
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# LLAMADA HÍBRIDA OPCIONAL A GEMINI AI (SI EXISTE CLAVE EN .ENV / SETTINGS)
# ══════════════════════════════════════════════════════════════════════════════

def sanitizar_respuesta_ia(texto):
    """
    Filtro de seguridad anti-alucinación:
    1. Reemplaza números de contacto inventados por el oficial de Monagua.
    2. Reemplaza correos externos inventados por el institucional.
    3. Corrige enlaces ficticios hacia las rutas válidas de Django.
    """
    if not texto:
        return texto

    # Garantizar teléfono de contacto oficial
    telefonos_inventados = re.findall(r'(?:\+?57)?\s*3\d{2}[- ]?\d{3}[- ]?\d{4}', texto)
    for tel in telefonos_inventados:
        tel_limpio = re.sub(r'[\s\-+]', '', tel)
        if '3223465191' not in tel_limpio:
            texto = texto.replace(tel, '+57 322 3465191')

    # Garantizar correo oficial
    correos_inventados = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', texto)
    for c in correos_inventados:
        if 'monagua' not in c.lower():
            texto = texto.replace(c, 'contacto@monagua.com')

    # Corregir URLs hacia rutas oficiales
    reemplazos_urls = [
        (r'/contacto(?:\.html)?\b', '/pqrs/'),
        (r'/reservar(?:\.html)?\b', '/tours/'),
        (r'/pago(?:\.html)?\b', '/pagos/enviar-comprobante/'),
        (r'/comprobante(?:\.html)?\b', '/pagos/enviar-comprobante/'),
        (r'/ofertas(?:\.html)?\b', '/promociones/'),
    ]
    for patron, reemplazo in reemplazos_urls:
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)

    return texto


def consultar_gemini(mensaje, request):
    """
    Si existe GEMINI_API_KEY configurada, procesa el mensaje con Google Gemini
    proporcionándole contexto estricto de Monagua con guardrails anti-alucinación.
    Si falla o no hay clave, retorna None para activar el motor local sin interrumpir al usuario.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '') or os.environ.get('GEMINI_API_KEY', '')
    if not api_key:
        return None

    # Contexto del sistema para anclar la IA a los datos reales de Monagua
    tours_context = obtener_tours_destacados()
    promos_context = obtener_promociones_activas()

    user = getattr(request, 'user', None)
    usuario_info = ""
    if user and user.is_authenticated:
        usuario_info = f"\nInformación del usuario autenticado:\n- Nombre: {user.get_full_name() or user.username}\n"
        res_info = obtener_resumen_reservas(user)
        if res_info:
            usuario_info += f"- Sus reservas registradas:\n{res_info}\n"
        pq_info = obtener_resumen_pqrs(user)
        if pq_info:
            usuario_info += f"- Sus solicitudes PQRS:\n{pq_info}\n"

    system_instruction = (
        "Eres Cóndy, el cóndor andino guardián y asistente virtual oficial de 'Monagua Turismo', "
        "agencia comunitaria de ecoturismo en el municipio de Mongua, Boyacá, Colombia.\n\n"
        "REGLAS ESTRICTAS CONTRA ALUCINACIONES (CÚMPLELAS SIN EXCEPCIÓN):\n"
        "1. UBICACIÓN EXCLUSIVA: Monagua opera ÚNICAMENTE en el municipio de Mongua, Boyacá "
        "(a 35-40 min de Sogamoso). Sus atractivos son el Páramo de Ocetá, Laguna Negra, Morro San Pedro, "
        "Peña de Otí y vestigios Muiscas. Si el usuario pregunta por otras ciudades o regiones (ej. Medellín, "
        "Cartagena, Bogotá, Cali, Santa Marta, Eje Cafetero), responde con amabilidad que Monagua NO opera allí y "
        "ofrécele los destinos de Mongua.\n"
        "2. CATÁLOGO REAL: Solo menciona los tours reales activos en nuestra base de datos:\n"
        f"{tours_context}\n"
        "NUNCA inventes nombres de tours que no figuren en esa lista.\n"
        "3. TARIFAS Y PRECIOS: Los precios varían según temporada, días y número de personas. "
        "NUNCA inventes valores numéricos ni precios exactos al azar; remite siempre al catálogo oficial /tours/.\n"
        "4. PROMOCIONES REALES:\n"
        f"{promos_context}\n"
        "No prometas descuentos ni códigos que no estén en esa lista.\n"
        "5. MÉTODOS DE PAGO: Solo aceptamos transferencias bancarias (Bancolombia, Davivienda, etc.) y "
        "billeteras digitales (Nequi, Daviplata). NUNCA digas que aceptamos pagos directos con tarjeta en línea, "
        "PayPal, PSE automático ni criptomonedas. El cliente debe pagar y luego subir su comprobante en "
        "/pagos/enviar-comprobante/.\n"
        "6. CONTACTO OFICIAL ÚNICO: Teléfono/WhatsApp oficial: +57 322 3465191. Correo: contacto@monagua.com. "
        "NUNCA inventes otros números de teléfono ni correos electrónicos.\n"
        "7. RADICACIÓN DE QUEJAS Y RECLAMOS: Para cualquier inconformidad, queja, reclamo o petición formal, "
        "indica SIEMPRE el módulo oficial de la plataforma: /pqrs/.\n"
        "8. ENLACES PERMITIDOS: Únicamente puedes citar estas rutas: /tours/, /pqrs/, /mis_pqrs/, "
        "/pagos/enviar-comprobante/, /reservas/mis-reservas/, /promociones/, /nosotros/.\n"
        "9. CLIMA: Frío de páramo (7°C a 16°C). Ropa recomendada: en capas, impermeable, calzado de trekking.\n"
        "10. BREVEDAD Y TONO: Sé cordial, conciso (máximo 2 párrafos) y 100% verídico."
        + usuario_info
    )

    modelos = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": mensaje}]}
        ],
        "generationConfig": {
            "temperature": 0.1,  # Temperatura baja para máxima fidelidad y cero alucinaciones
            "topP": 0.8,
            "maxOutputTokens": 350
        }
    }

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidates = res_data.get('candidates', [])
                    if candidates:
                        parts = candidates[0].get('content', {}).get('parts', [])
                        if parts and 'text' in parts[0]:
                            texto_ia = sanitizar_respuesta_ia(parts[0]['text'].strip())
                            resultado = {
                                "response": texto_ia,
                                "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "Radicar PQRS"]
                            }
                            # Detección inteligente de botones de navegación
                            texto_lower = texto_ia.lower()
                            if 'pqrs' in texto_lower or 'queja' in texto_lower or 'reclamo' in texto_lower:
                                resultado["link_url"] = "/pqrs/"
                                resultado["link_text"] = "Radicar PQRS oficial"
                                resultado["action"] = "pqrs"
                            elif 'comprobante' in texto_lower or 'pago' in texto_lower:
                                resultado["link_url"] = "/pagos/enviar-comprobante/"
                                resultado["link_text"] = "Enviar comprobante de pago"
                            elif 'tour' in texto_lower or 'paquete' in texto_lower or 'destino' in texto_lower:
                                resultado["link_url"] = "/tours/"
                                resultado["link_text"] = "Ver catálogo de tours"
                            elif 'oferta' in texto_lower or 'promocion' in texto_lower or 'descuento' in texto_lower:
                                resultado["link_url"] = "/promociones/"
                                resultado["link_text"] = "Ver promociones vigentes"

                            return resultado
        except Exception:
            continue

    return None


# ══════════════════════════════════════════════════════════════════════════════
# BASE DE CONOCIMIENTO LOCAL EXPANDIDA (25+ INTENCIONES SIN ALUCINACIONES)
# ══════════════════════════════════════════════════════════════════════════════

def construir_faqs(user=None):
    """Genera la lista de intenciones incorporando datos dinámicos de la BD."""
    tours_dinamicos = obtener_tours_destacados()
    promos_dinamicas = obtener_promociones_activas()

    nombre_usuario = (user.first_name or user.username) if (user and user.is_authenticated) else ""
    saludo_personalizado = f"¡Hola{', ' + nombre_usuario if nombre_usuario else ''}! Te doy la bienvenida a Monagua Turismo."

    faqs = [
        {
            "id": "saludo",
            "keywords": [
                "hola", "buen dia", "buenos dias", "buenas tardes", "buenas noches",
                "hey", "saludos", "que tal", "como estas", "que hubo", "buenas",
                "hi", "hello", "buena tarde", "buen dia condy", "hola condy"
            ],
            "answer": (
                f"{saludo_personalizado} Soy Cóndy, tu cóndor guardián y asistente virtual "
                f"en Mongua, Boyacá. ¿En qué te puedo colaborar hoy? Puedes consultarme sobre "
                f"nuestros tours ecológicos, cómo reservar, métodos de pago, guías o radicar una PQRS."
            ),
            "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "¿Dónde están ubicados?", "Radicar PQRS"]
        },
        {
            "id": "identidad",
            "keywords": [
                "quien eres", "que eres", "como te llamas", "tu nombre", "eres un bot",
                "eres una ia", "eres un robot", "que es condy", "quien es condy", "presentate",
                "que haces", "cual es tu funcion"
            ],
            "answer": (
                "Soy Cóndy, la mascota oficial y asistente virtual de Monagua Turismo. "
                "Represento al cóndor andino que sobrevuela las cumbres del Páramo de Ocetá. "
                "Estoy aquí para brindarte información verídica de nuestros destinos, resolver tus dudas "
                "y ayudarte a gestionar tus reservas y solicitudes."
            ),
            "options": ["¿Dónde están ubicados?", "¿Qué actividades tienen?", "¿Cómo contactar a un asesor?"]
        },
        {
            "id": "despedida_agradecimiento",
            "keywords": [
                "gracias", "muchas gracias", "mil gracias", "te agradezco", "chao",
                "adios", "hasta luego", "nos vemos", "que estes bien", "excelente",
                "perfecto", "muchas bendiciones", "muy amable", "listo gracias", "vale gracias"
            ],
            "answer": (
                "¡Con el mayor de los gustos! En Monagua amamos compartir la magia de Boyacá y cuidar "
                "la naturaleza. Si requieres algo más para tu aventura o tu reserva, aquí estaré. "
                "¡Que disfrutes tu viaje!"
            ),
            "options": ["Ver destinos", "¿Cómo reservar?", "¿Cuáles son sus horarios?"]
        },
        {
            "id": "ubicacion",
            "keywords": [
                "ubicacion", "direccion", "donde estan", "donde quedan", "donde se encuentran",
                "donde esta ubicado", "como llegar", "donde queda mongua", "en que ciudad estan",
                "en que municipio", "donde estan ubicados", "sede", "oficina", "punto de encuentro"
            ],
            "answer": (
                "Monagua Turismo tiene su centro de operaciones en el municipio de **Mongua, Boyacá, Colombia** "
                "(provincia de Sugamuxi, a 35 minutos de Sogamoso). Los puntos de salida para las expediciones "
                "se coordinan en el Parque Principal de Mongua frente al templo parroquial."
            ),
            "link_url": "/nosotros/",
            "link_text": "Conoce más sobre nosotros",
            "options": ["¿Cómo llegar desde Bogotá?", "¿Qué tours ofrecen?", "¿Cuál es el clima?"]
        },
        {
            "id": "transporte",
            "keywords": [
                "como llegar a mongua", "como viajar", "transporte", "como llego",
                "llegar desde bogota", "llegar desde tunja", "llegar desde sogamoso",
                "como llegar desde bogota", "como llegar desde tunja", "como llegar desde sogamoso",
                "bus", "flota", "terminal", "carro", "viajar a mongua", "carretera", "pasajes"
            ],
            "answer": (
                "Para llegar a Mongua desde Bogotá o Tunja: tomas un autobús hacia la Terminal de Sogamoso "
                "(aprox. 3 horas y media desde Bogotá). Desde la terminal de Sogamoso salen vehículos intermunicipales "
                "frecuentes hacia Mongua por vía pavimentada (trayecto de 35 a 45 minutos)."
            ),
            "options": ["¿Dónde están ubicados?", "¿Cuáles son los atractivos?", "¿Cómo reservar?"]
        },
        {
            "id": "atractivos",
            "keywords": [
                "paramo de oceta", "oceta", "laguna negra", "morro de san pedro",
                "peña de oti", "ciudad de piedra", "cascada desaguadero", "frailejones",
                "muisca", "arte rupestre", "pictogramas", "atractivos", "lugares para visitar",
                "sitios turisticos", "que conocer", "que ver en mongua", "monumentos"
            ],
            "answer": (
                "Mongua cuenta con escenarios naturales y arqueológicos excepcionales:\n"
                "• **Páramo de Ocetá**: La Ciudad de Piedra, jardines de frailejones y cascadas.\n"
                "• **Laguna Negra**: Espejo de agua místico de origen glaciar.\n"
                "• **Morro de San Pedro y Peña de Otí**: Miradores panorámicos de alta montaña.\n"
                "• **Cultura Muisca**: Petroglifos, pinturas rupestres y senderos ancestrales."
            ),
            "link_url": "/tours/",
            "link_text": "Explorar catálogo de destinos",
            "options": ["Ver tours disponibles", "¿Qué ropa llevar?", "¿Cuál es la dificultad?"]
        },
        {
            "id": "servicios_tours",
            "keywords": [
                "servicios", "servicios ofrecen", "que hacen", "actividad", "actividades",
                "tour", "tours", "paquete", "paquetes", "planes", "plan", "experiencias",
                "excursiones", "caminatas", "senderismo", "trekking", "ecoturismo", "destinos",
                "que tours tienen", "tours tienen", "tours disponibles", "paquetes disponibles",
                "planes disponibles", "que paquetes hay", "que tours hay", "catalogo de tours"
            ],
            "answer": (
                "En Monagua ofrecemos paquetes ecoturísticos guiados con póliza médica incluida. "
                "Nuestros tours más destacados disponibles actualmente son:\n\n"
                f"{tours_dinamicos}\n\n"
                "Puedes revisar el itinerario completo y la dificultad de cada uno en la sección de Destinos."
            ),
            "link_url": "/tours/",
            "link_text": "Ver todos los tours",
            "options": ["¿Cuánto cuestan los paquetes?", "¿Cómo reservar?", "¿Qué incluye la póliza?"]
        },
        {
            "id": "precios",
            "keywords": [
                "precio", "precios", "costo", "costos", "tarifas", "tarifa", "cuanto vale",
                "cuanto cuesta", "que cobran", "cotizar", "valores", "valor", "cuanto cobran"
            ],
            "answer": (
                "Nuestras tarifas varían según el paquete turístico, la duración (días/noches), "
                "la temporada (baja o alta) y el número de viajeros. Todos los paquetes incluyen "
                "acompañamiento de guía certificado y póliza de viaje. Puedes cotizar en tiempo real en 'Destinos'."
            ),
            "link_url": "/tours/",
            "link_text": "Consultar tarifas en Destinos",
            "options": ["¿Cómo reservar un tour?", "¿Qué métodos de pago aceptan?", "¿Hay promociones?"]
        },
        {
            "id": "promociones",
            "keywords": [
                "promocion", "promociones", "descuento", "descuentos", "oferta", "ofertas",
                "cupon", "cupones", "codigo promocional", "rebajas", "temporada baja"
            ],
            "answer": (
                "¡Tenemos ofertas y descuentos especiales para ti! Estas son algunas promociones activas:\n\n"
                f"{promos_dinamicas}\n\n"
                "Aprovecha estos beneficios ingresando a nuestra sección de Ofertas."
            ),
            "link_url": "/promociones/",
            "link_text": "Ver promociones vigentes",
            "options": ["Ver catálogo de tours", "¿Cómo reservar?", "¿Qué métodos de pago aceptan?"]
        },
        {
            "id": "reserva",
            "keywords": [
                "reserva", "reservas", "como reservar", "agendar", "apartar", "cupo",
                "cupos", "booking", "separar", "programar", "hacer reserva", "pasos para reservar"
            ],
            "answer": (
                "Reservar tu experiencia es muy sencillo:\n"
                "1. Ingresa a la sección **Destinos**.\n"
                "2. Selecciona el tour de tu preferencia y la fecha deseada.\n"
                "3. Indica la cantidad de personas y añade al carrito.\n"
                "4. Confirma tu reserva y adjunta el comprobante de transferencia en el módulo de pagos."
            ),
            "link_url": "/tours/",
            "link_text": "Ir a reservar un tour",
            "options": ["¿Cómo realizar el pago?", "¿Cuáles son las políticas de cancelación?", "Mis reservas"]
        },
        {
            "id": "mis_reservas_consulta",
            "keywords": [
                "mis reservas", "mi reserva", "como va mi reserva", "estado de mi reserva",
                "consultar mi reserva", "ver mis reservas", "historial de reservas"
            ],
            "answer": "",  # Se autogenera dinámicamente según el usuario
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Ver mis reservas",
            "options": ["Enviar comprobante", "Radicar PQRS", "¿Cuáles son sus horarios?"]
        },
        {
            "id": "pago",
            "keywords": [
                "pago", "pagos", "como pagar", "metodo de pago", "metodos de pago",
                "formas de pago", "transferencia", "nequi", "daviplata", "bancolombia",
                "banco", "comprobante", "subir comprobante", "enviar comprobante", "consignacion"
            ],
            "answer": (
                "Aceptamos transferencias bancarias (Bancolombia, Davivienda, etc.) y billeteras "
                "digitales (Nequi y Daviplata). Tras realizar el pago, debes ir a **Enviar Comprobante**, "
                "elegir tu reserva, ingresar la referencia de la transacción y subir la imagen para su aprobación."
            ),
            "link_url": "/pagos/enviar-comprobante/",
            "link_text": "Enviar comprobante de pago",
            "options": ["Mis reservas", "¿Cómo reservar?", "Políticas de cancelación"]
        },
        {
            "id": "cancelacion",
            "keywords": [
                "cancelar", "reembolso", "devolucion", "cancelacion", "retracto",
                "cancelado", "reembolsar", "anular reserva", "cambiar fecha", "reprogramar", "penalidad"
            ],
            "answer": (
                "Puedes gestionar la cancelación de tu reserva directamente desde tu panel en **Mis Reservas**. "
                "Las solicitudes tramitadas con más de 48 horas de anticipación a la salida aplican a mejores condiciones "
                "de reembolso o reprogramación con mínimas penalidades según los términos y condiciones de la agencia."
            ),
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Gestionar mis reservas",
            "options": ["Términos y condiciones", "¿Cómo contactar a un asesor?", "Radicar PQRS"]
        },
        {
            "id": "guias",
            "keywords": [
                "guia", "guias", "acompañante", "acompañantes", "orientador",
                "quien nos acompaña", "guia turistico", "guia certificado", "sena",
                "idioma guia", "guia bilingue"
            ],
            "answer": (
                "Todos nuestros tours son dirigidos por guías comunitarios y profesionales "
                "certificados por el SENA o inscritos en el Registro Nacional de Turismo (RNT). "
                "Cuentan con amplia experiencia en alta montaña, primeros auxilios, conocimiento de flora y fauna, "
                "y respeto absoluto por el patrimonio Muisca."
            ),
            "options": ["¿Qué tours ofrecen?", "¿Qué incluye la póliza de viaje?", "¿Qué ropa llevar?"]
        },
        {
            "id": "seguro_poliza",
            "keywords": [
                "seguro", "seguros", "poliza", "polizas", "asistencia medica",
                "seguro de viaje", "seguro medico", "emergencia", "primeros auxilios",
                "accidente", "cobertura"
            ],
            "answer": (
                "¡Tu seguridad es lo primero! Cada paquete turístico confirmado en Monagua incluye "
                "una póliza de asistencia médica y seguro de viaje para cubrir eventualidades, rescate "
                "y accidentes personales durante todo el recorrido con aseguradoras autorizadas."
            ),
            "options": ["Ver tours disponibles", "¿Qué recomendaciones debo seguir?", "¿Cómo reservar?"]
        },
        {
            "id": "clima_ropa",
            "keywords": [
                "clima", "temperatura", "frio", "llueve", "lluvia", "que llevar",
                "ropa", "que ropa llevar", "calzado", "zapatos", "botas", "chaqueta",
                "impermeable", "bloqueador", "equipaje", "mochila"
            ],
            "answer": (
                "Mongua y el Páramo de Ocetá tienen clima frío de páramo (entre 7°C y 16°C). "
                "Te sugerimos vestir en tres capas:\n"
                "1. Prenda térmica transpirable.\n"
                "2. Saco abrigado o forro polar.\n"
                "3. Chaqueta impermeable o cortavientos.\n"
                "Usa botas de senderismo con buen agarre, gorro, guantes, protector solar ecológico y botella de agua reutilizable."
            ),
            "options": ["¿Cuál es la dificultad de las caminatas?", "¿Dónde están ubicados?", "Ver tours"]
        },
        {
            "id": "dificultad",
            "keywords": [
                "dificultad", "nivel de dificultad", "exigencia", "caminata dificil",
                "es dificil", "pueden ir niños", "adultos mayores", "tercera edad",
                "edad minima", "condicion fisica", "mal de altura", "soroche"
            ],
            "answer": (
                "Contamos con caminatas para diferentes niveles:\n"
                "• **Baja**: Rutas culturales y urbanas aptas para toda la familia y niños.\n"
                "• **Media**: Senderos campestres hacia cascadas y miradores.\n"
                "• **Alta**: Expediciones completas al Páramo de Ocetá (alturas mayores a 3.600 msnm).\n"
                "En cada ficha de paquete se detalla la distancia y nivel recomendado."
            ),
            "link_url": "/tours/",
            "link_text": "Ver niveles en los tours",
            "options": ["¿Qué ropa llevar?", "¿Tienen guías?", "¿Cómo reservar?"]
        },
        {
            "id": "mascotas",
            "keywords": [
                "mascota", "mascotas", "perro", "perros", "gato", "gatos", "animal",
                "animales", "pet", "petfriendly", "puedo llevar mi perro"
            ],
            "answer": (
                "Las mascotas son bienvenidas en los senderos rurales y rutas culturales del pueblo. "
                "Sin embargo, por regulación ambiental de protección de ecosistemas estratégicos, "
                "el ingreso de mascotas está restringido en las zonas de reserva estricta del Páramo de Ocetá "
                "para preservar los frailejones y la fauna nativa."
            ),
            "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "Radicar PQRS"]
        },
        {
            "id": "comida",
            "keywords": [
                "comida", "comidas", "restaurante", "almuerzo", "desayuno", "cena",
                "alimentacion", "bebida", "bebidas", "snacks", "refrigerio", "alimentos",
                "que comer", "donde comer", "gastronomia", "platos tipicos", "arepas"
            ],
            "answer": (
                "En Mongua puedes degustar la auténtica gastronomía boyacense: las famosas arepas monguanas "
                "de maíz pelado, caldos campesinos, trucha fresca y agua de panela con queso. "
                "Durante las caminatas es ideal portar snacks energéticos (frutos secos, bocadillo veleño y chocolate)."
            ),
            "options": ["Ver tours disponibles", "¿Cuáles son sus horarios?", "¿Dónde están ubicados?"]
        },
        {
            "id": "horarios",
            "keywords": [
                "horario", "horarios", "abren", "cierran", "apertura", "cierre",
                "atencion", "jornada", "a que hora", "que horas", "cuando abren", "dias de atencion"
            ],
            "answer": (
                "Nuestro horario de atención y soporte en plataforma es de **Lunes a Domingo de 8:00 AM a 6:00 PM**. "
                "Las salidas a campo e inicio de caminatas se programan temprano en la mañana "
                "(entre 6:00 AM y 7:00 AM) para aprovechar las mejores condiciones climáticas del páramo."
            ),
            "options": ["¿Cómo contactar a un asesor?", "¿Qué servicios ofrecen?", "Radicar PQRS"]
        },
        {
            "id": "contacto",
            "keywords": [
                "contacto", "telefono", "celular", "email", "correo", "llamar",
                "whatsapp", "comunicarse", "numero", "escribir", "contactar", "hablar con alguien", "asesor"
            ],
            "answer": (
                "Puedes comunicarte directamente con nuestro equipo mediante llamada o WhatsApp al "
                "**+57 322 3465191** o escribiendo al correo **contacto@monagua.com**. "
                "Si requieres radicar una petición, queja o reclamo formal, te invitamos a usar el apartado oficial de PQRS."
            ),
            "link_url": "/pqrs/",
            "link_text": "Ir a Radicar PQRS",
            "options": ["Radicar PQRS", "¿Dónde están ubicados?", "¿Cuáles son sus horarios?"]
        },
        {
            "id": "pqrs_radicar",
            "keywords": [
                "pqrs", "pqr", "peticion", "peticiones", "queja", "quejas", "reclamo",
                "reclamos", "sugerencia", "sugerencias", "ticket", "tickets", "soporte",
                "radicar", "radicado", "inconformidad", "radicar pqrs", "poner queja",
                "hacer reclamo", "como poner una queja", "felicitacion"
            ],
            "answer": (
                "En Monagua contamos con un apartado oficial para la radicación de **PQRS** "
                "(Peticiones, Quejas, Reclamos y Sugerencias). Puedes diligenciar tu solicitud en línea "
                "para recibir un número de radicado y seguimiento formal por parte de la administración."
            ),
            "action": "pqrs",
            "link_url": "/pqrs/",
            "link_text": "Radicar PQRS oficial",
            "options": ["Radicar PQRS", "Consultar mis PQRS", "¿Cuáles son sus horarios?"]
        },
        {
            "id": "pqrs_consultar",
            "keywords": [
                "seguimiento pqrs", "consultar pqrs", "estado pqrs", "mi radicado",
                "numero radicado", "donde veo mi pqrs", "mis pqrs", "mis solicitudes",
                "ver mi queja", "respuesta pqrs", "consultar solicitudes"
            ],
            "answer": "",  # Se autogenera dinámicamente según el usuario
            "action": "pqrs",
            "link_url": "/mis_pqrs/",
            "link_text": "Consultar mis solicitudes",
            "options": ["Consultar mis PQRS", "Radicar PQRS", "Volver a Inicio"]
        },
        {
            "id": "facturas",
            "keywords": [
                "factura", "facturas", "recibo", "descargar factura", "comprobante de reserva",
                "qr", "codigo qr", "pdf reserva"
            ],
            "answer": (
                "Una vez aprobado el comprobante de pago de tu reserva, el sistema genera automáticamente "
                "tu factura legal y comprobante oficial en formato PDF con código QR verificable. "
                "Puedes consultarla y descargarla en cualquier momento desde la sección 'Mis Reservas'."
            ),
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Ver mis reservas y facturas",
            "options": ["Mis reservas", "¿Cómo realizar el pago?", "¿Cómo reservar?"]
        },
        {
            "id": "cuenta_usuario",
            "keywords": [
                "registro", "registrarse", "crear cuenta", "abrir cuenta", "iniciar sesion",
                "login", "ingresar", "mi cuenta", "perfil", "olvide contraseña", "cambiar contraseña"
            ],
            "answer": (
                "Puedes registrarte o iniciar sesión utilizando el botón en la esquina superior derecha "
                "de la página. Con tu cuenta podrás realizar reservas, consultar comprobantes, descargar facturas "
                "y hacer seguimiento a tus solicitudes de PQRS."
            ),
            "options": ["¿Cómo reservar?", "Ver destinos", "Radicar PQRS"]
        },
        {
            "id": "artesanias",
            "keywords": [
                "artesanias", "recuerdos", "souvenirs", "lana", "tejidos", "ruanas",
                "fique", "artesanos", "compras en mongua"
            ],
            "answer": (
                "Mongua es reconocida por sus artesanos tradicionales expertos en el hilado de lana virgen, "
                "confección de ruanas boyacenses, cobijas campesinas y canastos en fique. En el pueblo "
                "encontrarás talleres locales donde podrás adquirir auténticas artesanías de la región."
            ),
            "options": ["¿Dónde están ubicados?", "Ver tours disponibles", "¿Cuáles son sus horarios?"]
        }
    ]

    return faqs


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL DE PROCESAMIENTO NLP
# ══════════════════════════════════════════════════════════════════════════════

def procesar_mensaje(mensaje, request):
    """
    Procesador avanzado de Cóndy:
    1. Si existe GEMINI_API_KEY, consulta Gemini AI con anclaje a datos reales de Monagua.
    2. Si no hay clave o falla la red, ejecuta el motor semántico local con conexión a base de datos.
    3. Personaliza la información si el usuario está autenticado (reservas, PQRS, nombre).
    4. Garantiza enrutamiento estricto a las rutas oficiales de la plataforma (/pqrs/, /tours/, etc.).
    """
    if 'condy_fallos' not in request.session:
        request.session['condy_fallos'] = 0

    if not mensaje or not mensaje.strip():
        return {
            "response": "¡Hola! ¿En qué puedo orientarte hoy? Puedes consultarme sobre tours, reservas, pagos o radicar una PQRS.",
            "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "¿Dónde están ubicados?", "Radicar PQRS"]
        }

    # Intentar responder mediante Gemini AI si la clave existe
    respuesta_ia = consultar_gemini(mensaje, request)
    if respuesta_ia:
        request.session['condy_fallos'] = 0
        return respuesta_ia

    # Motor local basado en reglas semánticas y base de datos
    mensaje_norm = normalizar_texto(mensaje)

    # Filtros de regulación y prevención de falsos positivos
    mensaje_norm = (
        mensaje_norm
        .replace("perros calientes", "comida")
        .replace("perro caliente", "comida")
        .replace("hot dog", "comida")
    )

    user = getattr(request, 'user', None)
    faqs = construir_faqs(user)

    mejor_coincidencia = None
    mejor_puntaje = 0

    for faq in faqs:
        puntaje = 0
        for keyword in faq["keywords"]:
            kw_norm = normalizar_texto(keyword)
            if not kw_norm:
                continue

            if " " in kw_norm:
                if kw_norm in mensaje_norm:
                    puntaje += 4
            else:
                patron = r'\b' + re.escape(kw_norm) + r'\b'
                if re.search(patron, mensaje_norm):
                    puntaje += 2

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_coincidencia = faq

    # Procesamiento dinámico para intenciones de usuario
    if mejor_coincidencia and mejor_puntaje >= 2:
        request.session['condy_fallos'] = 0
        respuesta_texto = mejor_coincidencia["answer"]

        # 1. Si consulta por sus reservas
        if mejor_coincidencia["id"] == "mis_reservas_consulta":
            resumen_res = obtener_resumen_reservas(user)
            if resumen_res:
                respuesta_texto = (
                    f"Tienes las siguientes reservas recientes registradas en tu cuenta:\n\n"
                    f"{resumen_res}\n\n"
                    f"Puedes ver la factura, comprobantes y estado detallado en 'Mis Reservas'."
                )
            elif user and user.is_authenticated:
                respuesta_texto = "Actualmente no tienes reservas activas registradas. ¡Te invitamos a explorar nuestros tours y reservar tu viaje!"
            else:
                respuesta_texto = "Para consultar el estado de tus reservas, por favor inicia sesión con tu cuenta de usuario."

        # 2. Si consulta por sus solicitudes PQRS
        elif mejor_coincidencia["id"] == "pqrs_consultar":
            resumen_pq = obtener_resumen_pqrs(user)
            if resumen_pq:
                respuesta_texto = (
                    f"Estas son tus solicitudes PQRS más recientes en el sistema:\n\n"
                    f"{resumen_pq}\n\n"
                    f"Puedes consultar el historial completo y respuestas en 'Mis PQRS'."
                )
            elif user and user.is_authenticated:
                respuesta_texto = "No tienes solicitudes PQRS pendientes en este momento. Si necesitas ayuda o radicar una nueva, puedes hacerlo en 'Radicar PQRS'."
            else:
                respuesta_texto = "Puedes consultar el estado y respuestas de todas tus PQRS desde tu cuenta en la sección 'Mis PQRS'."

        resultado = {
            "response": respuesta_texto,
            "action": mejor_coincidencia.get("action"),
            "options": mejor_coincidencia.get("options", [])
        }
        if "link_url" in mejor_coincidencia:
            resultado["link_url"] = mejor_coincidencia["link_url"]
            resultado["link_text"] = mejor_coincidencia.get("link_text", "Ver más")
        return resultado

    # Manejo de reintentos
    request.session['condy_fallos'] += 1

    if request.session['condy_fallos'] >= 2:
        request.session['condy_fallos'] = 0
        return {
            "response": (
                "No he logrado comprender tu consulta con exactitud. "
                "Para recibir atención formal y personalizada, te invito a radicar "
                "una solicitud en nuestro apartado oficial de PQRS o comunicarte por WhatsApp al +57 322 3465191."
            ),
            "fallback_action": "pqrs",
            "link_url": "/pqrs/",
            "link_text": "Radicar PQRS en Monagua",
            "options": ["Radicar PQRS", "¿Cuáles son sus horarios?", "¿Dónde están ubicados?"]
        }
    else:
        return {
            "response": (
                "Disculpa, no logré entender tu pregunta. "
                "¿Podrías escribirla con otras palabras o seleccionar alguna de las opciones frecuentes?"
            ),
            "options": [
                "¿Cuáles son sus horarios?",
                "¿Qué tours ofrecen?",
                "¿Cómo realizar un pago?",
                "Radicar PQRS"
            ]
        }
