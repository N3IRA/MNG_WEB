from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from App.models import Pago, Reserva
from App.utils import crear_notificacion_sistema

from App.forms.pago.forms import ComprobantePagoForm

@login_required(login_url='login')
def enviar_comprobante(request):
    """
    Vista protegida para que el turista envíe el comprobante de pago de una reserva.
    Aplica validación estricta en el servidor mediante ComprobantePagoForm e impide
    la manipulación del monto, estado o reserva desde el navegador del cliente.
    """
    form = ComprobantePagoForm()

    if request.method == 'POST':
        reserva_id = request.POST.get('reserva')
        if not reserva_id:
            messages.error(request, "Por favor selecciona la reserva a la que corresponde este pago.")
            return redirect('enviar_comprobante')

        reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
        es_penalidad = reserva.estado_cancelacion == 'aprobada' and reserva.penalidad and reserva.penalidad > 0

        if not (reserva.estado_reserva == 'pendiente' or es_penalidad):
            messages.error(request, "Esta reserva no está disponible para pago en este momento.")
            return redirect('mis_comprobantes')

        pago_existente = getattr(reserva, 'pago', None)
        if pago_existente and pago_existente.estado_transaccion in ['pendiente', 'aprobado']:
            messages.warning(request, "Esta reserva ya tiene un comprobante registrado o en proceso de revisión.")
            return redirect('mis_comprobantes')

        form = ComprobantePagoForm(request.POST, request.FILES)
        if form.is_valid():
            pago = form.save(commit=False)
            pago.reserva = reserva
            pago.monto = reserva.penalidad if es_penalidad else reserva.monto_total
            pago.estado_transaccion = 'pendiente'
            pago.save()

            crear_notificacion_sistema(
                usuario=request.user,
                reserva=reserva,
                mensaje=f"Se ha enviado un nuevo comprobante de pago para {'la penalidad' if es_penalidad else 'la reserva'} #{reserva.id} del paquete '{reserva.paquete.nombre}'.",
                tipo="Comprobante de Pago",
                prioridad="alta"
            )

            messages.success(request, "¡Tu comprobante de pago ha sido enviado exitosamente y será revisado en breve!")
            return redirect('mis_comprobantes')
        else:
            errores_txt = [str(err[0]) for err in form.errors.values()]
            messages.error(request, f"Error en el comprobante: {' '.join(errores_txt)}")

    selected_reserva_id = request.GET.get('reserva_id', '')
    tipo_solicitado = (request.GET.get('tipo', '') or '').strip().lower()
    reservas_elegibles = list(Reserva.objects.filter(
        usuario=request.user
    ).filter(
        Q(estado_reserva='pendiente') |
        Q(estado_cancelacion='aprobada', penalidad__gt=0)
    ).exclude(pago__isnull=False))

    selected_tipo = 'reserva'
    selected_reserva = None
    if selected_reserva_id:
        selected_reserva = Reserva.objects.filter(usuario=request.user, id=selected_reserva_id).first()
        if selected_reserva and selected_reserva.estado_cancelacion == 'aprobada' and selected_reserva.penalidad and selected_reserva.penalidad > 0:
            selected_tipo = 'penalidad'
        elif selected_reserva:
            selected_tipo = 'reserva'

        if selected_reserva and not any(str(r.id) == str(selected_reserva.id) for r in reservas_elegibles):
            reservas_elegibles.insert(0, selected_reserva)

    if tipo_solicitado in ['reserva', 'penalidad']:
        selected_tipo = tipo_solicitado

    if selected_tipo == 'penalidad' and not selected_reserva_id:
        penalidad_default = next((r for r in reservas_elegibles if r.estado_cancelacion == 'aprobada' and r.penalidad and r.penalidad > 0), None)
        if penalidad_default:
            selected_reserva_id = str(penalidad_default.id)

    total_pendientes = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='pendiente').count()
    total_aprobados = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='aprobado').aggregate(total=Sum('monto'))['total'] or 0
    total_rechazados = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='rechazado').count()

    context = {
        'form': form,
        'reservas_elegibles': reservas_elegibles,
        'selected_reserva_id': selected_reserva_id,
        'selected_tipo': selected_tipo,
        'total_pendientes': total_pendientes,
        'total_aprobados': total_aprobados,
        'total_rechazados': total_rechazados,
    }
    return render(request, 'usuario/pago/enviar_comprobante.html', context)


@login_required(login_url='login')
def mis_comprobantes(request):
    """
    Vista para que el turista consulte el historial y estado de sus comprobantes de pago.
    Soporta filtrado dinámico y actualización asíncrona mediante HTMX sin recargar la página.
    """
    estado_filtro = request.GET.get('estado', '').strip().lower()
    comprobantes = Pago.objects.filter(reserva__usuario=request.user).select_related('reserva', 'reserva__paquete').order_by('-fecha_envio')
    
    total = comprobantes.count()
    total_pendientes = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='pendiente').count()
    total_aprobados = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='aprobado').aggregate(total=Sum('monto'))['total'] or 0
    total_rechazados = Pago.objects.filter(reserva__usuario=request.user, estado_transaccion='rechazado').count()

    if estado_filtro in ['pendiente', 'aprobado', 'rechazado']:
        comprobantes = comprobantes.filter(estado_transaccion=estado_filtro)

    context = {
        'comprobantes': comprobantes,
        'estado_filtro': estado_filtro,
        'total': total,
        'total_pendientes': total_pendientes,
        'total_aprobados': total_aprobados,
        'total_rechazados': total_rechazados,
    }
    return render(request, 'usuario/pago/mis_comprobantes.html', context)

