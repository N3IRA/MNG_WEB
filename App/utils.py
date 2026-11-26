"""
Utilidades del núcleo del proyecto: plantillas de correo HTML, envío de emails, 
generación de PDFs, registro en Bitácora y creación de Notificaciones.
"""

import base64
import io
import logging
import os
from datetime import datetime, time
from functools import wraps

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db.models import Q
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse
from pypdf import PdfReader, PdfWriter
import qrcode
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

MONAGUA_VERDE = '#2c6e3c'
MONAGUA_VERDE_OSCURO = '#1e4a2a'


def _logo_monagua_html():
    """Genera el bloque HTML con el logo Monagua para incluirlo dentro de correos."""
    logo_base64 = get_image_base64('static/img/logo_monagua.webp')
    if logo_base64:
        return (
            '<img src="{logo_base64}" alt="logo_monagua" title="logo_monagua" '
            'style="display:block; width:64px; height:64px; margin:0 auto 14px; border-radius:50%; '
            'object-fit:cover; border:2px solid rgba(44,110,60,0.18); background:#ffffff; '
            'box-shadow:0 8px 18px rgba(44,110,60,0.14);">'
        ).format(logo_base64=logo_base64)
    return (
        '<div style="width:64px; height:64px; line-height:64px; margin:0 auto 14px; text-align:center; '
        'border-radius:50%; background-color:#2c6e3c; color:#ffffff; font-size:30px; font-weight:700; '
        'font-family:Georgia, serif; box-shadow:0 8px 18px rgba(44,110,60,0.14);">M</div>'
    )


# ==========================================
# DECORADORES Y MIXINS
# ==========================================

