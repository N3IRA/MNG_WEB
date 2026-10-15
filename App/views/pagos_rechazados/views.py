from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from App.models import Pago, Reserva, Usuario
from App.utils import crear_notificacion_sistema


def es_admin(user):
    """Verifica si el usuario autenticado tiene permisos de administrador."""
    return user.is_authenticated and (user.is_staff or getattr(user, 'rol', None) in [Usuario.Roles.ADMIN, 1, 'ADMIN'])


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_pagos_rechazados(request):
    """
    Vista administrativa dedicada exclusivamente a la auditoría, seguimiento
    y gestión de pagos y comprobantes que han sido rechazados en el sistema.
    """
    pagos_rechazados = Pago.objects.filter(estado_transaccion='rechazado').select_related(
        'reserva', 'reserva__usuario', 'reserva__paquete'
    ).order_by('-fecha_envio')

    total_rechazados = pagos_rechazados.count()
    monto_total_rechazado = pagos_rechazados.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    clientes_afectados = pagos_rechazados.values('reserva__usuario').distinct().count()
    reservas_pendientes = pagos_rechazados.filter(reserva__estado_reserva='pendiente').count()

    context = {
        'pagos_rechazados': pagos_rechazados,
        'total_rechazados': total_rechazados,
        'monto_total_rechazado': monto_total_rechazado,
        'clientes_afectados': clientes_afectados,
        'reservas_pendientes': reservas_pendientes,
    }
    return render(request, 'admin/admin_pagos_rechazados.html', context)


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_reconsiderar_pago(request, pk):
    """
    Función administrativa para reconsiderar y aprobar un pago previamente rechazado,
    verificando el monto e impactando la reserva vinculada a confirmada.
    """
    if request.method == 'POST':
        pago = get_object_or_404(Pago.objects.select_related('reserva', 'reserva__usuario'), pk=pk)
        banco = request.POST.get('banco_origen', '').strip() or pago.banco_origen
        monto_str = request.POST.get('monto', '').strip()
        nota = request.POST.get('nota_admin', '').strip()

        try:
            monto_val = Decimal(monto_str) if monto_str else pago.monto
        except (ValueError, TypeError, Decimal.InvalidOperation):
            monto_val = pago.monto

        pago.banco_origen = banco or "Transferencia Verificada"
        pago.monto = monto_val
        pago.estado_transaccion = 'aprobado'
        pago.nota_admin = nota or f"Pago reconsiderado y aprobado por {request.user.get_full_name() or request.user.username}."
        pago.fecha_revision = timezone.now()
        pago.save()

        if pago.reserva:
            pago.reserva.estado_reserva = 'confirmada'
            pago.reserva.save()

        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"El comprobante #{pago.pk} fue reconsiderado y aprobado. Reserva #{pago.reserva.id if pago.reserva else 'N/A'} confirmada.",
            tipo="Comprobante de Pago",
            prioridad="alta"
        )
        messages.success(request, f"¡Pago #{pago.pk} reconsiderado y aprobado con éxito! La reserva ha sido confirmada.")
    return redirect('admin_pagos_rechazados')


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_reabrir_pago(request, pk):
    """
    Función para reabrir un pago rechazado y pasarlo a estado 'pendiente'
    para permitir una nueva revisión por parte del equipo administrativo.
    """
    if request.method == 'POST':
        pago = get_object_or_404(Pago.objects.select_related('reserva'), pk=pk)
        pago.estado_transaccion = 'pendiente'
        pago.fecha_revision = timezone.now()
        pago.nota_admin = f"Pago reabierto para re-validación por {request.user.get_full_name() or request.user.username}."
        pago.save()

        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"El comprobante #{pago.pk} fue reabierto y retornado a estado pendiente.",
            tipo="Comprobante de Pago",
            prioridad="media"
        )
        messages.info(request, f"El pago #{pago.pk} ha sido retornado a estado 'Pendiente' para su re-evaluación.")
    return redirect('admin_pagos_rechazados')


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_actualizar_nota_rechazo(request, pk):
    """
    Permite al administrador modificar o ampliar el motivo de rechazo de un comprobante
    para que el cliente tenga instrucciones claras de corrección.
    """
    if request.method == 'POST':
        pago = get_object_or_404(Pago, pk=pk)
        nueva_nota = request.POST.get('nota_admin', '').strip()
        if not nueva_nota:
            messages.error(request, "El motivo del rechazo no puede estar vacío.")
        else:
            pago.nota_admin = nueva_nota
            pago.fecha_revision = timezone.now()
            pago.save()
            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"Se actualizó la justificación de rechazo para el comprobante #{pago.pk}.",
                tipo="Comprobante de Pago",
                prioridad="baja"
            )
            messages.success(request, f"Motivo de rechazo del comprobante #{pago.pk} actualizado correctamente.")
    return redirect('admin_pagos_rechazados')


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_cancelar_reserva_rechazada(request, pk):
    """
    Permite cancelar la reserva vinculada a un pago rechazado cuando el cliente
    no subsanó el pago, liberando cupos y actualizando el estado de la reserva.
    """
    if request.method == 'POST':
        pago = get_object_or_404(Pago.objects.select_related('reserva'), pk=pk)
        if pago.reserva:
            reserva = pago.reserva
            reserva.estado_reserva = 'cancelada'
            motivo = request.POST.get('motivo_cancelacion', '').strip() or f"Cancelada por pago rechazado no subsanado (Comprobante #{pago.pk})."
            reserva.motivo_cancelacion = motivo
            reserva.save()

            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"La reserva #{reserva.id} fue cancelada definitivamente debido a comprobante de pago rechazado.",
                tipo="Reserva",
                prioridad="alta"
            )
            messages.warning(request, f"La reserva #{reserva.id} ha sido marcada como 'Cancelada' definitivamente.")
        else:
            messages.error(request, "El comprobante no tiene una reserva asociada.")
    return redirect('admin_pagos_rechazados')
