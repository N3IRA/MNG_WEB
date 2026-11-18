import re
import unicodedata

# ══════════════════════════════════════════════════════════════════════════════
# BASE DE CONOCIMIENTO INTEGRAL DE CÓNDY (MONAGUA TURISMO - MONGUA, BOYACÁ)
# ══════════════════════════════════════════════════════════════════════════════

FAQS = [
    {
        "id": "saludo",
        "keywords": [
            "hola", "buen dia", "buenos dias", "buenas tardes", "buenas noches",
            "hey", "saludos", "que tal", "como estas", "que hubo", "buenas",
            "hi", "hello", "buena tarde", "buen dia condy", "hola condy"
        ],
        "answer": (
            "¡Hola! Te doy una cálida bienvenida a Monagua Turismo. Soy Cóndy, "
            "tu asistente y cóndor guardián en Mongua, Boyacá. ¿En qué te puedo "
            "ayudar hoy? Puedes consultarme sobre tours ecológicos, reservas, "
            "pagos, guías o radicar una PQRS."
        ),
        "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "¿Dónde están ubicados?", "Radicar PQRS"]
    },
    {
        "id": "identidad",
        "keywords": [
            "quien eres", "que eres", "como te llamas", "tu nombre", "eres un bot",
            "eres una ia", "eres un robot", "que es condy", "quien es condy", "presentate"
        ],
        "answer": (
            "Soy Cóndy, el cóndor guardián y asistente virtual oficial de "
            "Monagua Turismo. Nací en los cielos del Páramo de Ocetá para orientarte "
            "sobre nuestros destinos ecológicos en Mongua, resolver tus dudas sobre reservas "
            "y guiarte en todo momento."
        ),
        "options": ["¿Dónde están ubicados?", "¿Qué actividades tienen?", "¿Cómo contactar a un asesor?"]
    },
    {
        "id": "despedida_agradecimiento",
        "keywords": [
            "gracias", "muchas gracias", "mil gracias", "te agradezco", "chao",
            "adios", "hasta luego", "nos vemos", "que estes bien", "excelente",
            "perfecto", "muchas bendiciones", "muy amable", "listo gracias"
        ],
        "answer": (
            "¡Con muchísimo gusto! En Monagua amamos compartir la magia de Boyacá. "
            "Si requieres algo más para tu viaje o tu reserva, aquí estaré. "
            "¡Que tengas una experiencia inolvidable!"
        ),
        "options": ["Ver destinos", "Mis reservas", "¿Cuáles son sus horarios?"]
    },
    {
        "id": "ubicacion",
        "keywords": [
            "ubicacion", "direccion", "donde estan", "donde quedan", "donde se encuentran",
            "donde esta ubicado", "como llegar", "donde queda mongua", "en que ciudad estan",
            "en que municipio", "donde estan ubicados", "sede", "oficina"
        ],
        "answer": (
            "Monagua Turismo opera en el municipio de Mongua, Boyacá, Colombia "
            "(provincia de Sugamuxi, a unos 35 minutos de Sogamoso). Los puntos de encuentro "
            "y salida de nuestras expediciones se realizan habitualmente en el Parque Principal "
            "de Mongua frente a la parroquia central."
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
            "bus", "flota", "terminal", "carro", "viajar a mongua", "carretera"
        ],
        "answer": (
            "Para llegar a Mongua desde Bogotá o Tunja: tomas un autobús hacia la "
            "Terminal de Transportes de Sogamoso (aprox. 3 horas y media desde Bogotá). "
            "Desde la terminal de Sogamoso salen vehículos y microbuses frecuentes hacia Mongua "
            "(recorrido pavimentado de 35 a 45 minutos)."
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
            "Mongua cuenta con joyas naturales y arqueológicas únicas: el majestuoso "
            "Páramo de Ocetá (con sus valles de frailejones y la Ciudad de Piedra), "
            "la mística Laguna Negra, el mirador del Morro de San Pedro, la Peña de Otí, "
            "la Cascada del Desaguadero y senderos con arte rupestre y petroglifos Muiscas."
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
            "excursiones", "caminatas", "senderismo", "trekking", "ecoturismo"
        ],
        "answer": (
            "Ofrecemos paquetes ecoturísticos integrales: caminatas guiadas de alta montaña, "
            "rutas de avistamiento de aves y flora, expediciones al Páramo de Ocetá, circuitos "
            "arqueológicos y culturales, con guías locales certificados y póliza de asistencia médica incluida."
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
            "acompañamiento de guía local y seguro de viaje. Consulta las tarifas vigentes en 'Destinos'."
        ),
        "link_url": "/tours/",
        "link_text": "Consultar precios en Destinos",
        "options": ["¿Cómo reservar un tour?", "¿Qué métodos de pago aceptan?", "¿Hay promociones?"]
    },
    {
        "id": "promociones",
        "keywords": [
            "promocion", "promociones", "descuento", "descuentos", "oferta", "ofertas",
            "cupon", "cupones", "codigo promocional", "rebajas", "temporada baja"
        ],
        "answer": (
            "En Monagua publicamos ofertas de temporada y cupones de descuento especiales "
            "para grupos y viajeros frecuentes. Puedes revisar las promociones activas con sus "
            "porcentajes de descuento y condiciones en nuestra sección de Ofertas."
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
            "Para reservar: 1) Ve a la sección 'Destinos', 2) Elige tu tour preferido, "
            "3) Selecciona la fecha y cantidad de personas, 4) Añade al carrito y confirma "
            "tu reserva. Luego podrás adjuntar tu comprobante de pago en el módulo correspondiente."
        ),
        "link_url": "/tours/",
        "link_text": "Ir al catálogo de Destinos",
        "options": ["¿Cómo realizar el pago?", "¿Cuáles son las políticas de cancelación?", "Mis reservas"]
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
            "digitales como Nequi y Daviplata. Una vez realizada la transferencia, subes tu "
            "comprobante en la sección 'Enviar Comprobante' indicando la referencia para su validación."
        ),
        "link_url": "/pagos/enviar-comprobante/",
        "link_text": "Enviar comprobante de pago",
        "options": ["Mis comprobantes", "¿Cómo reservar?", "Políticas de cancelación"]
    },
    {
        "id": "cancelacion",
        "keywords": [
            "cancelar", "reembolso", "devolucion", "cancelacion", "retracto",
            "cancelado", "reembolsar", "anular reserva", "cambiar fecha", "reprogramar", "penalidad"
        ],
        "answer": (
            "Puedes gestionar la cancelación de tu reserva desde 'Mis Reservas'. Las "
            "solicitudes efectuadas con al menos 48 horas de anticipación a la fecha de inicio "
            "aplican a mejores condiciones de reembolso o reprogramación según los términos del servicio."
        ),
        "link_url": "/reservas/mis-reservas/",
        "link_text": "Ir a Mis Reservas",
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
            "Todos nuestros tours cuentan con guías comunitarios y profesionales "
            "certificados por el SENA o con Registro Nacional de Turismo (RNT), formados "
            "en primeros auxilios, orientación en alta montaña y conocimiento de la biodiversidad local."
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
            "Tu seguridad es primordial. Todos los paquetes turísticos confirmados en "
            "Monagua incluyen póliza de asistencia médica y seguro de viaje para imprevistos "
            "y accidentes personales durante todo el itinerario."
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
            "Mongua y el Páramo de Ocetá poseen clima frío de alta montaña (entre 7°C y 16°C). "
            "Te sugerimos vestir en tres capas: 1) Prenda térmica, 2) Chaqueta abrigada o forro polar, "
            "3) Cortavientos o impermeable. Usa botas de trekking con agarre, gorro, guantes y bloqueador solar."
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
            "Ofrecemos caminatas para diferentes capacidades físicas: desde senderos culturales "
            "suaves para toda la familia, hasta travesías de alta exigencia en el Páramo de Ocetá "
            "(superando los 3.600 msnm). En la descripción de cada paquete se detalla su nivel."
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
            "Sin embargo, en las zonas de reserva estricta de páramo existen restricciones ambientales "
            "para proteger los frailejones y la fauna nativa."
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
            "En Mongua puedes deleitarte con la gastronomía típica boyacense: arepas "
            "monguanas de maíz pelado, caldos campesinos, trucha fresca y agua de panela con queso. "
            "Para las caminatas recomendamos llevar frutos secos, bocadillo y agua."
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
            "Nuestro horario de atención y soporte en plataforma es de Lunes a Domingo "
            "de 8:00 AM a 6:00 PM. Las salidas y caminatas a campo se inician habitualmente "
            "en las mañanas entre las 6:00 AM y las 7:00 AM según el itinerario del tour."
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
            "Puedes comunicarte con nuestro equipo al teléfono o WhatsApp **+57 322 3465191** "
            "o al correo **contacto@monagua.com**. Para radicaciones formales, te invitamos a usar "
            "nuestro apartado de PQRS en la web."
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
            "En Monagua contamos con un apartado oficial para la radicación de PQRS "
            "(Peticiones, Quejas, Reclamos y Sugerencias). Puedes diligenciar tu solicitud en línea "
            "para que nuestro equipo administrativo le dé trámite y te brinde respuesta formal."
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
        "answer": (
            "Puedes consultar el estado, historial y respuestas de todas tus solicitudes "
            "directamente en el apartado de 'Mis PQRS' de tu cuenta."
        ),
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
            "Cuando tu reserva es aprobada, el sistema genera automáticamente tu comprobante "
            "y factura en PDF con código QR oficial. Puedes consultarla y descargarla en 'Mis Reservas'."
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
            "Puedes registrarte o iniciar sesión con el botón en la esquina superior derecha "
            "de la página. Con tu cuenta podrás reservar, consultar comprobantes, descargar facturas "
            "y radicar o consultar tus PQRS."
        ),
        "options": ["¿Cómo reservar?", "Ver destinos", "Radicar PQRS"]
    }
]