def solo_turistas_requerido(view_func):
    """
    Decorador para vistas públicas de reserva: permite el acceso a usuarios no autenticados
    o a clientes/turistas. Redirige a administradores a su dashboard.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and getattr(request.user, 'es_admin', False):
            messages.info(request, "Los administradores no pueden realizar reservas de tours.")
            return redirect('dashboard_admin')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


class StaffRequiredMixin(UserPassesTestMixin):
    """
    Mixin para asegurar que el usuario esté autenticado y sea administrador.
    """
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or getattr(self.request.user, 'rol', None) == 1
        )


# ==========================================
# NOTIFICACIONES Y BITÁCORA
# ==========================================

def crear_notificacion_sistema(usuario, mensaje, tipo="Reserva", prioridad="media", reserva=None, **kwargs):
    """
    Crea un registro de notificación en el modelo Notificacion para reflejarse en la UI (campana).
    Acepta argumentos legacy adicionales pero los ignora para no romper referencias anteriores.
    """
    if usuario and getattr(usuario, 'is_authenticated', False):
        try:
            from App.models import Notificacion

            existente = Notificacion.objects.filter(
                usuario=usuario,
                reserva=reserva,
                mensaje=mensaje,
                tipo=tipo,
                leido=False,
            ).first()
            if existente:
                return existente

            return Notificacion.objects.create(
                usuario=usuario,
                reserva=reserva,
                mensaje=mensaje,
                tipo=tipo,
                prioridad=prioridad,
                leido=False
            )
        except Exception as e:
            logger.error(f"Error al crear la notificación en BD: {e}")
    return None


def registrar_bitacora(
    usuario=None,
    accion='UPDATE',
    modulo='',
    registro_id=None,
    descripcion='',
    seguimiento=None,
    reserva=None,
    pqrs=None,
    pago=None,
    ip_origen=None,
    **kwargs
):
    """
    Crea una entrada en el registro de Bitácora del sistema para auditoría interna.
    """
    try:
        from App.models import Bitacora
        return Bitacora.objects.create(
            usuario=usuario,
            seguimiento=seguimiento,
            reserva=reserva,
            pqrs=pqrs,
            pago=pago,
            accion=accion,
            modulo=modulo,
            registro_id=registro_id,
            ip_origen=ip_origen,
            descripcion=descripcion
        )
    except Exception as e:
        logger.error(f"Error registrando en Bitacora: {e}")
        return None


def lista_notificaciones_global(request):
    """
    Context processor para inyectar las notificaciones globales en el layout/campana.
    """
    if hasattr(request, 'user') and request.user.is_authenticated:
        from App.models import Notificacion

        alertas = Notificacion.objects.filter(
            usuario=request.user
        ).select_related('reserva', 'usuario').order_by('-fecha_creacion')[:10]

        contador_no_leidas = Notificacion.objects.filter(
            usuario=request.user,
            leido=False
        ).count()

        return {
            'notificaciones_globales': alertas,
            'contador_notificaciones': contador_no_leidas,
        }

    return {
        'notificaciones_globales': [],
        'contador_notificaciones': 0,
    }


# ==========================================
# PLANTILLAS DE CORREO Y ENVÍO DE EMAILS
# ==========================================

def plantilla_reserva_html(
    nombre_cliente,
    paquete,
    fecha=None,
    adultos=1,
    menores=0,
    punto_encuentro=None,
    hora_encuentro=None,
    estado='pendiente',
    reserva_id='',
    monto_total='0.00',
    url_pago=None,
    url_mis_reservas=None,
):
    """Genera el HTML de un correo electrónico para notificaciones de reservas con diseño mejorado, recordatorio de pago y enlace directo."""
    if isinstance(hora_encuentro, str):
        try:
            hora_encuentro = datetime.strptime(hora_encuentro, '%H:%M').time()
        except ValueError:
            try:
                hora_encuentro = datetime.strptime(hora_encuentro, '%H:%M:%S').time()
            except ValueError:
                hora_encuentro = time(0, 0)

    if not hora_encuentro:
        hora_encuentro = time(0, 0)

    hora_formateada = hora_encuentro.strftime('%H:%M')
    logo_html = _logo_monagua_html()

    # Formateo amigable de moneda para Colombia (COP)
    try:
        monto_float = float(monto_total)
        monto_formateado = f"${monto_float:,.0f} COP".replace(",", ".")
    except (ValueError, TypeError):
        monto_formateado = f"${monto_total} COP"

    # Fallbacks seguros para enlaces de pago y gestión
    if not url_pago:
        try:
            from django.urls import reverse
            if reserva_id:
                url_pago = f"/pagos/enviar-comprobante/?reserva_id={reserva_id}&tipo=reserva"
            else:
                url_pago = reverse('mis_reservas_usuario')
        except Exception:
            url_pago = "/reservas/mis-reservas/"

    if not url_mis_reservas:
        try:
            from django.urls import reverse
            url_mis_reservas = reverse('mis_reservas_usuario')
        except Exception:
            url_mis_reservas = "/reservas/mis-reservas/"

    # Configuración de estados y contenidos
    if estado == 'confirmada':
        color_tag = MONAGUA_VERDE
        bg_caja_estado = '#f4f8f5'
        texto_estado = 'Reserva Confirmada'
        titulo_principal = f'¡Reserva Confirmada, {nombre_cliente}!'
        subtitulo_principal = 'Tu pago ha sido verificado con éxito. Tu cupo está completamente asegurado para vivir esta gran aventura.'
        bloque_alerta_pago = ''
        bloque_boton_accion = f"""
        <div style="text-align: center; margin: 28px 0 15px 0;">
            <a href="{url_mis_reservas}" target="_blank" style="background-color: {MONAGUA_VERDE}; color: #ffffff; text-decoration: none; padding: 14px 34px; border-radius: 30px; font-weight: 700; font-size: 14.5px; display: inline-block; box-shadow: 0 4px 14px rgba(44, 110, 60, 0.25);">
                Ver Mis Reservas →
            </a>
        </div>
        """
        bloque_nota_pie = '¡Gracias por viajar con Monagua! Te esperamos con la mejor energía para descubrir los paisajes de Mongua.'

    elif estado == 'cancelada':
        color_tag = '#dc3545'
        bg_caja_estado = '#fff5f5'
        texto_estado = 'Reserva Cancelada'
        titulo_principal = f'Reserva Cancelada, {nombre_cliente}'
        subtitulo_principal = 'Te confirmamos que la reserva ha sido dada de baja en nuestro sistema según lo solicitado.'
        bloque_alerta_pago = ''
        bloque_boton_accion = ''
        bloque_nota_pie = 'Si consideras que esto es un error o necesitas comunicarte con nuestro equipo, por favor responde directamente a este correo.'

    else:
        # Pendiente de pago
        color_tag = '#ea580c'
        bg_caja_estado = '#fffaf5'
        texto_estado = 'Pendiente de Pago'
        id_texto = f" #{reserva_id}" if reserva_id else ""
        titulo_principal = f'¡Solicitud de Reserva Registrada, {nombre_cliente}!'
        subtitulo_principal = f'Hemos recibido tu solicitud de reserva{id_texto}. Para asegurar tus cupos, completa el pago y adjunta tu comprobante en la plataforma.'
        
        bloque_alerta_pago = f"""
        <div style="background-color: #fff7ed; border: 1px solid #fed7aa; border-left: 5px solid #ea580c; border-radius: 10px; padding: 18px 20px; margin: 24px 0; text-align: left;">
            <div style="margin-bottom: 8px;">
                <span style="font-size: 16px; margin-right: 6px;">⚠️</span>
                <strong style="color: #9a3412; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">Recordatorio Importante de Pago</strong>
            </div>
            <p style="margin: 0; font-size: 13.5px; color: #7c2d12; line-height: 1.6;">
                Tu reserva se encuentra en estado <strong>Pendiente de Pago</strong>. Para garantizar tus cupos debes realizar el pago correspondiente y registrar tu comprobante en la plataforma.
            </p>
            <p style="margin: 8px 0 0 0; font-size: 13.5px; color: #9a3412; font-weight: 600; line-height: 1.6;">
                🔔 <strong>Atención:</strong> Si no realizas el pago oportunamente, el sistema <u>cancelará y eliminará automáticamente</u> tu reserva para liberar los cupos disponibles a otros viajeros.
            </p>
        </div>
        """

        bloque_boton_accion = f"""
        <div style="text-align: center; margin: 28px 0 15px 0;">
            <a href="{url_pago}" target="_blank" style="background-color: {MONAGUA_VERDE}; color: #ffffff; text-decoration: none; padding: 15px 36px; border-radius: 30px; font-weight: 700; font-size: 15px; display: inline-block; box-shadow: 0 6px 18px rgba(44, 110, 60, 0.3); letter-spacing: 0.3px;">
                💳 Pagar y Subir Comprobante →
            </a>
        </div>
        <div style="text-align: center; font-size: 12px; color: #718096; margin-bottom: 25px; line-height: 1.6;">
            ¿El botón no responde? Puedes ingresar directamente copiando y pegando este enlace:<br>
            <a href="{url_pago}" style="color: {MONAGUA_VERDE}; font-weight: 600; word-break: break-all;">{url_pago}</a>
            <br><br>
            O gestiona todas tus solicitudes directamente en <a href="{url_mis_reservas}" style="color: {MONAGUA_VERDE}; font-weight: 600; text-decoration: underline;">Mis Reservas</a>.
        </div>

        <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 18px 20px; margin-top: 20px; text-align: left;">
            <div style="font-size: 12.5px; font-weight: 700; color: #334155; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px;">
                ¿Cómo confirmar tu reserva en 3 pasos?
            </div>
            <table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #475569;">
                <tr>
                    <td style="padding: 4px 10px 4px 0; vertical-align: top; width: 22px; font-weight: 700; color: {MONAGUA_VERDE}; font-size: 14px;">1.</td>
                    <td style="padding: 4px 0;">Realiza tu pago vía transferencia o consignación por el valor exacto de la reserva.</td>
                </tr>
                <tr>
                    <td style="padding: 4px 10px 4px 0; vertical-align: top; width: 22px; font-weight: 700; color: {MONAGUA_VERDE}; font-size: 14px;">2.</td>
                    <td style="padding: 4px 0;">Haz clic en el botón <strong>Pagar y Subir Comprobante</strong> y adjunta la imagen o soporte de pago.</td>
                </tr>
                <tr>
                    <td style="padding: 4px 10px 4px 0; vertical-align: top; width: 22px; font-weight: 700; color: {MONAGUA_VERDE}; font-size: 14px;">3.</td>
                    <td style="padding: 4px 0;">Nuestro equipo verificará la transacción y recibirás tu factura con código QR de confirmación.</td>
                </tr>
            </table>
        </div>
        """
        bloque_nota_pie = 'Una vez recibido tu comprobante, nuestro equipo lo verificará en el menor tiempo posible para confirmar tu cupo definitivamente.'

    # Construcción de la tabla de detalles
    bloque_detalles = ""
    if reserva_id:
        bloque_detalles += f"""
        <tr style="border-bottom: 1px solid #edf2f0;">
            <td style="padding: 11px 0; color: #718096;">Número de Reserva</td>
            <td style="padding: 11px 0; text-align: right; font-weight: 700; color: #1a202c;">#{reserva_id}</td>
        </tr>
        """
    bloque_detalles += f"""
    <tr style="border-bottom: 1px solid #edf2f0;">
        <td style="padding: 11px 0; color: #718096;">Destino / Paquete</td>
        <td style="padding: 11px 0; text-align: right; font-weight: 600; color: #1a202c;">{paquete}</td>
    </tr>
    """
    if fecha:
        bloque_detalles += f"""
        <tr style="border-bottom: 1px solid #edf2f0;">
            <td style="padding: 11px 0; color: #718096;">Fecha de Salida</td>
            <td style="padding: 11px 0; text-align: right; color: #1a202c; font-weight: 500;">{fecha}</td>
        </tr>
        """
    if punto_encuentro:
        bloque_detalles += f"""
        <tr style="border-bottom: 1px solid #edf2f0;">
            <td style="padding: 11px 0; color: #718096;">Punto de encuentro</td>
            <td style="padding: 11px 0; text-align: right; color: #1a202c;">{punto_encuentro}</td>
        </tr>
        """
    if hora_formateada and hora_formateada != "00:00":
        bloque_detalles += f"""
        <tr style="border-bottom: 1px solid #edf2f0;">
            <td style="padding: 11px 0; color: #718096;">Hora de encuentro</td>
            <td style="padding: 11px 0; text-align: right; color: #1a202c;">{hora_formateada}</td>
        </tr>
        """
    bloque_detalles += f"""
    <tr style="border-bottom: 1px solid #edf2f0;">
        <td style="padding: 11px 0; color: #718096;">Acompañantes</td>
        <td style="padding: 11px 0; text-align: right; color: #1a202c; font-weight: 500;">
            {adultos} Adulto{'s' if int(adultos) != 1 else ''}{f' • {menores} Menor' + ('es' if int(menores) != 1 else '') if int(menores) > 0 else ''}
        </td>
    </tr>
    <tr style="border-top: 2px solid #edf2f0;">
        <td style="padding: 14px 0 6px 0; color: #2d3748; font-weight: 700; font-size: 15px;">Monto Total a Pagar</td>
        <td style="padding: 14px 0 6px 0; text-align: right; font-weight: 800; color: {MONAGUA_VERDE}; font-size: 18px;">{monto_formateado}</td>
    </tr>
    """

    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f4f7f5; margin: 0; padding: 40px 15px;">
        <div style="max-width: 580px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 24px rgba(44, 110, 60, 0.08); border: 1px solid #e2e8f0;">
            <div style="background-color: {MONAGUA_VERDE}; text-align: center; padding: 36px 20px 28px 20px;">
                {logo_html}
                <div style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 2px; margin-bottom: 4px;">MONAGUA</div>
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.85); font-weight: bold;">Experiencias Ecoturísticas</div>
            </div>
            <div style="padding: 35px 30px; color: #2d3748; line-height: 1.6;">
                <h2 style="font-size: 22px; color: {MONAGUA_VERDE}; margin-top: 0; margin-bottom: 8px; font-weight: 700; text-align: center;">{titulo_principal}</h2>
                <p style="font-size: 14.5px; color: #4a5568; text-align: center; margin-bottom: 25px; line-height: 1.5;">{subtitulo_principal}</p>

                <!-- Resumen de la Reserva -->
                <div style="background-color: {bg_caja_estado}; border: 1px solid {color_tag}40; border-radius: 12px; padding: 22px; margin-bottom: 20px;">
                    <div style="text-align: center; margin-bottom: 18px;">
                        <span style="font-size: 12px; font-weight: bold; color: #ffffff; background-color: {color_tag}; padding: 4px 14px; border-radius: 20px; text-transform: uppercase; letter-spacing: 0.5px;">{texto_estado}</span>
                    </div>
                    <table style="width: 100%; border-collapse: collapse; font-size: 14.5px;">
                        {bloque_detalles}
                    </table>
                </div>

                <!-- Recordatorio importante de pago si aplica -->
                {bloque_alerta_pago}

                <!-- Botón de acción para pagar -->
                {bloque_boton_accion}

                <!-- Nota informativa -->
                <table style="width: 100%; background-color: #f8fafc; border-radius: 8px; border: 1px dashed #cbd5e1; margin-top: 20px;">
                    <tr>
                        <td style="padding: 14px; font-size: 12.5px; color: #475569; text-align: center; font-weight: 500; line-height: 1.5;">
                            <strong>Nota:</strong> {bloque_nota_pie}
                        </td>
                    </tr>
                </table>
            </div>

            <!-- Footer -->
            <div style="background-color: #fafdfb; text-align: center; padding: 25px 20px; border-top: 1px solid #edf2f0;">
                <p style="margin: 0; font-size: 13px; color: #718096; font-weight: 600;">Monagua Experiencias Ecoturísticas</p>
                <p style="margin: 5px 0 0 0; font-size: 11.5px; color: #a0aec0;">Mongua, Boyacá, Colombia · Naturaleza, Cultura y Aventura</p>
                <p style="margin: 12px 0 0 0; font-size: 12px; color: {MONAGUA_VERDE}; font-weight: bold;">© 2026 Monagua</p>
            </div>
        </div>
    </body>
    </html>
    """


