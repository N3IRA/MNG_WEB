import os
import re
import json
import time
import logging
import unicodedata
import urllib.request
import urllib.error
from decimal import Decimal
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Control de resiliencia y disyuntor (Circuit Breaker) para cortes de internet saliente
_LAST_INTERNET_ERROR_TIME = 0.0
_CIRCUIT_BREAKER_COOLDOWN_SECONDS = (
    45.0  # 45 segundos de pausa antes de reintentar si no hay internet
)


MAPA_CORRECCIONES_TIPOGRAFICAS = {
    # Errores frecuentes fonéticos / ortográficos en turismo y plataforma
    "reserba": "reserva", "reserbas": "reservas", "reserbar": "reservar",
    "prezio": "precio", "presio": "precio", "presios": "precios", "prezios": "precios",
    "frailehones": "frailejones", "frailehon": "frailejon", "fraylejon": "frailejon", "fraylejones": "frailejones",
    "dabiplata": "daviplata", "dabyplata": "daviplata", "nekwi": "nequi", "neki": "nequi",
    "bancolombia": "bancolombia", "bancolombiya": "bancolombia",
    "canzelar": "cancelar", "canzelacion": "cancelacion", "cancelasion": "cancelacion",
    "conprobante": "comprobante", "conprobantes": "comprobantes", "comprovante": "comprobante",
    "tur": "tour", "turs": "tours", "tuor": "tour", "tuors": "tours",
    "espedicion": "expedicion", "espediciones": "expediciones",
    "oceta": "oceta", "oseta": "oceta", "ozeta": "oceta",
    "monga": "mongua", "monwa": "mongua",
    "alusinacion": "alucinacion", "alusinaciones": "alucinaciones", "alucinasion": "alucinacion",
    "reembolzo": "reembolso", "rembolso": "reembolso", "reembolsar": "reembolsar",
    "soroche": "soroche", "sorocho": "soroche",
    "politica": "politica", "politicas": "politicas", "normatiba": "normativa",
}


def remove_accents(input_str):
    """Elimina tildes y caracteres diacríticos para normalización fonética."""
    if not input_str:
        return ""
    nfkd_form = unicodedata.normalize("NFKD", input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])


def normalizar_texto(texto):
    """Limpia caracteres especiales, espacios, acentos y corrige errores tipográficos/fonéticos."""
    if not texto:
        return ""
    texto = remove_accents(texto.lower().strip())
    texto = re.sub(r"[\r\n\t]+", " ", texto)
    texto = re.sub(r"[^\w\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    palabras = texto.split()
    palabras_corregidas = [MAPA_CORRECCIONES_TIPOGRAFICAS.get(p, p) for p in palabras]
    return " ".join(palabras_corregidas).strip()


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CONSULTA DINÁMICA A LA BASE DE DATOS (GROUNDING EN TIEMPO REAL)
# ══════════════════════════════════════════════════════════════════════════════


def obtener_tours_destacados():
    """Consulta los paquetes activos en la base de datos."""
    try:
        from App.models import Paquete

        tours = list(Paquete.objects.filter(estado=True).order_by("id")[:5])
        if tours:
            nombres = []
            for t in tours:
                cat_nombre = (
                    getattr(t.categoria, "nombre", "Ecoturismo")
                    if getattr(t, "categoria", None)
                    else "Ecoturismo"
                )
                duracion = f"{t.dias_duracion} día{'s' if t.dias_duracion > 1 else ''}"
                nombres.append(f"• **{t.nombre}** ({duracion} — {cat_nombre})")
            return "\n".join(nombres)
    except Exception:
        pass
    return "• **Mongua Mágico** (senderos de páramo y cascadas)\n• **Ruta del Páramo de Ocetá** (Ciudad de Piedra y frailejones)\n• **Aventura Laguna Negra** (espejo glaciar sagrado)"


def obtener_promociones_activas():
    """Consulta las promociones vigentes en la base de datos."""
    try:
        from App.models import Promocion

        hoy = timezone.now().date()
        promos = list(
            Promocion.objects.filter(
                activa=True, fecha_inicio__lte=hoy, fecha_fin__gte=hoy
            )[:3]
        )
        if promos:
            detalles = []
            for p in promos:
                cupon_txt = f" (Cupón: `{p.codigo_cupon}`)" if p.codigo_cupon else ""
                detalles.append(
                    f"• **{p.nombre}**: {p.porcentaje_descuento}% de descuento{cupon_txt}"
                )
            return "\n".join(detalles)
    except Exception:
        pass
    return "• **Descuento de Temporada Baja**: Hasta 10% de ahorro en tours seleccionados.\n• **Promoción Grupal**: Consulta ofertas vigentes en nuestro catálogo."


def obtener_resumen_reservas(user):
    """Consulta las reservas recientes del usuario autenticado."""
    if not user or not user.is_authenticated:
        return None
    try:
        from App.models import Reserva

        reservas = list(
            Reserva.objects.filter(usuario=user)
            .select_related("paquete")
            .order_by("-id")[:3]
        )
        if reservas:
            lineas = []
            for r in reservas:
                paquete_nombre = getattr(r.paquete, "nombre", "Tour")
                fecha = (
                    r.fecha_inicio.strftime("%d/%m/%Y")
                    if r.fecha_inicio
                    else "Fecha por definir"
                )
                total = (
                    f"COP ${r.monto_total:,.0f}" if r.monto_total else "Por liquidar"
                )
                lineas.append(
                    f"• **Reserva #{r.id}** ({paquete_nombre}) — Fecha: {fecha} — {total} — Estado: **{r.get_estado_reserva_display()}**"
                )
            return "\n".join(lineas)
    except Exception:
        pass
    return None


def obtener_resumen_pqrs(user):
    """Consulta las solicitudes PQRS recientes del usuario autenticado."""
    if not user or not user.is_authenticated:
        return None
    try:
        from App.models import PQRS

        pqrs_list = list(PQRS.objects.filter(usuario=user).order_by("-id")[:3])
        if pqrs_list:
            lineas = []
            for p in pqrs_list:
                estado_txt = getattr(p, "estado", "Pendiente")
                if hasattr(p, "get_estado_display"):
                    estado_txt = p.get_estado_display()
                lineas.append(
                    f"• **Radicado #{p.id}** ('{p.asunto[:35]}...') — Estado: **{estado_txt}**"
                )
            return "\n".join(lineas)
    except Exception:
        pass
    return None


def obtener_resumen_saldo_favor(user):
    """Consulta el saldo a favor y notas de crédito del usuario autenticado."""
    if not user or not user.is_authenticated:
        return None
    try:
        saldo = getattr(user, "saldo_favor", Decimal("0.00"))
        lineas = [f"Tu saldo a favor actual en cuenta es: **COP ${saldo:,.0f}**."]
        from App.models import NotaCredito

        notas = list(
            NotaCredito.objects.filter(usuario=user).order_by("-fecha_emision")[:2]
        )
        if notas:
            lineas.append("Notas de crédito recientes:")
            for nc in notas:
                lineas.append(
                    f"• `{nc.codigo}`: COP ${nc.monto_devuelto:,.0f} ({nc.get_estado_display()})"
                )
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
    telefonos_inventados = re.findall(r"(?:\+?57)?\s*3\d{2}[- ]?\d{3}[- ]?\d{4}", texto)
    for tel in telefonos_inventados:
        tel_limpio = re.sub(r"[\s\-+]", "", tel)
        if "3223465191" not in tel_limpio:
            texto = texto.replace(tel, "+57 322 3465191")

    # Garantizar correo oficial
    correos_inventados = re.findall(r"[\w\.-]+@[\w\.-]+\.\w+", texto)
    for c in correos_inventados:
        if "monagua" not in c.lower():
            texto = texto.replace(c, "contacto@monagua.com")

    # Anti-alucinación: corregir afirmaciones sobre métodos de pago no soportados
    if re.search(r'\b(paypal|tarjeta de cr[eé]dito directa|criptomonedas?|bitcoin|binance)\b', texto, re.IGNORECASE):
        texto = re.sub(
            r'(?:aceptamos|puedes pagar con|mediante)\s*(?:paypal|tarjeta de cr[eé]dito directa|cripto\w*|bitcoin)[^.\n]*[.\n]?',
            'En Monagua Turismo los pagos oficiales se realizan por transferencia bancaria (Bancolombia) o billeteras digitales (Nequi y Daviplata). ',
            texto,
            flags=re.IGNORECASE
        )

    # Corregir URLs hacia rutas oficiales de la plataforma
    reemplazos_urls = [
        (r"/contacto(?:\.html)?\b", "/pqrs/"),
        (r"/reservar(?:\.html)?\b", "/tours/"),
        (r"/pago(?:\.html)?\b", "/pagos/enviar-comprobante/"),
        (r"/comprobante(?:\.html)?\b", "/pagos/enviar-comprobante/"),
        (r"/ofertas(?:\.html)?\b", "/promociones/"),
        (r"/articulos(?:\.html)?\b", "/blog/"),
        (r"/calificaciones(?:\.html)?\b", "/calificaciones/mis-calificaciones/"),
    ]
    for patron, reemplazo in reemplazos_urls:
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)

    return texto