def remove_accents(input_str):
    """Elimina tildes y caracteres diacríticos para normalización fonética."""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])


def normalizar_texto(texto):
    """Limpia caracteres especiales, espacios y acentos."""
    texto = remove_accents(texto.lower().strip())
    # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def procesar_mensaje(mensaje, request):
    """
    Motor NLP de Condy: evalúa similitud por frases clave y tokens con pesos.
    Evita falsos positivos, elimina alucinaciones y redirige al apartado oficial de PQRS.
    """
    if 'condy_fallos' not in request.session:
        request.session['condy_fallos'] = 0

    if not mensaje or not mensaje.strip():
        return {
            "response": "¿En qué puedo colaborarte hoy? Puedes preguntarme sobre tours, reservas, pagos o PQRS.",
            "options": ["¿Qué tours ofrecen?", "¿Cómo reservar?", "¿Dónde están ubicados?", "Radicar PQRS"]
        }

    mensaje_norm = normalizar_texto(mensaje)

    # Filtros de regulación y prevención de falsos positivos
    mensaje_norm = (
        mensaje_norm
        .replace("perros calientes", "comida")
        .replace("perro caliente", "comida")
        .replace("hot dog", "comida")
    )

    mejor_coincidencia = None
    mejor_puntaje = 0

    for faq in FAQS:
        puntaje = 0
        for keyword in faq["keywords"]:
            kw_norm = normalizar_texto(keyword)
            if not kw_norm:
                continue

            # Si es frase compuesta (más de una palabra), tiene mayor peso
            if " " in kw_norm:
                if kw_norm in mensaje_norm:
                    puntaje += 4
            else:
                # Búsqueda exacta de palabra completa con límites \b
                patron = r'\b' + re.escape(kw_norm) + r'\b'
                if re.search(patron, mensaje_norm):
                    puntaje += 2

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_coincidencia = faq

    # Umbral mínimo para considerar coincidencia válida
    if mejor_coincidencia and mejor_puntaje >= 2:
        request.session['condy_fallos'] = 0
        resultado = {
            "response": mejor_coincidencia["answer"],
            "action": mejor_coincidencia.get("action"),
            "options": mejor_coincidencia.get("options", [])
        }
        if "link_url" in mejor_coincidencia:
            resultado["link_url"] = mejor_coincidencia["link_url"]
            resultado["link_text"] = mejor_coincidencia.get("link_text", "Ver más")
        return resultado

    # En caso de no comprender el mensaje tras varios intentos
    request.session['condy_fallos'] += 1

    if request.session['condy_fallos'] >= 2:
        request.session['condy_fallos'] = 0
        return {
            "response": (
                "No he logrado comprender tu consulta con exactitud. "
                "Para brindarte una atención personalizada, puedes radicar "
                "una solicitud formal en nuestro apartado oficial de PQRS "
                "o escribirnos a WhatsApp al +57 322 3465191."
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
                "¿Podrías escribirla con otras palabras o elegir uno de los temas frecuentes?"
            ),
            "options": [
                "¿Cuáles son sus horarios?",
                "¿Qué tours ofrecen?",
                "¿Cómo realizar un pago?",
                "Radicar PQRS"
            ]
        }