def plantilla_cancelacion_html(nombre_cliente, paquete, estado, penalidad="0.00"):
    """Genera el HTML de un correo electrónico para notificaciones de cancelaciones."""
    logo_html = _logo_monagua_html()

    if estado in ['aceptada', 'confirmada', 'aprobada']:
        color_tag = '#dc3545'
        bg_caja_estado = '#fff5f5'
        texto_estado = 'Solicitud Aprobada'
        mensaje_cuerpo = f'La solicitud de cancelación de tu viaje fue procesada con éxito. Ten en cuenta que se aplicará una penalidad de <strong style="color: #dc3545; font-size: 17px;">${penalidad}</strong> conforme a las políticas del servicio.'
    elif estado in ['rechazada', 'cancelada']:
        color_tag = MONAGUA_VERDE
        bg_caja_estado = '#f4f8f5'
        texto_estado = 'Solicitud Rechazada'
        mensaje_cuerpo = 'Tu solicitud de cancelación ha sido revisada y <strong>no ha sido aprobada</strong>. Esto significa que tu itinerario sigue en pie y <strong>tu reserva continúa completamente activa</strong>. ¡Te esperamos!'
    else:
        color_tag = MONAGUA_VERDE
        bg_caja_estado = '#fafdfb'
        texto_estado = 'En Revisión / Recibida'
        mensaje_cuerpo = 'Hemos recibido tu solicitud de cancelación. Nuestro equipo está analizando los detalles de tu caso bajo las políticas vigentes. Te enviaremos una notificación definitiva lo antes posible.'

    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f4f7f5; margin: 0; padding: 40px 15px;">
        <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 24px rgba(44, 110, 60, 0.08);">
            <div style="background-color: {MONAGUA_VERDE}; text-align: center; padding: 36px 20px 28px 20px;">
                {logo_html}
                <div style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 2px; margin-bottom: 6px;">MONAGUA</div>
                <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 2px; color: rgba(255,255,255,0.8); font-weight: bold;">Actualización de Solicitud</div>
            </div>
            <div style="padding: 40px; color: #2d3748; line-height: 1.7;">
                <h2 style="font-size: 24px; color: {MONAGUA_VERDE}; margin-top: 0; text-align: center; font-weight: 600;">Estado de tu Cancelación</h2>
                <p style="font-size: 15px; color: #4a5568; text-align: center; margin-bottom: 30px;">Hola {nombre_cliente}, hay novedades sobre tu solicitud para el paquete: <strong>{paquete}</strong></p>
                <div style="background-color: {bg_caja_estado}; border: 1px solid {color_tag}40; border-radius: 12px; padding: 25px; margin-bottom: 30px; text-align: center;">
                    <span style="font-size: 11px; font-weight: bold; background-color: {color_tag}; color: #ffffff; padding: 4px 14px; border-radius: 20px; text-transform: uppercase; letter-spacing: 1px;">{texto_estado}</span>
                    <p style="margin: 20px 0 0 0; font-size: 15px; color: #2d3748; line-height: 1.6;">{mensaje_cuerpo}</p>
                </div>
                <p style="font-size: 13px; color: #718096; text-align: center; margin-top: 30px;">Si crees que hay un error o requieres asistencia personalizada, responde a este correo directamente.</p>
            </div>
            <div style="background-color: #fafdfb; text-align: center; padding: 30px 20px; border-top: 1px solid #edf2f0;">
                <p style="margin: 0; font-size: 13px; color: #718096; font-weight: 600;">Monagua Experiencias</p>
                <p style="margin: 5px 0 0 0; font-size: 11px; color: #a0aec0;">Estás recibiendo este correo porque realizaste una solicitud en nuestro sitio web.</p>
                <p style="margin: 15px 0 0 0; font-size: 12px; color: {MONAGUA_VERDE}; font-weight: bold;">© 2026</p>
            </div>
        </div>
    </body>
    </html>
    """


def enviar_correo_html_monagua(asunto, mensaje_texto, destinatario, html_contenido):
    """Envía un correo electrónico con contenido HTML desde la cuenta configurada."""
    if not destinatario:
        return False
    try:
        send_mail(
            asunto,
            mensaje_texto,
            settings.EMAIL_HOST_USER,
            [destinatario],
            fail_silently=False,
            html_message=html_contenido
        )
        return True
    except Exception as e:
        logger.error("Error al enviar correo electrónico a %s: %s", destinatario, e)
        return False


# ==========================================
# GENERACIÓN DE PDFS Y QR
# ==========================================

def get_image_base64(relative_path):
    """Retorna la representación en base64 de una imagen estática local."""
    file_path = os.path.join(settings.BASE_DIR, relative_path)
    if os.path.exists(file_path):
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            ext = os.path.splitext(file_path)[1].replace('.', '')
            mime = 'image/webp' if ext == 'webp' else ('image/png' if ext == 'png' else 'image/jpeg')
            return f"data:{mime};base64,{encoded_string}"
    return ""


def get_qr_base64(url):
    """Genera un código QR para la URL dada y lo retorna en formato base64."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    encoded_string = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{encoded_string}"