def consultar_gemini(mensaje, request):
    """
    Si existe GEMINI_API_KEY configurada, procesa el mensaje con Google Gemini
    proporcionándole contexto estricto de Monagua con guardrails anti-alucinación.
    Si falla el internet o no hay clave, activa de inmediato el motor local sin interrumpir al usuario.
    """
    global _LAST_INTERNET_ERROR_TIME

    # Disyuntor (Circuit Breaker): si recientemente falló la conexión a internet, evitar latencia y pasar a local
    ahora = time.time()
    if ahora - _LAST_INTERNET_ERROR_TIME < _CIRCUIT_BREAKER_COOLDOWN_SECONDS:
        return None

    api_key = getattr(settings, "GEMINI_API_KEY", "") or os.environ.get(
        "GEMINI_API_KEY", ""
    )
    if not api_key:
        return None

    # Contexto del sistema para anclar la IA a los datos reales de Monagua
    tours_context = obtener_tours_destacados()
    promos_context = obtener_promociones_activas()

    user = getattr(request, "user", None)
    usuario_info = ""
    if user and user.is_authenticated:
        usuario_info = f"\nInformación del usuario autenticado:\n- Nombre: {user.get_full_name() or user.username}\n"
        res_info = obtener_resumen_reservas(user)
        if res_info:
            usuario_info += f"- Sus reservas registradas:\n{res_info}\n"
        pq_info = obtener_resumen_pqrs(user)
        if pq_info:
            usuario_info += f"- Sus solicitudes PQRS:\n{pq_info}\n"
        saldo_info = obtener_resumen_saldo_favor(user)
        if saldo_info:
            usuario_info += f"- Su saldo a favor:\n{saldo_info}\n"

    system_instruction = (
        "Eres Cóndy, el cóndor andino guardián y asistente virtual oficial de 'Monagua Turismo', "
        "agencia comunitaria de ecoturismo en el municipio de Mongua, Boyacá, Colombia.\n\n"
        "REGLAS ESTRICTAS Y REGULACIONES DE LA PLATAFORMA (CÚMPLELAS SIN EXCEPCIÓN):\n"
        "1. REGULACIONES AMBIENTALES Y LEGALES (LEY 1930 DE 2018 - LEY DE PÁRAMOS):\n"
        "   - Prohibido terminantemente tocar, arrancar o pisar frailejones (Espeletia) y musgos de páramo. "
        "     Son especies protegidas vitales para el agua de Colombia; destruirlas acarrea sanciones penales y ambientales.\n"
        "   - Principio 'No Deje Rastro': CERO basura. Todo residuo plástico, empaque o residuo orgánico debe regresar con el turista.\n"
        "   - Prohibidas fogatas, hornillas, colillas de cigarrillos o cualquier fuente de ignición en páramos y reservas naturales.\n"
        "   - Prohibida la extracción de fósiles, piedras, flora nativa o fauna silvestre.\n"
        "   - Respeto al patrimonio arqueológico Muisca: prohibido rayar, pintar o tocar los petroglifos y pictogramas.\n"
        "   - Drones: Prohibido su vuelo en reservas y áreas protegidas sin permiso expreso de Corpoboyacá / Parque Natural.\n"
        "   - Mascotas: Restringidas en zonas de reserva estricta de alta montaña para proteger la fauna silvestre.\n"
        "2. REGULACIONES OPERATIVAS Y DE SEGURIDAD:\n"
        "   - El ascenso a alta montaña exige ACOMPAÑAMIENTO OBLIGATORIO DE GUÍAS LOCALES CERTIFICADOS (RNT / SENA).\n"
        "   - Toda reserva confirmada incluye PÓLIZA DE ASISTENCIA MÉDICA Y SEGURO DE VIAJE contra accidentes y rescate.\n"
        "   - Salidas muy temprano (6:00 AM - 7:00 AM) por seguridad meteorológica del páramo.\n"
        "   - Exigencia de ropa por capas (térmica, polar, cortavientos/impermeable) y calzado de trekking con agarre.\n"
        "3. UBICACIÓN EXCLUSIVA:\n"
        "   - Monagua opera ÚNICAMENTE en el municipio de Mongua, Boyacá (a 35-40 min de Sogamoso).\n"
        "   - Sus atractivos son: Páramo de Ocetá, Laguna Negra, Ciudad de Piedra, Morro San Pedro, Peña de Otí y vestigios Muiscas.\n"
        "   - Si el usuario pregunta por otras regiones (ej. Medellín, Cartagena, Santa Marta, Cali, Eje Cafetero), "
        "     aclara con amabilidad que Monagua opera exclusivamente en Mongua, Boyacá y recomiéndale los destinos de la región.\n"
        "4. CATÁLOGO REAL DE TOURS:\n"
        f"{tours_context}\n"
        "   - NUNCA inventes nombres de tours que no figuren en esa lista.\n"
        "5. TARIFAS Y TEMPORADAS:\n"
        "   - Contamos con Temporada Alta (festivos, puentes, vacaciones) y Temporada Baja con tarifas preferenciales.\n"
        "   - Los precios varían según temporada, duración y personas. NUNCA inventes valores numéricos al azar; "
        "     invita a cotizar en tiempo real en /tours/.\n"
        "6. PROMOCIONES ACTIVAS:\n"
        f"{promos_context}\n"
        "   - No prometas descuentos ni cupones ficticios.\n"
        "7. MÉTODOS DE PAGO Y FACTURACIÓN:\n"
        "   - Aceptamos transferencias bancarias (Bancolombia, Davivienda, etc.) y billeteras digitales (Nequi, Daviplata).\n"
        "   - El usuario realiza el pago y luego debe subir su comprobante en /pagos/enviar-comprobante/.\n"
        "   - Ninguna reserva se confirma sin pago 100% verificado y aprobado por administración.\n"
        "   - Tras aprobación, el turista puede descargar su Factura Legal en PDF con código QR desde /reservas/mis-reservas/.\n"
        "8. POLÍTICAS DE CANCELACIÓN, NOTAS DE CRÉDITO Y REEMBOLSOS:\n"
        "   - Modificación de personas o cupos: se puede reducir cupos generando una Nota de Crédito contable.\n"
        "   - Cancelaciones: el turista puede solicitarla desde 'Mis Reservas'. Con >48 horas aplican mejores condiciones.\n"
        "   - La administración tramita el reembolso vía transferencia bancaria y adjunta el comprobante bancario visible en 'Mis Reembolsos'.\n"
        "9. CONTACTO OFICIAL ÚNICO:\n"
        "   - Teléfono/WhatsApp oficial: +57 322 3465191. Correo institucional: contacto@monagua.com.\n"
        "10. RADICACIÓN DE PQRS:\n"
        "   - Cualquier queja, reclamo, petición o sugerencia debe ser remitida formalmente a /pqrs/.\n"
        "11. RUTAS OFICIALES PERMITIDAS:\n"
        "   - Únicamente cita estas rutas: /tours/, /pqrs/, /mis_pqrs/, /pagos/enviar-comprobante/, /reservas/mis-reservas/, "
        "     /promociones/, /blog/, /nosotros/, /terminos-y-condiciones/, /calificaciones/mis-calificaciones/.\n"
        "12. TONO Y FORMATO:\n"
        "   - Sé cordial, protector de la naturaleza, conciso (máximo 2 párrafos) y 100% verídico."
        + usuario_info
    )

    modelos = ["gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.5-flash"]
    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": mensaje}]}],
        "generationConfig": {
            "temperature": 0.1,  # Temperatura baja para máxima fidelidad
            "topP": 0.8,
            "maxOutputTokens": 380,
        },
    }

    for modelo in modelos:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2.5) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            texto_ia = sanitizar_respuesta_ia(parts[0]["text"].strip())
                            resultado = {
                                "response": texto_ia,
                                "options": [
                                    "¿Qué tours ofrecen?",
                                    "Regulaciones ambientales",
                                    "Radicar PQRS",
                                ],
                            }
                            # Detección inteligente de botones de navegación
                            texto_lower = texto_ia.lower()
                            if (
                                "pqrs" in texto_lower
                                or "queja" in texto_lower
                                or "reclamo" in texto_lower
                            ):
                                resultado["link_url"] = "/pqrs/"
                                resultado["link_text"] = "Radicar PQRS oficial"
                                resultado["action"] = "pqrs"
                            elif "comprobante" in texto_lower or "pago" in texto_lower:
                                resultado["link_url"] = "/pagos/enviar-comprobante/"
                                resultado["link_text"] = "Enviar comprobante de pago"
                            elif (
                                "tour" in texto_lower
                                or "paquete" in texto_lower
                                or "destino" in texto_lower
                            ):
                                resultado["link_url"] = "/tours/"
                                resultado["link_text"] = "Ver catálogo de tours"
                            elif (
                                "oferta" in texto_lower
                                or "promocion" in texto_lower
                                or "descuento" in texto_lower
                            ):
                                resultado["link_url"] = "/promociones/"
                                resultado["link_text"] = "Ver promociones vigentes"
                            elif (
                                "regulacion" in texto_lower
                                or "paramo" in texto_lower
                                or "norma" in texto_lower
                            ):
                                resultado["link_url"] = "/terminos-y-condiciones/"
                                resultado["link_text"] = "Ver normas y regulaciones"
                            elif (
                                "reserva" in texto_lower
                                or "cancelar" in texto_lower
                                or "factura" in texto_lower
                            ):
                                resultado["link_url"] = "/reservas/mis-reservas/"
                                resultado["link_text"] = "Ir a Mis Reservas"
                            elif "blog" in texto_lower or "articulo" in texto_lower:
                                resultado["link_url"] = "/blog/"
                                resultado["link_text"] = "Ver Blog de Monagua"

                            return resultado
        except (urllib.error.URLError, TimeoutError, OSError) as net_err:
            # Corte de internet, fallo DNS o timeout de red: activar disyuntor y conmutar a motor local sin demoras
            _LAST_INTERNET_ERROR_TIME = time.time()
            logger.info(
                "Conexión externa no disponible (%s). Activando motor local resiliente.",
                net_err,
            )
            break
        except Exception as ex:
            logger.debug("Error evaluando modelo %s: %s", modelo, ex)
            continue

    return None


