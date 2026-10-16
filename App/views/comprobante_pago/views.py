import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum
from django.utils import timezone
from App.models import Pago, Reserva, Usuario
from App.utils import crear_notificacion_sistema, registrar_bitacora


def es_admin(user):
    """Verifica si el usuario autenticado tiene permisos de administrador."""
    return user.is_authenticated and (user.is_staff or getattr(user, 'rol', None) in [Usuario.Roles.ADMIN, 1, 'ADMIN'])


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_comprobantes(request):
    """
    Vista administrativa para listar, filtrar y buscar los comprobantes de pago subidos por los usuarios.
    Los comprobantes rechazados se gestionan exclusivamente en su apartado dedicado.
    """
    estado_filtro = request.GET.get('estado', '').strip().lower()

    # Si se intenta filtrar por 'rechazado', redirigir directamente al apartado dedicado
    if estado_filtro == 'rechazado':
        return redirect('admin_pagos_rechazados')

    # Excluir comprobantes rechazados del listado general
    comprobantes = Pago.objects.exclude(estado_transaccion='rechazado').select_related(
        'reserva', 'reserva__usuario', 'reserva__paquete'
    ).order_by('-fecha_envio')

    if estado_filtro in ['pendiente', 'aprobado']:
        comprobantes = comprobantes.filter(estado_transaccion=estado_filtro)

    total = Pago.objects.exclude(estado_transaccion='rechazado').count()
    total_pendientes = Pago.objects.filter(estado_transaccion='pendiente').count()
    total_aprobados = Pago.objects.filter(estado_transaccion='aprobado').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    total_rechazados = Pago.objects.filter(estado_transaccion='rechazado').count()

    context = {
        'comprobantes': comprobantes,
        'estado_filtro': estado_filtro,
        'total': total,
        'total_pendientes': total_pendientes,
        'total_aprobados': total_aprobados,
        'total_rechazados': total_rechazados,
    }
    return render(request, 'admin/admin_comprobantes.html', context)


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_revisar_comprobante(request, pk):
    """
    Vista administrativa para revisar detalladamente un comprobante de pago,
    aprobarlo o rechazarlo, y actualizar sincronizadamente la reserva asociada.
    """
    comprobante = get_object_or_404(
        Pago.objects.select_related('reserva', 'reserva__usuario', 'reserva__paquete'),
        pk=pk
    )
    error_msg = None

    if request.method == 'POST':
        banco_origen = request.POST.get('banco_origen', '').strip()
        monto_str = request.POST.get('monto', '').strip()
        estado_transaccion = request.POST.get('estado_transaccion', '').strip().lower()
        nota_admin = request.POST.get('nota_admin', '').strip()

        if estado_transaccion not in ['pendiente', 'aprobado', 'rechazado']:
            error_msg = "El estado de transacción seleccionado no es válido."
        elif estado_transaccion == 'rechazado' and not nota_admin:
            error_msg = "Debes ingresar una nota del administrador indicando el motivo del rechazo para que el usuario pueda corregirlo."
        else:
            try:
                monto_val = Decimal(monto_str) if monto_str else comprobante.monto
            except (ValueError, TypeError, Decimal.InvalidOperation):
                monto_val = comprobante.monto

            if estado_transaccion == 'aprobado':
                if not banco_origen and not comprobante.banco_origen:
                    error_msg = "Debe especificar el banco o medio de pago de origen para aprobar el comprobante."
                elif not monto_val or monto_val <= 0:
                    error_msg = "Debe especificar un monto pagado válido mayor a cero para aprobar el comprobante."
                elif comprobante.reserva and monto_val < comprobante.reserva.monto_total:
                    error_msg = f"El monto verificado (COP ${monto_val:,.0f}) no puede ser menor al monto total de la reserva (COP ${comprobante.reserva.monto_total:,.0f})."

            if not error_msg:
                estado_anterior = comprobante.estado_transaccion
                comprobante.banco_origen = banco_origen or comprobante.banco_origen
                comprobante.monto = monto_val
                comprobante.estado_transaccion = estado_transaccion
                comprobante.nota_admin = nota_admin
                comprobante.fecha_revision = timezone.now()

                try:
                    comprobante.save()

                    # Actualizar estado de la reserva vinculada
                    if comprobante.reserva:
                        reserva = comprobante.reserva
                        if estado_transaccion == 'aprobado':
                            reserva.estado_reserva = 'confirmada'
                            reserva.save()
                        elif estado_transaccion == 'rechazado' and reserva.estado_reserva == 'confirmada':
                            reserva.estado_reserva = 'pendiente'
                            reserva.save()

                    # Registrar en Bitácora del sistema para auditoría y trazabilidad
                    registrar_bitacora(
                        usuario=request.user,
                        accion='UPDATE',
                        modulo='Comprobantes de Pago',
                        registro_id=comprobante.pk,
                        pago=comprobante,
                        reserva=comprobante.reserva,
                        descripcion=f"Comprobante #{comprobante.pk}: Estado modificado de '{estado_anterior.capitalize()}' a '{estado_transaccion.capitalize()}'. Monto: COP ${monto_val:,.0f}. Banco: {comprobante.banco_origen}. Nota: {nota_admin or 'Sin observaciones'}.",
                        ip_origen=request.META.get('REMOTE_ADDR')
                    )

                    # Registrar notificación en el sistema
                    crear_notificacion_sistema(
                        usuario=request.user,
                        mensaje=f"El comprobante #{comprobante.pk} ha sido actualizado de '{estado_anterior}' a '{estado_transaccion}'.",
                        tipo="Comprobante de Pago",
                        prioridad="alta"
                    )

                    messages.success(request, f"Comprobante #{comprobante.pk} actualizado como '{estado_transaccion.capitalize()}' exitosamente.")
                    destino_url = reverse('admin_comprobantes')

                    if request.headers.get('HX-Request'):
                        # Redirección directa del navegador vía HTMX hacia /admin/comprobantes/
                        response = HttpResponse(status=200)
                        response['HX-Redirect'] = destino_url
                        return response

                    return redirect(destino_url)
                except ValidationError as ve:
                    if hasattr(ve, 'message_dict'):
                        error_msg = " ".join([m for ms in ve.message_dict.values() for m in (ms if isinstance(ms, list) else [ms])])
                    elif hasattr(ve, 'messages'):
                        error_msg = " ".join(ve.messages)
                    else:
                        error_msg = str(ve)

    if request.headers.get('HX-Request') and error_msg:
        response = render(request, 'admin/admin_revisar_comprobante.html', {
            'comprobante': comprobante,
            'error_msg': error_msg,
        })
        response['HX-Trigger'] = json.dumps({
            'mostrarNotificacionBitacora': {
                'tipo': 'error',
                'titulo': 'Atención',
                'mensaje': error_msg
            }
        })
        return response

    context = {
        'comprobante': comprobante,
        'error_msg': error_msg,
    }
    return render(request, 'admin/admin_revisar_comprobante.html', context)


@login_required(login_url='login')
@user_passes_test(es_admin, login_url='login')
def admin_eliminar_comprobante(request, pk):
    """
    Vista administrativa para eliminar un comprobante de pago.
    """
    if request.method == 'POST':
        comprobante = get_object_or_404(Pago, pk=pk)
        reserva_id = comprobante.reserva.id if comprobante.reserva else "N/A"
        pago_id = comprobante.pk

        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"Se ha eliminado el comprobante #{pago_id} vinculado a la reserva #{reserva_id}.",
            tipo="Comprobante de Pago",
            prioridad="alta"
        )

        comprobante.delete()
        messages.success(request, f"El comprobante #{pago_id} ha sido eliminado correctamente.")
    return redirect('admin_comprobantes')


# Retrocompatibilidad: Re-exportar vistas desde su nuevo módulo dedicado 'pagos_rechazados'
from App.views.pagos_rechazados.views import (  # noqa: F401, E402
    admin_pagos_rechazados,
    admin_reconsiderar_pago,
    admin_reabrir_pago,
    admin_actualizar_nota_rechazo,
    admin_cancelar_reserva_rechazada,
)