def generar_factura_pdf_bytes(reserva, request=None, password=None):
    """Genera el contenido en bytes del PDF de la factura, opcionalmente protegido por contraseña."""
    pago = getattr(reserva, 'pago', None)
    comprobante = pago if (pago and getattr(pago, 'estado_transaccion', None) == 'aprobado') else None
    metodo_pago = (comprobante.banco_origen or comprobante.metodo_pago) if comprobante else "Transferencia Bancaria"

    documento_tipo = getattr(reserva.usuario, 'tipo_documento', 'Documento') or "Documento"
    documento_num = getattr(reserva.usuario, 'numero_documento', '—') or "—"

    if request:
        abs_url = request.build_absolute_uri(reverse('ver_factura', args=[reserva.id]))
    else:
        domain = "localhost:8000"
        scheme = "http" if settings.DEBUG else "https"
        abs_url = f"{scheme}://{domain}{reverse('ver_factura', args=[reserva.id])}"

    qr_base64 = get_qr_base64(abs_url)
    logo_base64 = get_image_base64('static/img/logo_monagua.webp')

    if hasattr(reserva, 'fecha_registro') and reserva.fecha_registro:
        fecha_emision = reserva.fecha_registro.strftime('%d/%m/%Y')
    else:
        fecha_emision = reserva.fecha_inicio.strftime('%d/%m/%Y') if getattr(reserva, 'fecha_inicio', None) else ""

    cliente_nombre = getattr(reserva.usuario, 'nombre_completo', None) if reserva.usuario else None
    if not cliente_nombre and reserva.usuario:
        cliente_nombre = reserva.usuario.get_full_name() or reserva.usuario.username

    context = {
        'reserva_id': reserva.id,
        'nro_factura': f"FAC-1000{reserva.id}",
        'cliente_nombre': cliente_nombre or 'Cliente',
        'cliente_email': reserva.usuario.email if reserva.usuario else '',
        'cliente_documento_tipo': documento_tipo,
        'cliente_documento': documento_num,
        'fecha_emision': fecha_emision,
        'metodo_pago': metodo_pago,
        'paquete_nombre': reserva.paquete.nombre if reserva.paquete else 'Aventura Mongua',
        'pasajeros_adultos': reserva.numero_adultos if hasattr(reserva, 'numero_adultos') else 1,
        'pasajeros_menores': reserva.numero_menores if hasattr(reserva, 'numero_menores') else 0,
        'subtotal': reserva.monto_total,
        'total': reserva.monto_total,
        'logo_base64': logo_base64,
        'qr_base64': qr_base64,
    }

    html_string = render_to_string('usuario/reserva/factura_pdf.html', context)
    pdf_temp = io.BytesIO()
    pisa.pisaDocument(io.BytesIO(html_string.encode("UTF-8")), pdf_temp)
    pdf_bytes = pdf_temp.getvalue()

    if password:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)
            writer.encrypt(user_password=password, owner_password=None)
            pdf_encrypted = io.BytesIO()
            writer.write(pdf_encrypted)
            return pdf_encrypted.getvalue()
        except Exception as e:
            logger.error(f"Error encrypting PDF: {e}")

    return pdf_bytes