# ══════════════════════════════════════════════════════════════════════════════
# BASE DE CONOCIMIENTO LOCAL ROBUSTA (30+ INTENCIONES COMPLETAS Y REGULADAS)
# ══════════════════════════════════════════════════════════════════════════════


def construir_faqs(user=None):
    """Genera la lista de intenciones incorporando datos dinámicos de la BD y regulaciones."""
    tours_dinamicos = obtener_tours_destacados()
    promos_dinamicas = obtener_promociones_activas()

    nombre_usuario = (
        (user.first_name or user.username) if (user and user.is_authenticated) else ""
    )
    saludo_personalizado = f"¡Hola{', ' + nombre_usuario if nombre_usuario else ''}! Te doy la bienvenida a Monagua Turismo."

    faqs = [
        # 1. Saludo
        {
            "id": "saludo",
            "keywords": [
                "hola",
                "buen dia",
                "buenos dias",
                "buenas tardes",
                "buenas noches",
                "hey",
                "saludos",
                "que tal",
                "como estas",
                "que hubo",
                "buenas",
                "hi",
                "hello",
                "buena tarde",
                "buen dia condy",
                "hola condy",
            ],
            "answer": (
                f"{saludo_personalizado} Soy Cóndy, tu cóndor guardián y asistente virtual "
                f"en Mongua, Boyacá. ¿En qué te puedo orientar hoy? Puedes consultarme sobre "
                f"nuestros tours ecológicos, cómo reservar, métodos de pago, regulaciones del páramo o radicar una PQRS."
            ),
            "options": [
                "¿Qué tours ofrecen?",
                "¿Cómo funciona la página?",
                "Regulaciones ambientales",
                "Radicar PQRS",
            ],
        },
        # 2. Identidad
        {
            "id": "identidad",
            "keywords": [
                "quien eres",
                "que eres",
                "como te llamas",
                "tu nombre",
                "eres un bot",
                "eres una ia",
                "eres un robot",
                "que es condy",
                "quien es condy",
                "presentate",
                "que haces",
                "cual es tu funcion",
            ],
            "answer": (
                "Soy Cóndy, la mascota oficial y asistente virtual de Monagua Turismo. "
                "Represento al cóndor andino que vigila las cumbres del Páramo de Ocetá. "
                "Mi misión es guiarte por nuestra plataforma, explicarte las normas de preservación ambiental, "
                "resolver tus dudas sobre reservas y pagos, y ayudarte en tus solicitudes."
            ),
            "options": [
                "¿Cómo funciona la página?",
                "¿Dónde están ubicados?",
                "Regulaciones del páramo",
            ],
        },
        # 3. Despedida y agradecimiento
        {
            "id": "despedida_agradecimiento",
            "keywords": [
                "gracias",
                "muchas gracias",
                "mil gracias",
                "te agradezco",
                "chao",
                "adios",
                "hasta luego",
                "nos vemos",
                "que estes bien",
                "excelente",
                "perfecto",
                "muchas bendiciones",
                "muy amable",
                "listo gracias",
                "vale gracias",
            ],
            "answer": (
                "¡Ha sido un verdadero placer colaborarte! En Monagua amamos proteger la magia de Boyacá y su naturaleza. "
                "Si requieres algo más para tu aventura, comprobante o reserva, aquí estaré con las alas abiertas. "
                "¡Que tengas una gran experiencia!"
            ),
            "options": ["Ver destinos", "¿Cómo reservar?", "Regulaciones ambientales"],
        },
        # 4. Ubicación
        {
            "id": "ubicacion",
            "keywords": [
                "ubicacion",
                "direccion",
                "donde estan",
                "donde quedan",
                "donde se encuentran",
                "donde esta ubicado",
                "donde queda mongua",
                "en que ciudad estan",
                "en que departamento",
                "en que municipio",
                "donde estan ubicados",
                "sede",
                "oficina",
                "punto de encuentro",
            ],
            "answer": (
                "Monagua Turismo tiene su centro de operaciones en el municipio de **Mongua, Boyacá, Colombia** "
                "(provincia de Sugamuxi, a solo 35-40 minutos de Sogamoso). Los puntos de salida e inducción para las expediciones "
                "se coordinan en el Parque Principal de Mongua frente al templo parroquial."
            ),
            "link_url": "/nosotros/",
            "link_text": "Conoce más sobre Monagua",
            "options": [
                "¿Cómo llegar desde Bogotá?",
                "¿Qué tours ofrecen?",
                "Regulaciones ambientales",
            ],
        },
        # 5. Cómo llegar y Transporte
        {
            "id": "transporte",
            "keywords": [
                "como llegar a mongua",
                "como viajar",
                "transporte",
                "como llego",
                "llegar desde bogota",
                "llegar desde tunja",
                "llegar desde sogamoso",
                "bus",
                "flota",
                "terminal",
                "carro",
                "viajar a mongua",
                "carretera",
                "pasajes",
                "ruta de viaje",
            ],
            "answer": (
                "Para llegar a Mongua desde Bogotá o Tunja:\n"
                "1. Tomas un autobús intermunicipal hasta la **Terminal de Sogamoso** (aprox. 3 horas y media desde Bogotá).\n"
                "2. Desde la terminal de Sogamoso salen vehículos y microbuses frecuentes hacia **Mongua** por vía pavimentada (35 a 45 minutos de viaje)."
            ),
            "options": [
                "¿Dónde están ubicados?",
                "¿Cuáles son los atractivos?",
                "¿Cómo reservar?",
            ],
        },
        # 6. Atractivos Turísticos de Mongua
        {
            "id": "atractivos",
            "keywords": [
                "paramo de oceta",
                "oceta",
                "laguna negra",
                "morro de san pedro",
                "peña de oti",
                "ciudad de piedra",
                "cascada desaguadero",
                "frailejones",
                "muisca",
                "arte rupestre",
                "pictogramas",
                "atractivos",
                "lugares para visitar",
                "sitios turisticos",
                "que conocer",
                "que ver en mongua",
                "monumentos",
            ],
            "answer": (
                "Mongua cuenta con escenarios naturales y arqueológicos únicos en los Andes colombianos:\n"
                "• **Páramo de Ocetá**: Considerado uno de los páramos más hermosos del mundo, con su mística Ciudad de Piedra y valles de frailejones.\n"
                "• **Laguna Negra**: Espejo de agua de origen glaciar rodeado de leyendas ancestrales.\n"
                "• **Morro de San Pedro y Peña de Otí**: Miradores panorámicos de alta montaña con vista a valles interandinos.\n"
                "• **Patrimonio Muisca**: Petroglifos, pictogramas y senderos sagrados de gran valor arqueológico."
            ),
            "link_url": "/tours/",
            "link_text": "Explorar catálogo de destinos",
            "options": [
                "Regulaciones del páramo",
                "Ver tours disponibles",
                "¿Qué ropa llevar?",
            ],
        },
        # 7. REGULACIONES AMBIENTALES Y LEY DE PÁRAMOS (NUEVA INTENCIÓN CLAVE)
        {
            "id": "regulaciones_ambientales",
            "keywords": [
                "regulaciones",
                "regulacion",
                "normas",
                "normativa",
                "reglas",
                "ley 1930",
                "ley de paramos",
                "cuidar el paramo",
                "prohibido",
                "que esta prohibido",
                "prohibiciones",
                "sanciones",
                "multas",
                "frailejon",
                "frailejones",
                "basura",
                "residuos",
                "fogata",
                "fogatas",
                "fumar",
                "cigarrillo",
                "drones",
                "dron",
                "no deje rastro",
                "medio ambiente",
                "conservacion",
                "proteccion ambiental",
                "arrancar plantas",
                "fosiles",
            ],
            "answer": (
                "🌲 **Regulaciones Ambientales Oficiales (Ley 1930 de 2018 - Protección de Páramos):**\n\n"
                "1. **Prohibición sobre Frailejones y Flora**: Está terminantemente prohibido pisar, cortar, arrancar o llevarse frailejones (*Espeletia*), musgos o líquenes. Crecen apenas 1 cm al año y destruirlos es delito ambiental.\n"
                "2. **Cero Basuras ('No Deje Rastro')**: Todo residuo, envoltura o plástico debe retornar en tu mochila. Prohibido plásticos de un solo uso.\n"
                "3. **Prohibición Total de Fuego**: Cero fogatas, hornillas o cigarrillos en zonas de páramo y bosque.\n"
                "4. **Patrimonio Arqueológico Muisca**: Prohibido tocar, pintar o rayar petroglifos y arte rupestre.\n"
                "5. **Drones**: Su vuelo en zonas protegidas requiere permiso ambiental previo de Corpoboyacá.\n"
                "6. **Acompañamiento Obligatorio**: No se permite el ingreso a senderos de páramo sin guía local certificado."
            ),
            "link_url": "/terminos-y-condiciones/",
            "link_text": "Ver términos y regulaciones completas",
            "options": [
                "¿Se pueden llevar mascotas?",
                "¿Qué ropa llevar?",
                "¿Por qué se exige guía?",
            ],
        },
        # 8. CÓMO FUNCIONA LA PÁGINA (NUEVA INTENCIÓN CLAVE)
        {
            "id": "como_funciona_plataforma",
            "keywords": [
                "como funciona la pagina",
                "como funciona la web",
                "como funciona monagua",
                "como funciona la plataforma",
                "guia de la pagina",
                "pasos para usar la pagina",
                "que puedo hacer en la pagina",
                "manual de uso",
                "instructivo",
                "de que trata la pagina",
                "que es monagua web",
                "como comprar",
                "proceso de compra",
            ],
            "answer": (
                "💻 **¿Cómo funciona Monagua Turismo? Paso a paso:**\n\n"
                "1. **Explora**: Ingresa a 'Destinos' (/tours/) y consulta las actividades, itinerarios y dificultad.\n"
                "2. **Regístrate**: Crea tu cuenta de forma segura con verificación por correo (código OTP).\n"
                "3. **Reserva**: Selecciona la fecha deseada, el número de personas (adultos/niños) y agrega al carrito.\n"
                "4. **Paga y Comprueba**: Realiza tu transferencia (Nequi, Daviplata o Bancolombia) y sube la captura en 'Enviar Comprobante'.\n"
                "5. **Confirmación y Factura**: Una vez el administrador valida el pago, tu reserva queda confirmada y puedes descargar tu factura con código QR.\n"
                "6. **Asiste a tu Tour**: Te asignamos un guía certificado y póliza médica para tu expedición."
            ),
            "link_url": "/tours/",
            "link_text": "Comenzar explorando tours",
            "options": [
                "¿Qué roles hay en la página?",
                "¿Cómo registrarse?",
                "¿Qué métodos de pago aceptan?",
            ],
        },
        # 9. ROLES DE USUARIO (NUEVA INTENCIÓN CLAVE)
        {
            "id": "roles_usuario",
            "keywords": [
                "roles",
                "tipos de usuario",
                "que roles hay",
                "rol de usuario",
                "turista",
                "cliente",
                "guia turistico",
                "administrador",
                "admin",
                "quien administra",
                "permisos",
                "diferencia de roles",
            ],
            "answer": (
                "👥 **En Monagua Turismo existen tres roles principales:**\n\n"
                "• **Turista / Cliente**: Puede explorar el catálogo, reservar paquetes, subir comprobantes, reducir cupos, gestionar cancelaciones, solicitar reembolsos, descargar facturas, calificar tours y radicar PQRS.\n"
                "• **Guía Turístico**: Guía local acreditado (SENA/RNT) con formación en rescate, primeros auxilios e historia Muisca. Es asignado a los grupos para liderar las rutas.\n"
                "• **Administrador / Staff**: Revisa y aprueba comprobantes de pago, administra el catálogo y tarifas, asigna guías, gestiona cancelaciones y autoriza transferencias bancarias de reembolsos."
            ),
            "link_url": "/nosotros/",
            "link_text": "Conoce a nuestro equipo",
            "options": [
                "¿Cómo registrarse?",
                "¿Cómo ser guía?",
                "¿Cómo funciona la página?",
            ],
        },
        # 10. Catálogo de Tours y Servicios
        {
            "id": "servicios_tours",
            "keywords": [
                "servicios",
                "servicios ofrecen",
                "que hacen",
                "actividad",
                "actividades",
                "tour",
                "tours",
                "paquete",
                "paquetes",
                "planes",
                "plan",
                "experiencias",
                "excursiones",
                "caminatas",
                "senderismo",
                "trekking",
                "ecoturismo",
                "destinos",
                "que tours tienen",
                "tours disponibles",
                "paquetes disponibles",
                "catalogo de tours",
            ],
            "answer": (
                "En Monagua ofrecemos paquetes ecoturísticos de alta montaña y cultura con póliza médica y guía certificado. "
                "Nuestros tours disponibles actualmente en el sistema son:\n\n"
                f"{tours_dinamicos}\n\n"
                "Puedes consultar el itinerario completo, desnivel y dificultad de cada uno en la sección de Destinos."
            ),
            "link_url": "/tours/",
            "link_text": "Ver catálogo de tours",
            "options": [
                "¿Cuánto cuestan los paquetes?",
                "¿Cómo reservar?",
                "Regulaciones ambientales",
            ],
        },
        # 11. Precios y Tarifas
        {
            "id": "precios",
            "keywords": [
                "precio",
                "precios",
                "costo",
                "costos",
                "tarifas",
                "tarifa",
                "cuanto vale",
                "cuanto cuesta",
                "que cobran",
                "cotizar",
                "valores",
                "valor",
                "cuanto cobran",
            ],
            "answer": (
                "Nuestras tarifas dependen del tour seleccionado, la duración (días/noches), la temporada "
                "(baja o alta) y la cantidad de viajeros (adultos y menores). Cada paquete incluye "
                "acompañamiento de guía profesional y seguro de viaje. Puedes cotizar en tiempo real seleccionando tu fecha en 'Destinos'."
            ),
            "link_url": "/tours/",
            "link_text": "Consultar tarifas en Destinos",
            "options": [
                "Temporada alta vs baja",
                "¿Cómo reservar un tour?",
                "¿Qué métodos de pago aceptan?",
            ],
        },
        # 12. TEMPORADAS Y TARIFAS (NUEVA INTENCIÓN)
        {
            "id": "temporadas_tarifas",
            "keywords": [
                "temporada",
                "temporadas",
                "temporada alta",
                "temporada baja",
                "tarifas por temporada",
                "cuando es temporada alta",
                "cuando es temporada baja",
                "diferencia de temporada",
                "fechas de temporada",
            ],
            "answer": (
                "📅 **Manejo de Temporadas en Monagua:**\n\n"
                "• **Temporada Alta**: Corresponde a fines de semana con puente festivo, Semana Santa, vacaciones de mitad de año (junio/julio) y receso de fin de año (diciembre/enero).\n"
                "• **Temporada Baja**: Resto del año, ideal para disfrutar de senderos más tranquilos con tarifas preferenciales y descuentos especiales.\n\n"
                "El sistema aplica la tarifa automáticamente según la fecha que escojas en tu reserva."
            ),
            "link_url": "/tours/",
            "link_text": "Ver paquetes y fechas",
            "options": [
                "Ver promociones vigentes",
                "¿Cómo reservar?",
                "¿Qué métodos de pago aceptan?",
            ],
        },
        # 13. Promociones
        {
            "id": "promociones",
            "keywords": [
                "promocion",
                "promociones",
                "descuento",
                "descuentos",
                "oferta",
                "ofertas",
                "cupon",
                "cupones",
                "codigo promocional",
                "rebajas",
            ],
            "answer": (
                "¡Tenemos ofertas y descuentos especiales disponibles para ti! Estas son algunas promociones activas:\n\n"
                f"{promos_dinamicas}\n\n"
                "Aprovecha estos beneficios ingresando a nuestra sección de Ofertas y aplicando el cupón en tu reserva."
            ),
            "link_url": "/promociones/",
            "link_text": "Ver promociones vigentes",
            "options": [
                "Ver catálogo de tours",
                "¿Cómo reservar?",
                "¿Cómo aplicar un cupón?",
            ],
        },
        # 14. Cómo Reservar
        {
            "id": "reserva",
            "keywords": [
                "reserva", "reservas", "reservar", "como reservar", "como puedo reservar",
                "quiero reservar", "agendar", "como agendar", "apartar", "separar",
                "cupo", "cupos", "booking", "programar", "hacer reserva", "hacer una reserva",
                "quiero hacer una reserva", "reserva para", "reservar para", "pasos para reservar",
                "como viajar", "quiero ir"
            ],
            "answer": (
                "Reservar tu expedición es muy fácil:\n"
                "1. Ingresa a **Destinos** (/tours/) y selecciona el paquete deseado.\n"
                "2. Escoge la fecha de viaje y la cantidad de adultos y menores (mínimo 1 adulto).\n"
                "3. Añade al carrito y confirma los datos de la reserva.\n"
                "4. Realiza el pago y carga el comprobante en **Enviar Comprobante** para confirmar tus cupos."
            ),
            "link_url": "/tours/",
            "link_text": "Ir a reservar un tour",
            "options": [
                "¿Cómo realizar el pago?",
                "Políticas de cancelación",
                "Mis reservas",
            ],
        },
        # 15. Consultar Mis Reservas (Dinámica)
        {
            "id": "mis_reservas_consulta",
            "keywords": [
                "mis reservas",
                "mi reserva",
                "como va mi reserva",
                "estado de mi reserva",
                "consultar mi reserva",
                "ver mis reservas",
                "historial de reservas",
                "mis viajes",
            ],
            "answer": "",  # Se autogenera dinámicamente según el usuario
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Ver mis reservas",
            "options": ["Enviar comprobante", "Descargar factura", "Radicar PQRS"],
        },
        # 16. MODIFICACIÓN DE RESERVAS Y REDUCCIÓN DE PERSONAS (NUEVA INTENCIÓN)
        {
            "id": "modificar_reserva_cupos",
            "keywords": [
                "modificar reserva",
                "cambiar personas",
                "reducir personas",
                "menos personas",
                "agregar personas",
                "cambiar fecha",
                "reprogramar",
                "modificacion de reserva",
                "bajar cupos",
                "modificar cupos",
                "quitar personas",
            ],
            "answer": (
                "✏️ **Modificación de Reservas y Reducción de Personas:**\n\n"
                "Si ya tienes una reserva pagada pero necesitas reducir el número de personas, puedes hacerlo desde **Mis Reservas**:\n"
                "• El sistema recalcula el valor correspondiente a los cupos liberados.\n"
                "• Si la modificación se realiza dentro de los tiempos estipulados por política, se genera automáticamente una **Nota de Crédito**.\n"
                "• Ese monto se acredita como **Saldo a Favor** en tu cuenta para adquirir otros tours o solicitar reembolso bancario."
            ),
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Gestionar mis reservas",
            "options": [
                "¿Qué es una nota de crédito?",
                "Políticas de cancelación",
                "Consultar saldo a favor",
            ],
        },
        # 17. Pagos y Métodos de Pago
        {
            "id": "pago",
            "keywords": [
                "pago",
                "pagos",
                "pagar",
                "como pagar",
                "como puedo pagar",
                "donde pagar",
                "puedo pagar",
                "quiero pagar",
                "metodo de pago",
                "metodos de pago",
                "formas de pago",
                "transferencia",
                "transferir",
                "nequi",
                "daviplata",
                "bancolombia",
                "banco",
                "comprobante",
                "subir comprobante",
                "enviar comprobante",
                "consignacion",
                "consignar",
                "pse",
                "tarjeta",
                "donde pagar",
                "a que cuenta pagar",
                "cuenta bancaria",
            ],
            "answer": (
                "💳 **Métodos de Pago Oficiales en Monagua:**\n\n"
                "Aceptamos transferencias bancarias (Bancolombia, Davivienda, etc.) y billeteras digitales (Nequi y Daviplata).\n\n"
                "**Paso a paso para reportar tu pago:**\n"
                "1. Realiza la transferencia por el monto exacto de tu reserva.\n"
                "2. Dirígete a **Enviar Comprobante** (/pagos/enviar-comprobante/).\n"
                "3. Selecciona tu reserva, ingresa el número de referencia bancario y adjunta la imagen del comprobante.\n"
                "4. La administración revisará y confirmará tu reserva en pocas horas."
            ),
            "link_url": "/pagos/enviar-comprobante/",
            "link_text": "Enviar comprobante de pago",
            "options": [
                "Mis reservas",
                "¿Cómo descargar mi factura?",
                "Políticas de cancelación",
            ],
        },
        # 18. FACTURAS ELECTRÓNICAS Y COMPROBANTES CON QR (NUEVA INTENCIÓN)
        {
            "id": "facturas",
            "keywords": [
                "factura",
                "facturas",
                "recibo",
                "descargar factura",
                "comprobante de reserva",
                "qr",
                "codigo qr",
                "pdf reserva",
                "factura legal",
                "mis facturas",
            ],
            "answer": (
                "📄 **Facturas y Comprobantes Oficiales:**\n\n"
                "Tan pronto tu pago es aprobado por la administración, el sistema genera de forma automática:\n"
                "• Tu **Factura Legal** con detalle de pasajeros, fechas e impuestos.\n"
                "• Tu **Comprobante Digital** en PDF con un **Código QR** único de verificación para control en campo por el guía.\n\n"
                "Puedes consultar y descargar tus facturas en cualquier momento desde 'Mis Facturas' o 'Mis Reservas'."
            ),
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Ver mis facturas y reservas",
            "options": [
                "Mis reservas",
                "¿Cómo realizar el pago?",
                "Políticas de cancelación",
            ],
        },
        # 19. POLÍTICAS DE CANCELACIÓN Y REEMBOLSOS BANCARIOS (AMPLIADA)
        {
            "id": "cancelacion",
            "keywords": [
                "cancelar",
                "reembolso",
                "devolucion",
                "cancelacion",
                "retracto",
                "cancelado",
                "reembolsar",
                "anular reserva",
                "penalidad",
                "penalidades",
                "devolver plata",
                "me devuelven el dinero",
                "derecho de retracto",
            ],
            "answer": (
                "🔄 **Políticas de Cancelación y Reembolsos:**\n\n"
                "Puedes solicitar la cancelación de tu reserva en **Mis Reservas** especificando el motivo:\n"
                "• **Más de 48 horas de anticipación**: Aplica a las condiciones más favorables de reembolso o reprogramación con penalidad mínima.\n"
                "• **Menos de 24 horas o inasistencia**: Pueden aplicar penalidades por costos logísticos y pólizas ya emitidas.\n"
                "• **Desembolso del Reembolso**: Tras ser aprobada la cancelación, la administración realiza la transferencia bancaria (Nequi, Daviplata o banco) y adjunta el comprobante bancario oficial en tu módulo de 'Mis Reembolsos'."
            ),
            "link_url": "/reservas/mis-reservas/",
            "link_text": "Gestionar cancelación en Mis Reservas",
            "options": [
                "¿Qué es una nota de crédito?",
                "Consultar saldo a favor",
                "Radicar PQRS",
            ],
        },
        # 20. SALDO A FAVOR Y NOTAS DE CRÉDITO (NUEVA INTENCIÓN DINÁMICA)
        {
            "id": "saldo_a_favor_notas_credito",
            "keywords": [
                "saldo a favor",
                "nota de credito",
                "notas de credito",
                "mi saldo",
                "cuanto saldo tengo",
                "saldo disponible",
                "monedero",
                "credito en cuenta",
                "usar mi saldo",
                "saldo pendiente",
            ],
            "answer": "",  # Se autogenera dinámicamente según el usuario
            "link_url": "/perfil/",
            "link_text": "Ver mi perfil y saldo",
            "options": [
                "Ver mis reservas",
                "Ver catálogo de tours",
                "Políticas de cancelación",
            ],
        },
        # 21. REGISTRO, LOGIN Y VALIDACIÓN CON OTP (NUEVA INTENCIÓN)
        {
            "id": "cuenta_usuario_otp",
            "keywords": [
                "registro",
                "registrarse",
                "crear cuenta",
                "abrir cuenta",
                "iniciar sesion",
                "login",
                "ingresar",
                "mi cuenta",
                "perfil",
                "olvide contraseña",
                "cambiar contraseña",
                "codigo otp",
                "otp",
                "correo de verificacion",
                "clave",
                "contraseña",
                "recuperar cuenta",
            ],
            "answer": (
                "🔐 **Gestión de Cuenta y Seguridad OTP:**\n\n"
                "• **Registro Seguro**: Completa tus datos con validación instantánea (HTMX). Para proteger tu cuenta, te enviamos un código OTP (de un solo uso) a tu correo para verificar tu identidad.\n"
                "• **Inicio de Sesión**: Ingresa con tu nombre de usuario y contraseña desde el botón superior derecho.\n"
                "• **Recuperar Contraseña**: Si olvidaste tu clave, haz clic en '¿Olvidaste tu contraseña?' e ingresa tu correo registrado para recibir un enlace seguro y código de restablecimiento."
            ),
            "link_url": "/autenticacion/registro/",
            "link_text": "Ir a Registro de Usuario",
            "options": ["¿Cómo funciona la página?", "Ver destinos", "Radicar PQRS"],
        },
        # 22. Guías Turísticos
        {
            "id": "guias",
            "keywords": [
                "guia",
                "guias",
                "acompañante",
                "acompañantes",
                "orientador",
                "quien nos acompaña",
                "guia turistico",
                "guia certificado",
                "sena",
                "idioma guia",
                "guia bilingue",
                "por que se exige guia",
            ],
            "answer": (
                "Todos nuestros recorridos son dirigidos por guías comunitarios y profesionales "
                "certificados por el SENA o inscritos en el Registro Nacional de Turismo (RNT). "
                "Poseen amplia experiencia en alta montaña, primeros auxilios, conocimiento de flora y fauna nativa, "
                "y respeto absoluto por el patrimonio Muisca. Por regulación ambiental y seguridad, no está permitido ingresar al páramo sin guía."
            ),
            "options": [
                "¿Qué tours ofrecen?",
                "Recomendaciones de seguridad",
                "Regulaciones ambientales",
            ],
        },
        # 23. Clima y Ropa Recomendada
        {
            "id": "clima_ropa",
            "keywords": [
                "clima",
                "temperatura",
                "frio",
                "llueve",
                "lluvia",
                "que llevar",
                "ropa",
                "que ropa llevar",
                "que ropa",
                "como vestir",
                "calzado",
                "zapatos",
                "botas",
                "chaqueta",
                "impermeable",
                "bloqueador",
                "equipaje",
                "mochila",
                "guantes",
                "gorro",
            ],
            "answer": (
                "Mongua y el Páramo de Ocetá poseen clima frío de alta montaña (entre 7°C y 16°C). "
                "Te recomendamos vestir con el sistema de **tres capas**:\n"
                "1. Prenda térmica transpirable (primera capa pegada al cuerpo).\n"
                "2. Saco abrigado o forro polar (segunda capa térmica).\n"
                "3. Chaqueta impermeable o cortavientos (tercera capa de protección).\n"
                "Indispensable: botas de senderismo con suela antideslizante, guantes, gorro para el frío, protector solar ecológico y termo de agua reutilizable."
            ),
            "link_url": "/tours/",
            "link_text": "Ver recomendaciones en los tours",
            "options": [
                "¿Cuál es la dificultad de las caminatas?",
                "¿Dónde están ubicados?",
                "Regulaciones ambientales",
            ],
        },
        # 25. Dificultad Física y Altura (Soroche)
        {
            "id": "dificultad",
            "keywords": [
                "dificultad",
                "nivel de dificultad",
                "exigencia",
                "caminata dificil",
                "es dificil",
                "pueden ir niños",
                "adultos mayores",
                "tercera edad",
                "edad minima",
                "condicion fisica",
                "mal de altura",
                "soroche",
                "altura",
                "msnm",
            ],
            "answer": (
                "Contamos con recorridos para diferentes niveles de condición física:\n"
                "• **Baja**: Rutas culturales, arqueológicas y urbanas por el municipio de Mongua (aptas para toda la familia y niños).\n"
                "• **Media**: Senderos campestres hacia cascadas y miradores panorámicos.\n"
                "• **Alta**: Expedición integral al Páramo de Ocetá (alturas superiores a 3.600 msnm, requiere buen estado cardiovascular).\n\n"
                "Para evitar el mal de altura (soroche): hidrátate bien, consume dulces o panela, y camina al paso marcado por el guía."
            ),
            "link_url": "/tours/",
            "link_text": "Ver niveles en el catálogo",
            "options": ["¿Qué ropa llevar?", "¿Tienen guías?", "¿Cómo reservar?"],
        },
        # 26. Mascotas y Regulación
        {
            "id": "mascotas",
            "keywords": [
                "mascota",
                "mascotas",
                "perro",
                "perros",
                "gato",
                "gatos",
                "animal",
                "animales",
                "pet",
                "petfriendly",
                "puedo llevar mi perro",
            ],
            "answer": (
                "🐾 **Regulación sobre Mascotas:**\n\n"
                "Las mascotas son bienvenidas en las rutas culturales urbanas y senderos campestres bajos de Mongua. "
                "Sin embargo, por regulación ambiental y protección del ecosistema estratégico del **Páramo de Ocetá**, "
                "el ingreso de mascotas está **prohibido en la zona de páramo y reserva estricta** para salvaguardar a los frailejones "
                "y evitar la alteración o transmisión de patógenos a la fauna silvestre."
            ),
            "options": [
                "Regulaciones ambientales",
                "¿Qué tours ofrecen?",
                "¿Cómo reservar?",
            ],
        },
        # 27. Gastronomía
        {
            "id": "comida",
            "keywords": [
                "comida",
                "comidas",
                "restaurante",
                "almuerzo",
                "desayuno",
                "cena",
                "alimentacion",
                "bebida",
                "bebidas",
                "snacks",
                "refrigerio",
                "alimentos",
                "que comer",
                "donde comer",
                "gastronomia",
                "platos tipicos",
                "arepas",
            ],
            "answer": (
                "En Mongua podrás degustar la más exquisita gastronomía boyacense: las tradicionales arepas monguanas "
                "de maíz pelado horneadas en lajas de barro, caldos campesinos, trucha arcoíris fresca y agua de panela con queso de la región. "
                "Para las caminatas recomendamos portar snacks energéticos: frutos secos, bocadillos y chocolate."
            ),
            "options": [
                "Ver tours disponibles",
                "¿Cuáles son sus horarios?",
                "¿Dónde están ubicados?",
            ],
        },
        # 28. Horarios
        {
            "id": "horarios",
            "keywords": [
                "horario",
                "horarios",
                "abren",
                "cierran",
                "apertura",
                "cierre",
                "atencion",
                "jornada",
                "a que hora",
                "que horas",
                "cuando abren",
                "dias de atencion",
            ],
            "answer": (
                "⏰ **Horarios de Atención:**\n\n"
                "• **Soporte y Atención Web**: Lunes a Domingo de 8:00 AM a 6:00 PM.\n"
                "• **Salidas de Expedición en Campo**: Se inician temprano en la mañana (entre 6:00 AM y 7:00 AM) "
                "desde el punto de encuentro en el Parque de Mongua para aprovechar el mejor clima y visibilidad del páramo."
            ),
            "options": [
                "¿Cómo contactar a un asesor?",
                "¿Qué servicios ofrecen?",
                "Radicar PQRS",
            ],
        },
        # 29. Contacto Oficial
        {
            "id": "contacto",
            "keywords": [
                "contacto",
                "telefono",
                "celular",
                "email",
                "correo",
                "llamar",
                "whatsapp",
                "comunicarse",
                "numero",
                "escribir",
                "contactar",
                "hablar con alguien",
                "asesor",
            ],
            "answer": (
                "📞 **Canales Oficiales de Monagua Turismo:**\n\n"
                "• **Línea Telefónica y WhatsApp**: +57 322 3465191\n"
                "• **Correo Electrónico**: contacto@monagua.com\n"
                "• **Ubicación**: Mongua, Boyacá, Colombia (Parque Principal)\n\n"
                "Para solicitudes formales, reclamaciones o garantías, te recomendamos utilizar nuestro módulo oficial de PQRS."
            ),
            "link_url": "/pqrs/",
            "link_text": "Ir a Radicar PQRS",
            "options": [
                "Radicar PQRS",
                "¿Dónde están ubicados?",
                "¿Cuáles son sus horarios?",
            ],
        },
        # 30. Radicación de PQRS
        {
            "id": "pqrs_radicar",
            "keywords": [
                "pqrs",
                "pqr",
                "peticion",
                "peticiones",
                "queja",
                "quejas",
                "reclamo",
                "reclamos",
                "sugerencia",
                "sugerencias",
                "ticket",
                "soporte",
                "radicar",
                "radicado",
                "inconformidad",
                "radicar pqrs",
                "poner queja",
                "hacer reclamo",
                "como poner una queja",
                "felicitacion",
            ],
            "answer": (
                "En Monagua contamos con un apartado oficial y transparente para la radicación de **PQRS** "
                "(Peticiones, Quejas, Reclamos y Sugerencias). Al diligenciar tu formulario recibirás un número "
                "de radicado oficial y seguimiento por parte del equipo administrativo."
            ),
            "action": "pqrs",
            "link_url": "/pqrs/",
            "link_text": "Radicar PQRS oficial",
            "options": [
                "Radicar PQRS",
                "Consultar mis PQRS",
                "¿Cuáles son sus horarios?",
            ],
        },
        # 31. Consulta de PQRS (Dinámica)
        {
            "id": "pqrs_consultar",
            "keywords": [
                "seguimiento pqrs",
                "consultar pqrs",
                "estado pqrs",
                "mi radicado",
                "numero radicado",
                "donde veo mi pqrs",
                "mis pqrs",
                "mis solicitudes",
                "ver mi queja",
                "respuesta pqrs",
                "consultar solicitudes",
            ],
            "answer": "",  # Se autogenera dinámicamente según el usuario
            "action": "pqrs",
            "link_url": "/mis_pqrs/",
            "link_text": "Consultar mis solicitudes",
            "options": ["Consultar mis PQRS", "Radicar PQRS", "Volver a Inicio"],
        },
        # 32. CALIFICACIONES Y RESEÑAS (NUEVA INTENCIÓN)
        {
            "id": "calificaciones_resenas",
            "keywords": [
                "calificaciones",
                "calificar",
                "resenas",
                "opiniones",
                "comentarios",
                "estrellas",
                "experiencias de otros",
                "calificar guia",
                "mis calificaciones",
                "dejar opinion",
                "calificar tour",
            ],
            "answer": (
                "⭐ **Calificaciones y Reseñas de Viajeros:**\n\n"
                "Al finalizar tu expedición, puedes calificar el paquete turístico y el servicio del guía "
                "asignado (con puntuación de 1 a 5 estrellas y un comentario detallado). "
                "Puedes gestionar tus reseñas en **Mis Calificaciones**."
            ),
            "link_url": "/calificaciones/mis-calificaciones/",
            "link_text": "Ver mis calificaciones",
            "options": ["Mis reservas", "Ver catálogo de tours", "Radicar PQRS"],
        },
        # 33. BLOG Y CONTENIDO CULTURAL (NUEVA INTENCIÓN)
        {
            "id": "blog_cultura",
            "keywords": [
                "blog",
                "noticias",
                "articulos",
                "historias",
                "leyendas",
                "cultura muisca",
                "biodiversidad",
                "fauna y flora",
                "lecturas",
                "consejos de viaje",
                "articulos de viaje",
            ],
            "answer": (
                "📖 **Blog Ecoturístico de Monagua:**\n\n"
                "Descubre artículos fascinantes sobre las leyendas de los caciques Muiscas, la importancia vital "
                "del agua en el Páramo de Ocetá, guías de fotografía de alta montaña y testimonios de caminantes. "
                "Explora nuestras publicaciones en la sección **Blog**."
            ),
            "link_url": "/blog/",
            "link_text": "Leer el Blog de Monagua",
            "options": [
                "Ver destinos",
                "Regulaciones ambientales",
                "¿Dónde están ubicados?",
            ],
        },
        # 34. Artesanías
        {
            "id": "artesanias",
            "keywords": [
                "artesanias",
                "recuerdos",
                "souvenirs",
                "lana",
                "tejidos",
                "ruanas",
                "fique",
                "artesanos",
                "compras en mongua",
            ],
            "answer": (
                "Mongua es reconocida por sus artesanos tradicionales expertos en el hilado de lana virgen, "
                "confección de ruanas boyacenses, cobijas campesinas y canastos en fique. En el pueblo "
                "encontrarás talleres locales donde podrás adquirir auténticas artesanías campesinas."
            ),
            "options": [
                "¿Dónde están ubicados?",
                "Ver tours disponibles",
                "¿Cuáles son sus horarios?",
            ],
        },
    ]

    return faqs


