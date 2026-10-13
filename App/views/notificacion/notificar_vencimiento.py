import logging
from datetime import date, timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction
from App.models import Reserva, Notificacion

logger = logging.getLogger(__name__)


def notificar_vencimientos(stdout=None, style=None):
    """
    Notifica a los usuarios con reservas pendientes próximas a vencer (3 días o menos).
    Puede ejecutarse directamente como función o mediante un comando.
    """
    hoy = date.today()
    limite_vencimiento = hoy + timedelta(days=3)

    reservas_pendientes = Reserva.objects.filter(
        estado_reserva='pendiente',
        fecha_inicio__lte=limite_vencimiento,
        fecha_inicio__gte=hoy
    )

    notificaciones_creadas = 0
    errores = 0

    for reserva in reservas_pendientes:
        if not Notificacion.objects.filter(reserva=reserva, tipo='alerta_pago').exists() and reserva.usuario:
            try:
                with transaction.atomic():
                    from django.urls import reverse
                    url_pagos = reverse('mis_reservas_usuario')

                    asunto = f"Aviso de vencimiento: Reserva {reserva.paquete.nombre}"
                    mensaje = (
                        f"¡Atención! Tu reserva para el paquete '{reserva.paquete.nombre}' (Fecha: {reserva.fecha_inicio}) está próxima a vencer. "
                        f"El monto total pendiente es de ${reserva.monto_total}. "
                        f"Para no perder tu cupo, por favor completa tu pago y sube el comprobante desde la sección de 'Mis Reservas' o ve directamente a {url_pagos}."
                    )

                    # Crear la notificación en la plataforma
                    Notificacion.objects.create(
                        reserva=reserva,
                        usuario=reserva.usuario,
                        mensaje=mensaje,
                        tipo='alerta_pago',
                        prioridad='alta'
                    )

                    # Enviar correo electrónico
                    if reserva.usuario.email:
                        send_mail(
                            subject=asunto,
                            message=mensaje,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[reserva.usuario.email],
                            fail_silently=True,
                        )

                    notificaciones_creadas += 1
                    msg = f'Notificación creada exitosamente para la reserva {reserva.id} (Usuario: {reserva.usuario})'
                    if stdout and style:
                        stdout.write(style.SUCCESS(msg))
                    else:
                        logger.info(msg)

            except Exception as e:
                errores += 1
                logger.error(f"Error al procesar notificación para reserva {reserva.id}: {e}")
                if stdout and style:
                    stdout.write(style.ERROR(f'Error con reserva {reserva.id}: {e}'))

    resumen = {
        'creadas': notificaciones_creadas,
        'errores': errores
    }
    if errores > 0:
        msg = f'Sincronización finalizada con {errores} errores. Se crearon {notificaciones_creadas} notificaciones nuevas.'
        if stdout and style:
            stdout.write(style.WARNING(msg))
        else:
            logger.warning(msg)
    else:
        msg = f'Sincronización exitosa. Se crearon {notificaciones_creadas} notificaciones nuevas.'
        if stdout and style:
            stdout.write(style.SUCCESS(msg))
        else:
            logger.info(msg)

    return resumen


class Command(BaseCommand):
    help = 'Notifica a los usuarios con reservas pendientes próximas a vencer (3 días o menos)'

    def handle(self, *args, **kwargs):
        notificar_vencimientos(stdout=self.stdout, style=self.style)