def enviar_correo_confirmacion_con_factura(reserva, request=None):
    """Genera la factura PDF encriptada con el número de documento y envía el correo."""
    password = getattr(reserva.usuario, 'numero_documento', None)
    if password:
        password = str(password).strip()

    pdf_bytes = generar_factura_pdf_bytes(reserva, request=request, password=password)

    nombre_cliente = reserva.usuario.get_full_name() or reserva.usuario.username
    asunto = f"¡Tu Pago fue Aprobado y tu Reserva #{reserva.id} está Confirmada! - Monagua"
    mensaje_texto = (
        f"Hola {nombre_cliente}, ¡excelentes noticias! Tu comprobante de pago ha sido aprobado con éxito "
        f"y tu aventura está 100% asegurada. Hemos adjuntado tu factura oficial en formato PDF."
    )

    context = {
        'nombre_cliente': nombre_cliente,
        'reserva_id': reserva.id,
        'paquete': reserva.paquete.nombre,
        'fecha': reserva.fecha_inicio.strftime('%d/%m/%Y') if getattr(reserva, 'fecha_inicio', None) else "",
        'adultos': reserva.numero_adultos,
        'menores': reserva.numero_menores,
        'monto_total': str(reserva.monto_total),
        'tiene_password': bool(password),
        'logo_base64': get_image_base64('static/img/logo_monagua.webp'),
    }

    html_contenido = render_to_string('email/factura_email.html', context)

    email = EmailMultiAlternatives(
        subject=asunto,
        body=mensaje_texto,
        from_email=settings.EMAIL_HOST_USER,
        to=[reserva.usuario.email],
    )
    email.attach_alternative(html_contenido, "text/html")

    pdf_filename = f"factura_FAC-1000{reserva.id}.pdf"
    email.attach(pdf_filename, pdf_bytes, "application/pdf")

    email.send(fail_silently=False)


def notificar_administradores(mensaje, tipo="Sistema", prioridad="media", reserva=None):
    """Crea una notificación individual para todos los usuarios administradores activos."""
    try:
        from django.contrib.auth import get_user_model
        Usuario = get_user_model()
        administradores = Usuario.objects.filter(is_active=True).filter(
            Q(is_staff=True) | Q(rol=Usuario.Roles.ADMIN)
        ).distinct()
        creadas = []
        for administrador in administradores:
            creada = crear_notificacion_sistema(
                administrador,
                mensaje,
                tipo=tipo,
                prioridad=prioridad,
                reserva=reserva,
            )
            if creada:
                creadas.append(creada)
        return creadas
    except Exception as e:
        logger.error(f"Error al notificar administradores: {e}")
        return []