# ══════════════════════════════════════════════════════════════════════════════
# CONTROL ANTI-ALUCINACIÓN Y DETECCIÓN FUERA DE ÁMBITO ("FUERA DE LAS LLAVES")
# ══════════════════════════════════════════════════════════════════════════════

def detectar_intenciones_especiales_o_fuera_de_ambito(mensaje_norm):
    """
    Detecta consultas fuera de ámbito o 'fuera de las llaves' para evitar alucinaciones:
    - Otras ciudades turísticas (Cartagena, Medellín, etc.) -> Aclara ámbito exclusivo de Mongua.
    - Medios de pago no autorizados (PayPal, cripto, etc.) -> Aclara pasarela oficial.
    - Temas desconectados (código de programación, tareas, recetas) -> Recuerda identidad ecoturística.
    """
    if not mensaje_norm:
        return None

    # 1. Ciudades fuera de Mongua / Boyacá (Evitar alucinación geográfica)
    ciudades_externas = [
        "cartagena", "medellin", "santa marta", "san andres", "cali", "barranquilla",
        "eje cafetero", "leticia", "tayrona", "cancun", "guatape", "salento", "villavicencio",
        "bogota tour", "tours en bogota", "tours en cartagena", "tours en medellin",
        "marte", "luna", "jupiter", "saturno"
    ]
    for c in ciudades_externas:
        if c in mensaje_norm or re.search(r'\b' + re.escape(c) + r'\b', mensaje_norm):
            return {
                "response": (
                    "📍 **Ubicación Exclusiva de Monagua Turismo:**\n\n"
                    "Monagua Turismo opera **única y exclusivamente en el municipio de Mongua, Boyacá** "
                    "(Páramo de Ocetá, Laguna Negra, Ciudad de Piedra, Morro San Pedro, Peña de Otí y vestigios Muiscas).\n\n"
                    f"No disponemos de servicios turísticos en '{c.capitalize()}' ni en otros destinos externos. "
                    "Te invitamos a conocer las cumbres boyacenses y páramos sagrados con nuestros guías certificados."
                ),
                "link_url": "/tours/",
                "link_text": "Ver destinos en Mongua, Boyacá",
                "options": ["¿Qué tours ofrecen en Mongua?", "¿Dónde están ubicados?", "Regulaciones ambientales"]
            }

    # 2. Medios de pago no soportados o inventados (Anti-alucinación de pagos)
    pagos_invalidos = [
        "paypal", "tarjeta de credito directa", "tarjeta directa", "bitcoin", "cripto",
        "criptomonedas", "usdt", "western union", "baloto", "efecty", "contraentrega", "tarjeta de credito"
    ]
    for p in pagos_invalidos:
        if re.search(r'\b' + re.escape(p) + r'\b', mensaje_norm):
            return {
                "response": (
                    "💳 **Aclaración sobre Medios de Pago Oficiales:**\n\n"
                    f"En Monagua Turismo **no procesamos pagos mediante {p.title()}** ni pasarelas externas no autorizadas.\n\n"
                    "Nuestros métodos oficiales aprobados son:\n"
                    "• **Transferencias Bancarias**: Bancolombia, Davivienda y cuentas nacionales.\n"
                    "• **Billeteras Digitales**: Nequi y Daviplata.\n\n"
                    "Tras realizar tu abono, carga el soporte en **Enviar Comprobante** para validación del equipo administrativo."
                ),
                "link_url": "/pagos/enviar-comprobante/",
                "link_text": "Subir comprobante de pago",
                "options": ["¿Cómo pagar?", "¿Cómo funciona la página?", "¿Qué tours ofrecen?"]
            }

    # 3. Temas off-topic / no turísticos (Código, tareas, recetas de cocina, etc.)
    patrones_offtopic = [
        r'\b(python|javascript|java|c\+\+|php|sql|html|css)\b',
        r'\b(codigo|programar|programacion|script|desarrollar una app)\b',
        r'\b(hazme la tarea|hacer mi tarea|resuelve esta ecuacion|ejercicio de matematicas|hacer un ensayo)\b',
        r'\b(receta de|como cocinar|preparar pizza|ingredientes para)\b',
        r'\b(cuentame un chiste|escribe un poema|inventa un cuento|cantar una cancion)\b',
    ]
    for patron in patrones_offtopic:
        if re.search(patron, mensaje_norm):
            return {
                "response": (
                    "🦅 **Soy Cóndy, Asistente Ecoturístico de Monagua Turismo:**\n\n"
                    "Mi función está 100% orientada a orientarte sobre las maravillas naturales de Mongua, Boyacá, "
                    "nuestro Páramo de Ocetá, reservas de tours, comprobantes de pago y normatividad ambiental.\n\n"
                    "No tengo funciones para resolver tareas generales o programación. ¿Deseas conocer nuestros paquetes ecológicos?"
                ),
                "link_url": "/tours/",
                "link_text": "Explorar destinos ecoturísticos",
                "options": ["¿Qué tours ofrecen?", "Regulaciones ambientales", "¿Cómo funciona la página?"]
            }

    return None


# ══════════════════════════════════════════════════════════════════════════════
# MOTOR PRINCIPAL DE PROCESAMIENTO NLP
# ══════════════════════════════════════════════════════════════════════════════


def procesar_mensaje(mensaje, request):
    """
    Procesador avanzado de Cóndy:
    1. Si existe GEMINI_API_KEY, consulta Gemini AI con anclaje a datos reales de Monagua y regulaciones.
    2. Si no hay clave o falla la red, ejecuta el motor semántico local con conexión a base de datos.
    3. Personaliza la información si el usuario está autenticado (reservas, saldo a favor, PQRS, nombre).
    4. Garantiza enrutamiento estricto a las rutas oficiales de la plataforma (/pqrs/, /tours/, etc.).
    """
    if not request.session.session_key:
        request.session.save()

    if "condy_fallos" not in request.session:
        request.session["condy_fallos"] = 0

    if not mensaje or not mensaje.strip():
        return {
            "response": "¡Hola! ¿En qué puedo orientarte hoy? Puedes consultarme sobre tours, cómo funciona la página, regulaciones ambientales o radicar una PQRS.",
            "options": [
                "¿Qué tours ofrecen?",
                "¿Cómo funciona la página?",
                "Regulaciones ambientales",
                "Radicar PQRS",
            ],
        }

    # 1. Intentar responder mediante Gemini AI si la clave existe
    respuesta_ia = consultar_gemini(mensaje, request)
    if respuesta_ia:
        request.session["condy_fallos"] = 0
        return respuesta_ia

    # 2. Motor local basado en reglas semánticas y base de datos
    mensaje_norm = normalizar_texto(mensaje)

    # 3. Control previo anti-alucinaciones y fuera de ámbito (fuera de las llaves)
    caso_especial = detectar_intenciones_especiales_o_fuera_de_ambito(mensaje_norm)
    if caso_especial:
        request.session['condy_fallos'] = 0
        return caso_especial

    # Filtros de regulación y prevención de falsos positivos
    mensaje_norm = (
        mensaje_norm.replace("perros calientes", "comida")
        .replace("perro caliente", "comida")
        .replace("hot dog", "comida")
    )

    user = getattr(request, "user", None)
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
                    # Ponderación mayor si la frase completa coincide
                    puntaje += 5
            else:
                patron = r"\b" + re.escape(kw_norm) + r"\b"
                if re.search(patron, mensaje_norm):
                    puntaje += 2

        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_coincidencia = faq

    # Procesamiento dinámico para intenciones de usuario
    if mejor_coincidencia and mejor_puntaje >= 2:
        request.session["condy_fallos"] = 0
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

        # 3. Si consulta por su saldo a favor y notas de crédito
        elif mejor_coincidencia["id"] == "saldo_a_favor_notas_credito":
            resumen_saldo = obtener_resumen_saldo_favor(user)
            if resumen_saldo:
                respuesta_texto = (
                    f"{resumen_saldo}\n\n"
                    f"Recuerda que tu saldo a favor se aplica automáticamente en futuras reservas o puedes solicitar su reembolso formal."
                )
            elif user and user.is_authenticated:
                respuesta_texto = "Actualmente tu saldo a favor es de COP $0. Las notas de crédito se generan cuando reduces cupos o cancelas reservas conforme a las políticas."
            else:
                respuesta_texto = "Para consultar tu saldo a favor y notas de crédito, por favor inicia sesión en tu cuenta."

        resultado = {
            "response": respuesta_texto,
            "action": mejor_coincidencia.get("action"),
            "options": mejor_coincidencia.get("options", []),
        }
        if "link_url" in mejor_coincidencia:
            resultado["link_url"] = mejor_coincidencia["link_url"]
            resultado["link_text"] = mejor_coincidencia.get("link_text", "Ver más")
        return resultado

    # Manejo de reintentos y preguntas fuera de las llaves
    request.session["condy_fallos"] += 1

    if request.session["condy_fallos"] >= 2:
        request.session["condy_fallos"] = 0
        return {
            "response": (
                "No he identificado una respuesta exacta dentro de la base de conocimientos de Monagua Turismo. "
                "Para orientarte de manera directa, puedes escribir a nuestro WhatsApp oficial al **+57 322 3465191** "
                "o radicar una consulta en **Radicar PQRS**."
            ),
            "fallback_action": "pqrs",
            "link_url": "/pqrs/",
            "link_text": "Radicar PQRS oficial",
            "options": ["Radicar PQRS", "¿Cómo funciona la página?", "Regulaciones ambientales", "Ver catálogo de tours"]
        }
    else:
        return {
            "response": (
                "No encontré información exacta sobre esa consulta dentro de los servicios de Monagua Turismo en Mongua, Boyacá.\n\n"
                "¿Podrías consultarlo con otras palabras o elegir uno de nuestros temas frecuentes?"
            ),
            "options": [
                "¿Cómo funciona la página?",
                "Regulaciones ambientales",
                "¿Qué tours ofrecen?",
                "¿Cómo realizar un pago?",
                "Radicar PQRS",
            ],
        }
