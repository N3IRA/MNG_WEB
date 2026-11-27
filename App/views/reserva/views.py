import hashlib
import json
import re
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import logging
from django.http import HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse

from App.models import Reserva, Paquete, Tarifa, Pago, ModificacionReserva, NotaCredito, Usuario, Reembolso
from App.validators import validar_archivo_subido, validar_comprobante_pago

logger = logging.getLogger(__name__)
from App.forms.reserva.forms import ReservaForm
from App.utils import (
    plantilla_reserva_html,
    plantilla_cancelacion_html,
    enviar_correo_html_monagua,
    get_image_base64,
    get_qr_base64,
    generar_factura_pdf_bytes,
    enviar_correo_confirmacion_con_factura,
    crear_notificacion_sistema,
    StaffRequiredMixin,
    solo_turistas_requerido
)

def requiere_administrador(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not (request.user.is_authenticated and (request.user.is_staff or getattr(request.user, 'rol', None) == 1)):
            messages.error(request, "No tienes permisos de administrador.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def requiere_autenticacion(view_func):
    return login_required(view_func, login_url='login')


# =========================
# GESTIÓN DE RESERVAS (ADMIN)
# =========================

@method_decorator(requiere_administrador, name='dispatch')
class GestionReservasListView(ListView):
    """Vista administrativa para la gestión, filtrado y monitoreo de reservas."""
    model = Reserva
    template_name = 'admin/reserva/reservas_admin.html'
    context_object_name = 'reservas'

    def get_queryset(self):
        estado_param = self.request.GET.get('estado')

        if estado_param == 'todas':
            queryset = Reserva.objects.all()
        elif estado_param:
            queryset = Reserva.objects.filter(estado_reserva=estado_param)
        else:
            queryset = Reserva.objects.exclude(estado_reserva='cancelada')
            
        return queryset.select_related('usuario', 'paquete', 'pago').order_by('-id')

    def _calcular_hash_estado(self, queryset, stats):
        filas = list(
            queryset.values_list(
                'id',
                'estado_reserva',
                'numero_adultos',
                'numero_menores',
                'monto_total',
                'estado_cancelacion',
            )
        )
        payload = f"{stats}|{filas}"
        return hashlib.md5(payload.encode('utf-8')).hexdigest()

    def get(self, request, *args, **kwargs):
        last_hash = request.GET.get('last_hash')
        if request.headers.get('HX-Request') == 'true' and last_hash:
            queryset = self.get_queryset()
            stats = Reserva.objects.aggregate(
                total=Count('id'),
                pendientes=Count('id', filter=Q(estado_reserva='pendiente')),
                confirmadas=Count('id', filter=Q(estado_reserva='confirmada')),
                canceladas=Count('id', filter=Q(estado_reserva='cancelada'))
            )
            current_hash = self._calcular_hash_estado(queryset, stats)
            if current_hash == last_hash:
                return HttpResponse(status=204)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Gestión de Reservas'
        context['ultima_actualizacion'] = timezone.localtime(timezone.now())
        
        stats = Reserva.objects.aggregate(
            total=Count('id'),
            pendientes=Count('id', filter=Q(estado_reserva='pendiente')),
            confirmadas=Count('id', filter=Q(estado_reserva='confirmada')),
            canceladas=Count('id', filter=Q(estado_reserva='cancelada'))
        )
        context.update(stats)
        context['reservas_hash'] = self._calcular_hash_estado(self.object_list, stats)

        context['stats_list'] = [
            ('Total', stats['total'], 'text-dark'),
            ('Pendientes', stats['pendientes'], 'text-warning'),
            ('Confirmadas', stats['confirmadas'], 'text-success'),
            ('Canceladas', stats['canceladas'], 'text-danger'),
        ]

        context['estado_seleccionado'] = self.request.GET.get('estado', '')
        return context


@method_decorator(requiere_administrador, name='dispatch')
class CrearReservaAdminView(CreateView):
    model = Reserva
    form_class = ReservaForm
    template_name = 'admin/reserva/agregar_reserva.html'
    success_url = reverse_lazy('gestion_reservas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tarifas_activas = Tarifa.objects.filter(
            estado=True,
            paquete__estado=True,
            temporada__estado=True
        ).select_related('temporada')

        tarifas_por_paquete = {}
        for t in tarifas_activas:
            if t.temporada and t.temporada.fecha_inicio and t.temporada.fecha_fin:
                pid = str(t.paquete_id)
                if pid not in tarifas_por_paquete:
                    tarifas_por_paquete[pid] = []
                tarifas_por_paquete[pid].append({
                    'from': t.temporada.fecha_inicio.strftime('%Y-%m-%d'),
                    'to': t.temporada.fecha_fin.strftime('%Y-%m-%d'),
                })
        context['tarifas_por_paquete'] = tarifas_por_paquete

        clientes_qs = Usuario.objects.filter(
            rol=Usuario.Roles.CLIENTE,
            is_active=True
        ).order_by('first_name', 'last_name', 'username')

        context['clientes_registrados'] = [
            {
                'id': c.id,
                'nombre': c.nombre_completo,
                'email': c.email,
                'documento': c.numero_documento,
                'tipo_documento': c.tipo_documento or 'CC',
                'telefono': c.telefono or '',
            }
            for c in clientes_qs
        ]
        return context

    def form_valid(self, form):
        from django.core.exceptions import ValidationError as DjangoValidationError
        adultos = form.cleaned_data.get('numero_adultos', 0)
        menores = form.cleaned_data.get('numero_menores', 0)
        fecha = form.cleaned_data.get('fecha_inicio')

        if adultos < 1:
            form.add_error('numero_adultos', 'Debe haber al menos 1 adulto en la reserva.')
            return self.form_invalid(form)

        if menores < 0:
            form.add_error('numero_menores', 'El número de menores no puede ser negativo.')
            return self.form_invalid(form)

        if fecha and fecha < date.today():
            form.add_error('fecha_inicio', 'No puedes crear reservas en fechas pasadas.')
            return self.form_invalid(form)

        paquete = form.cleaned_data.get('paquete')
        if paquete and fecha:
            tiene_tarifa = Tarifa.objects.filter(
                paquete=paquete,
                estado=True,
                temporada__estado=True,
                temporada__fecha_inicio__lte=fecha,
                temporada__fecha_fin__gte=fecha,
            ).exists()
            if not tiene_tarifa:
                form.add_error('fecha_inicio', 'No hay una tarifa activa vigente para este paquete en la fecha seleccionada. Crea o ajusta la tarifa primero.')
                return self.form_invalid(form)

        try:
            response = super().form_valid(form)
        except DjangoValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for field_name, errors in exc.message_dict.items():
                    target_field = field_name if field_name in form.fields else None
                    for err in errors:
                        form.add_error(target_field, err)
            else:
                for err in exc.messages:
                    form.add_error(None, err)
            return self.form_invalid(form)

        if self.object.usuario:
            crear_notificacion_sistema(
                usuario=self.object.usuario,
                reserva=self.object,
                mensaje=f"Se ha creado tu reserva para el paquete '{self.object.paquete.nombre}'",
                tipo="Reserva",
                prioridad="media"
            )

        # Enviar correo de confirmación de reserva (tanto para cliente registrado como presencial)
        email_destino = self.object.email_cliente
        if email_destino:
            try:
                url_pago = self.request.build_absolute_uri(f"{reverse('enviar_comprobante')}?reserva_id={self.object.id}&tipo=reserva") if self.request else None
                asunto = f"¡Tu Reserva #{self.object.id} ha sido registrada con éxito! - Monagua"
                mensaje_texto = (
                    f"Hola {self.object.nombre_cliente},\n\n"
                    f"Tu reserva para el tour '{self.object.paquete.nombre}' ha sido registrada con éxito "
                    f"{'en modalidad presencial' if self.object.es_presencial else ''}.\n"
                    f"Fecha de inicio: {self.object.fecha_inicio.strftime('%d/%m/%Y') if self.object.fecha_inicio else ''}\n"
                    f"Adultos: {self.object.numero_adultos} | Menores: {self.object.numero_menores}\n"
                    f"Monto total: COP ${self.object.monto_total:,.0f}\n\n"
                )
                if url_pago:
                    mensaje_texto += f"Recuerda realizar tu pago y adjuntar tu comprobante de pago a tiempo:\n{url_pago}"

                html_contenido = plantilla_reserva_html(
                    nombre_cliente=self.object.nombre_cliente,
                    paquete=self.object.paquete.nombre,
                    fecha=self.object.fecha_inicio.strftime('%d/%m/%Y') if self.object.fecha_inicio else None,
                    adultos=self.object.numero_adultos,
                    menores=self.object.numero_menores,
                    punto_encuentro=self.object.paquete.punto_encuentro or None,
                    hora_encuentro=self.object.paquete.hora_encuentro.strftime('%H:%M') if self.object.paquete.hora_encuentro else None,
                    estado=self.object.estado_reserva,
                    reserva_id=self.object.id,
                    monto_total=f"{self.object.monto_total:,.0f}",
                    url_pago=url_pago,
                )
                enviar_correo_html_monagua(asunto, mensaje_texto, email_destino, html_contenido)
            except Exception as e:
                logger.error(f"Error enviando correo de reserva creada (admin): {e}")

        messages.success(self.request, f"Reserva #{self.object.id} para '{self.object.paquete.nombre}' creada con éxito.", extra_tags='reserva')
        return response


@method_decorator(requiere_administrador, name='dispatch')
class EditarReservaAdminView(UpdateView):
    model = Reserva
    form_class = ReservaForm
    template_name = 'admin/reserva/editar_reserva.html'
    success_url = reverse_lazy('gestion_reservas')

    def form_valid(self, form):
        nuevo_estado = form.cleaned_data.get('estado_reserva')

        reserva_antigua = self.get_object()
        adultos_anteriores = reserva_antigua.numero_adultos
        menores_anteriores = reserva_antigua.numero_menores
        monto_anterior = reserva_antigua.monto_total

        adultos_nuevos = form.cleaned_data.get('numero_adultos', adultos_anteriores)
        menores_nuevos = form.cleaned_data.get('numero_menores', menores_anteriores)
        personas_cambiaron = adultos_nuevos != adultos_anteriores or menores_nuevos != menores_anteriores

        motivo_modificacion = (self.request.POST.get('motivo_modificacion') or '').strip()
        if personas_cambiaron:
            if getattr(reserva_antigua, 'pago', None) is not None:
                form.add_error('numero_adultos', 'No se pueden cambiar personas porque ya existe un comprobante o pago registrado.')
                return self.form_invalid(form)
            if reserva_antigua.estado_reserva == 'cancelada':
                form.add_error('numero_adultos', 'No se pueden cambiar personas de una reserva cancelada.')
                return self.form_invalid(form)
            if len(motivo_modificacion) < 5:
                form.add_error('numero_adultos', 'Debes indicar un motivo válido para corregir la cantidad de personas.')
                return self.form_invalid(form)

            inicio_viaje = timezone.make_aware(
                datetime.combine(reserva_antigua.fecha_inicio, datetime.min.time()),
                timezone.get_current_timezone()
            )
            if inicio_viaje - timezone.now() < timedelta(hours=48):
                form.add_error('numero_adultos', 'Solo se pueden cambiar personas con al menos 48 horas de anticipación.')
                return self.form_invalid(form)

        if nuevo_estado == 'confirmada':
            pago = getattr(reserva_antigua, 'pago', None)
            if not pago or pago.estado_transaccion != 'aprobado':
                form.add_error('estado_reserva', 'No se puede confirmar la reserva sin un pago aprobado.')
                return self.form_invalid(form)

        if nuevo_estado == 'cancelada' and reserva_antigua.estado_cancelacion != 'aprobada':
            form.add_error('estado_reserva', 'La reserva solo puede cancelarse después de aprobar la solicitud de cancelación.')
            return self.form_invalid(form)

        valor_viejo = f"Estado: {reserva_antigua.estado_reserva}, Fecha: {reserva_antigua.fecha_inicio}, Adultos: {reserva_antigua.numero_adultos}, Menores: {reserva_antigua.numero_menores}"

        response = super().form_valid(form)
        reserva = self.object
        nombre_cliente = reserva.nombre_cliente
        
        valor_nuevo = f"Estado: {reserva.estado_reserva}, Fecha: {reserva.fecha_inicio}, Adultos: {reserva.numero_adultos}, Menores: {reserva.numero_menores}"

        if personas_cambiaron:
            reserva.recalcular_monto()
            reserva.save(update_fields=['monto_total'])
            ModificacionReserva.objects.create(
                reserva=reserva,
                usuario=self.request.user,
                adultos_anteriores=adultos_anteriores,
                adultos_nuevos=reserva.numero_adultos,
                menores_anteriores=menores_anteriores,
                menores_nuevos=reserva.numero_menores,
                monto_anterior=monto_anterior,
                monto_nuevo=reserva.monto_total,
                motivo=motivo_modificacion,
                realizado_por_admin=True
            )
            if reserva.usuario:
                crear_notificacion_sistema(
                    usuario=reserva.usuario,
                    reserva=reserva,
                    mensaje=f"Un administrador actualizó los pasajeros de tu reserva #{reserva.id}: {reserva.numero_adultos} adulto(s) y {reserva.numero_menores} menor(es). Nuevo total: COP ${reserva.monto_total:,.0f}.",
                    tipo="Reserva",
                    prioridad="alta"
                )

        if reserva.estado_reserva in ['confirmada', 'cancelada']:
            if reserva.usuario:
                crear_notificacion_sistema(
                    usuario=reserva.usuario,
                    reserva=reserva,
                    mensaje=f"El estado de tu reserva #{reserva.id} ha sido cambiado de '{reserva_antigua.estado_reserva}' a '{reserva.estado_reserva}'.",
                    tipo="Reserva",
                    prioridad="alta"
                )

            if reserva.estado_reserva == 'confirmada':
                try:
                    enviar_correo_confirmacion_con_factura(reserva, request=self.request)
                except Exception as e:
                    print(f"Error enviando correo de confirmación de reserva (admin): {e}")
            else:
                url_pago = self.request.build_absolute_uri(f"{reverse('enviar_comprobante')}?reserva_id={reserva.id}&tipo=reserva") if self.request else None
                url_mis_reservas = self.request.build_absolute_uri(reverse('mis_reservas_usuario')) if self.request else None

                asunto = f"Tu Reserva #{reserva.id} ha sido {reserva.estado_reserva.upper()} - Monagua"
                mensaje_texto = f"Hola {nombre_cliente}, el estado de tu reserva #{reserva.id} para {reserva.paquete.nombre} ha cambiado a {reserva.estado_reserva}."
                if reserva.estado_reserva == 'pendiente' and url_pago:
                    mensaje_texto += f"\n\nRecuerda que debes realizar tu pago y adjuntar tu comprobante a tiempo; de lo contrario, la reserva será cancelada automáticamente:\n{url_pago}"
                
                html_contenido = plantilla_reserva_html(
                    nombre_cliente=nombre_cliente,
                    paquete=reserva.paquete.nombre,
                    fecha=reserva.fecha_inicio.strftime('%d/%m/%Y') if reserva.fecha_inicio else None,
                    adultos=reserva.numero_adultos,
                    menores=reserva.numero_menores,
                    punto_encuentro=reserva.paquete.punto_encuentro or None,
                    hora_encuentro=reserva.paquete.hora_encuentro.strftime('%H:%M') if reserva.paquete.hora_encuentro else None,
                    estado=reserva.estado_reserva,
                    reserva_id=reserva.id,
                    monto_total=str(reserva.monto_total),
                    url_pago=url_pago,
                    url_mis_reservas=url_mis_reservas
                )
                if reserva.email_cliente:
                    try:
                        enviar_correo_html_monagua(asunto, mensaje_texto, reserva.email_cliente, html_contenido)
                    except Exception as e:
                        print(f"Error enviando correo de actualización de reserva: {e}")
                
        messages.success(self.request, f"Reserva #{reserva.id} para '{reserva.paquete.nombre}' actualizada exitosamente.", extra_tags='reserva')
        return response

@method_decorator(requiere_administrador, name='dispatch')
class EliminarReservaAdminView(DeleteView):
    model = Reserva
    template_name = 'admin/reserva/eliminar_reserva.html'
    success_url = reverse_lazy('gestion_reservas')

    def form_valid(self, form):
        """
        Django 6.1: BaseDeleteView.post() borra el objeto via form_valid(),
        NO via delete(). La notificación debe crearse aquí (antes del borrado)
        para que el cliente reciba el aviso de eliminación de su reserva.
        """
        self.object = self.get_object()
        reserva_id = self.object.id
        usuario_reserva = self.object.usuario
        valor_viejo = f"ID: {self.object.id}, Cliente: {self.object.usuario}, Paquete: {self.object.paquete.nombre if self.object.paquete else 'N/A'}, Estado: {self.object.estado_reserva}"

        if usuario_reserva:
            crear_notificacion_sistema(
                usuario=usuario_reserva,
                mensaje=f"Tu reserva #{reserva_id} ha sido eliminada del sistema. Detalles previos: {valor_viejo}",
                tipo="Reserva",
                prioridad="alta"
            )

        messages.success(self.request, f"La reserva #{reserva_id} fue eliminada exitosamente.", extra_tags='reserva')
        return super().form_valid(form)


def normalizar_estados_cancelacion_usuario(usuario):
    """Corrige inconsistencias de estado para que la reserva y la cancelación siempre estén alineadas."""
    # Caso 1: si el usuario solicitó cancelar SIN penalidad (flujo de auto-aprobación),
    # la reserva debe quedar cancelada. Con penalidad > 0 la reserva se mantiene activa
    # hasta que el administrador revise la solicitud.
    Reserva.objects.filter(
        usuario=usuario,
        estado_cancelacion='pendiente',
        penalidad__lte=0
    ).exclude(
        estado_reserva='cancelada'
    ).update(estado_reserva='cancelada')

    # Caso 2: si la reserva ya fue cancelada y la solicitud sigue pendiente, solo se aprueba automáticamente cuando no hay penalidad.
    Reserva.objects.filter(
        usuario=usuario,
        estado_reserva='cancelada',
        estado_cancelacion='pendiente',
        penalidad__lte=0
    ).update(estado_cancelacion='aprobada')

    # Caso 3: una solicitud ya aprobada no puede seguir activa en el flujo de reservas del usuario.
    Reserva.objects.filter(
        usuario=usuario,
        estado_cancelacion='aprobada'
    ).exclude(
        estado_reserva='cancelada'
    ).update(estado_reserva='cancelada')

    # Caso 4: una cancelación rechazada no puede dejar la reserva en estado cancelado si fue reactivada.
    # Al reactivar, solo se confirma si existe pago aprobado; si no, vuelve a 'pendiente'.
    for reserva in Reserva.objects.filter(
        usuario=usuario,
        estado_cancelacion='rechazada',
        estado_reserva='cancelada'
    ):
        pago = getattr(reserva, 'pago', None)
        if pago and pago.estado_transaccion == 'aprobado':
            reserva.estado_reserva = 'confirmada'
        else:
            reserva.estado_reserva = 'pendiente'
        reserva.save(update_fields=['estado_reserva'])


def obtener_contexto_mis_reservas(usuario, estado_filtro=''):
    normalizar_estados_cancelacion_usuario(usuario)

    estado_filtro = (estado_filtro or '').strip().lower()

    # Reservas activas o en proceso de cancelación
    # Se excluyen únicamente las reservas que ya fueron efectivamente canceladas y aprobadas
    reservas_base = Reserva.objects.filter(
        usuario=usuario
    ).exclude(
        Q(estado_reserva='cancelada', estado_cancelacion='aprobada')
    )

    total_todas = reservas_base.count()
    total_pendientes = reservas_base.filter(estado_reserva='pendiente').count()
    total_confirmadas = reservas_base.filter(estado_reserva='confirmada').count()

    reservas = reservas_base
    if estado_filtro in ['pendiente', 'confirmada']:
        reservas = reservas.filter(estado_reserva=estado_filtro)

    reservas = reservas.select_related('paquete', 'paquete__categoria', 'pago').prefetch_related('paquete__actividades', 'notas_credito').order_by('-fecha_registro')

    return {
        'reservas': reservas,
        'estado_filtro': estado_filtro,
        'total_todas': total_todas,
        'total_pendientes': total_pendientes,
        'total_confirmadas': total_confirmadas,
    }


@login_required(login_url='login')
def mis_reservas_usuario(request):
    if getattr(request.user, 'es_admin', False) or request.user.is_staff or request.user.is_superuser or getattr(request.user, 'rol', None) == 'ADMIN':
        return redirect('gestion_reservas')
    estado_filtro = request.GET.get('estado', '')
    context = obtener_contexto_mis_reservas(request.user, estado_filtro)
    return render(request, 'admin/reserva/mis_reservas.html', context)


@login_required(login_url='login')
def cancelar_reserva_usuario(request, reserva_id=None, pk=None):
    """Procesa la cancelación enviada desde el modal o formulario inline, calcula la penalidad numérica y aplica políticas."""
    
    # 1. Validación de método HTTP
    if request.method != 'POST':
        return redirect('mis_reservas_usuario')

    real_id = reserva_id or pk
    reserva = get_object_or_404(Reserva, id=real_id, usuario=request.user)

    # 2. La solicitud no puede repetirse si ya está aprobada
    if reserva.estado_reserva == 'cancelada' and reserva.estado_cancelacion == 'aprobada':
        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'warning',
                    'titulo': 'Atención',
                    'mensaje': f'La reserva #{reserva.id} ya se encuentra cancelada.'
                }
            })
            return response
        messages.warning(request, "Esta reserva ya se encuentra cancelada.")
        return redirect('mis_cancelaciones')

    motivo = request.POST.get('motivo_cancelacion', '').strip()
    if not motivo:
        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'warning',
                    'titulo': 'Campo Requerido',
                    'mensaje': 'Debes ingresar un motivo válido para cancelar la reserva.'
                }
            })
            return response
        messages.error(request, "Debes ingresar un motivo válido para cancelar la reserva.")
        return redirect('mis_reservas_usuario')

    # El motivo debe ser texto real, no solo números
    if motivo.isdigit() or not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', motivo):
        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'warning',
                    'titulo': 'Motivo Inválido',
                    'mensaje': 'El motivo de cancelación debe ser un texto descriptivo, no solo números.'
                }
            })
            return response
        messages.error(request, "El motivo de cancelación debe ser un texto descriptivo, no solo números.")
        return redirect('mis_reservas_usuario')

    pago = getattr(reserva, 'pago', None)
    tiene_pago_valido = pago is not None and pago.estado_transaccion in ['pendiente', 'aprobado']

    if reserva.estado_cancelacion == 'pendiente' and tiene_pago_valido:
        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'warning',
                    'titulo': 'Solicitud en Revisión',
                    'mensaje': f'Ya tienes una solicitud de cancelación en revisión para la reserva #{reserva.id}.'
                }
            })
            return response
        messages.warning(request, "Ya tienes una solicitud de cancelación en revisión para esta reserva.")
        return redirect('mis_cancelaciones')

    # CASO A: Reserva sin pago o con comprobante rechazado -> Cancelación inmediata sin penalidad
    if not tiene_pago_valido:
        reserva.motivo_cancelacion = motivo
        reserva.penalidad = Decimal('0.00')
        reserva.estado_cancelacion = 'aprobada'
        reserva.estado_reserva = 'cancelada'
        reserva.save()

        crear_notificacion_sistema(
            usuario=request.user,
            reserva=reserva,
            mensaje=f"Cancelaste tu reserva #{reserva.id} sin pago registrado. Motivo: '{motivo}'.",
            tipo="Reserva",
            prioridad="media"
        )

        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'success',
                    'titulo': '¡Reserva Cancelada!',
                    'mensaje': f'La reserva #{reserva.id} ha sido cancelada exitosamente sin ninguna penalidad.'
                }
            })
            return response

        messages.success(
            request,
            f"La reserva #{reserva.id} ha sido cancelada exitosamente sin ninguna penalidad.",
            extra_tags='reserva'
        )
        return redirect('mis_cancelaciones')

    # CASO B: Reserva con pago registrado (pendiente o aprobado) -> Aplica cálculo de políticas y revisión
    monto_total = Decimal(reserva.monto_total or 0)
    if monto_total <= 0 and pago:
        monto_total = Decimal(getattr(pago, 'monto', 0) or 0)

    fecha_tour = getattr(reserva, 'fecha_inicio', None)
    penalidad_calculada = Decimal('0.00')
    politica_reembolso = "Sujeto a evaluación administrativa."
    dias_para_tour = None

    if fecha_tour:
        inicio_viaje = timezone.make_aware(
            datetime.combine(fecha_tour, datetime.min.time()),
            timezone.get_current_timezone()
        )
        tiempo_restante = inicio_viaje - timezone.now()

        if tiempo_restante < timedelta(hours=48):
            reserva.motivo_cancelacion = motivo
            reserva.estado_cancelacion = 'pendiente'
            reserva.save(update_fields=['motivo_cancelacion', 'estado_cancelacion'])

            if request.headers.get('HX-Request'):
                context = obtener_contexto_mis_reservas(request.user)
                response = render(request, 'admin/reserva/mis_reservas.html', context)
                response['HX-Trigger'] = json.dumps({
                    'mostrarNotificacionBitacora': {
                        'tipo': 'warning',
                        'titulo': 'Cancelación Bloqueada',
                        'mensaje': 'La cancelación no puede realizarse porque faltan menos de 48 horas para el viaje.'
                    }
                })
                return response

            messages.warning(request, 'La cancelación no puede realizarse porque faltan menos de 48 horas para el viaje.')
            return redirect('mis_reservas_usuario')

        if tiempo_restante > timedelta(days=15):
            penalidad_calculada = monto_total * Decimal('0.10')
            politica_reembolso = "Favorable (Reembolso del 90% / Penalidad del 10%)."
        else:
            penalidad_calculada = monto_total * Decimal('0.50')
            politica_reembolso = "Parcial (Reembolso del 50% / Penalidad del 50%)."

    reserva.motivo_cancelacion = motivo
    reserva.penalidad = penalidad_calculada

    if penalidad_calculada <= 0:
        reserva.estado_reserva = 'cancelada'
        reserva.estado_cancelacion = 'aprobada'
        reserva.save()

        crear_notificacion_sistema(
            usuario=request.user,
            reserva=reserva,
            mensaje=f"Tu cancelación de la reserva #{reserva.id} fue aprobada automáticamente porque no aplica penalidad. Motivo: '{motivo}'.",
            tipo="Reserva",
            prioridad="media"
        )

        if request.headers.get('HX-Request'):
            context = obtener_contexto_mis_reservas(request.user)
            response = render(request, 'admin/reserva/mis_reservas.html', context)
            response['HX-Trigger'] = json.dumps({
                'mostrarNotificacionBitacora': {
                    'tipo': 'success',
                    'titulo': '¡Cancelación Aprobada!',
                    'mensaje': f'La cancelación de la reserva #{reserva.id} fue procesada exitosamente sin penalidad.'
                }
            })
            return response

        messages.success(request, f"La cancelación de la reserva #{reserva.id} fue procesada exitosamente sin penalidad.")
        return redirect('mis_cancelaciones')

    # La reserva se marca como 'cancelada' con la solicitud 'pendiente' de revisión administrativa.
    reserva.estado_reserva = 'cancelada'
    reserva.estado_cancelacion = 'pendiente'
    reserva.save()

    crear_notificacion_sistema(
        usuario=request.user,
        reserva=reserva,
        mensaje=f"Solicitaste la cancelación de tu reserva #{reserva.id}. Motivo: '{motivo}'. Penalidad calculada: COP ${penalidad_calculada:,.0f}",
        tipo="Reserva",
        prioridad="alta"
    )

    try:
        asunto = f"Solicitud de cancelación recibida - Reserva #{reserva.id} | Monagua"
        mensaje = (
            f"Hola {request.user.get_full_name() or request.user.username},\n\n"
            f"Recibimos tu solicitud de cancelación para la reserva #{reserva.id}.\n"
            f"La reserva se encuentra en revisión administrativa.\n\n"
            f"- Motivo: {motivo}\n"
            f"- Penalidad calculada: COP ${penalidad_calculada:,.0f}\n"
            f"- Política aplicada: {politica_reembolso}\n\n"
            f"Atentamente,\nEquipo Monagua"
        )
        send_mail(asunto, mensaje, None, [request.user.email], fail_silently=True)
    except Exception:
        pass

    if request.headers.get('HX-Request'):
        context = obtener_contexto_mis_reservas(request.user)
        response = render(request, 'admin/reserva/mis_reservas.html', context)
        response['HX-Trigger'] = json.dumps({
            'mostrarNotificacionBitacora': {
                'tipo': 'info',
                'titulo': 'Solicitud Enviada',
                'mensaje': f'Tu solicitud de cancelación para la reserva #{reserva.id} está en revisión administrativa.'
            }
        })
        return response

    messages.success(request, f"Tu solicitud de cancelación para la reserva #{reserva.id} fue enviada para revisión administrativa.", extra_tags='reserva')
    return redirect('mis_cancelaciones')

@login_required(login_url='login')
def mis_cancelaciones(request):
    """
    Vista para que el usuario consulte el historial de sus cancelaciones pendientes o aprobadas.
    """
    normalizar_estados_cancelacion_usuario(request.user)

    cancelaciones = Reserva.objects.filter(
        usuario=request.user
    ).filter(
        Q(estado_cancelacion='pendiente') |
        Q(estado_cancelacion='aprobada') |
        Q(estado_cancelacion='rechazada') |
        Q(estado_reserva='cancelada', estado_cancelacion='aprobada')
    ).select_related('paquete').prefetch_related('paquete__actividades').order_by('-fecha_registro')

    context = {
        'cancelaciones': cancelaciones
    }
    return render(request, 'admin/reserva/mis_cancelaciones.html', context)

# =========================
# VISTA PÚBLICA
# =========================

@solo_turistas_requerido
def reservas_view(request):
    paquetes = Paquete.objects.all()
    paquete_id = request.GET.get('paquete_id')
    paquete = None
    if paquete_id:
        paquete = get_object_or_404(
            Paquete.objects.prefetch_related('actividades', 'tarifas__temporada', 'paquetepromocion_set__promocion'),
            id=paquete_id
        )

    context = {
        'paquetes': paquetes,
        'paquete': paquete
    }

    return render(
        request,
        'admin/reserva/reservas.html',
        context
    )


@login_required(login_url='login')
@solo_turistas_requerido
def carrito_view(request):
    return redirect('mis_reservas_usuario')


@login_required(login_url='login')
@solo_turistas_requerido
def comprobante_reserva_html(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id, usuario=request.user)
    context = {
        'reserva': reserva,
    }
    return render(request, 'usuario/reserva/comprobante_reserva.html', context)


@login_required(login_url='login')
@solo_turistas_requerido
def comprobante_multiple(request):
    if request.method != 'POST':
        return redirect('mis_reservas_usuario')

    ids = request.POST.getlist('reservas')
    if not ids:
        messages.error(request, 'Debes seleccionar al menos una reserva para continuar.')
        return redirect('mis_reservas_usuario')

    try:
        ids_int = [int(i) for i in ids]
    except ValueError:
        messages.error(request, 'Selección de reservas inválida.')
        return redirect('mis_reservas_usuario')

    reservas_qs = Reserva.objects.filter(id__in=ids_int, usuario=request.user).select_related('paquete')
    reservas = list(reservas_qs)

    if not reservas:
        messages.error(request, 'No se encontraron reservas asociadas a tu usuario.')
        return redirect('mis_reservas_usuario')

    total = sum((r.monto_total or 0) for r in reservas)

    context = {
        'reservas': reservas,
        'total': total,
    }
    return render(request, 'usuario/reserva/comprobante_multiple.html', context)


@login_required
@solo_turistas_requerido
@login_required(login_url='login')
def guardar_reserva(request, paquete_id):
    if request.method == 'POST':
        paquete = get_object_or_404(Paquete, id=paquete_id)
        fecha_viaje = request.POST.get('fecha')

        if not fecha_viaje:
            messages.error(request, "Por favor selecciona una fecha válida.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        try:
            fecha_date = datetime.strptime(fecha_viaje, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, "El formato de la fecha no es válido.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        fecha_minima = date.today() + timedelta(days=2)
        if fecha_date < fecha_minima:
            messages.error(
                request, 
                f"No es posible reservar para fechas pasadas ni con menos de 2 días de anticipación. "
                f"La fecha mínima permitida es {fecha_minima.strftime('%d/%m/%Y')}."
            )
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        tarifa = Tarifa.objects.filter(
            paquete=paquete,
            temporada__fecha_inicio__lte=fecha_date,
            temporada__fecha_fin__gte=fecha_date
        ).first()

        if not tarifa:
            messages.error(
                request, "No hay tarifas disponibles para esta fecha. Por favor elige otra.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        try:
            adultos = int(request.POST.get('adultos', 1))
            menores = int(request.POST.get('menores', 0))
        except ValueError:
            adultos, menores = 1, 0

        # --- VALIDACIONES AGREGADAS (Zero-Trust Frontend) ---
        if adultos < 1:
            messages.error(request, "Debes seleccionar al menos 1 adulto para realizar la reserva.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        if adultos > 10:
            messages.error(request, "El cupo de adultos no puede superar las 10 personas.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        if menores < 0:
            messages.error(request, "El número de menores no puede ser un valor negativo.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        if menores > 10:
            messages.error(request, "El cupo de menores no puede superar las 10 personas.")
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        ya_existe = Reserva.objects.filter(
            usuario=request.user,
            paquete=paquete,
            fecha_inicio=fecha_date
        ).exists()

        if ya_existe:
            messages.warning(
                request,
                f"Ya tienes una reserva para {paquete.nombre} en la fecha {fecha_viaje}. No se puede crear otra reserva para el mismo paquete y fecha."
            )
            return redirect(f"/reservas/reservar/?paquete_id={paquete_id}")

        reserva = Reserva.objects.create(
            usuario=request.user,
            paquete=paquete,
            fecha_inicio=fecha_date,
            numero_adultos=adultos,
            numero_menores=menores,
            estado_reserva='pendiente'
        )

        crear_notificacion_sistema(
            usuario=request.user,
            reserva=reserva,
            mensaje=f"Se ha creado tu reserva para el paquete '{paquete.nombre}'",
            tipo="Reserva",
            prioridad="media"
        )

        url_pago = request.build_absolute_uri(f"{reverse('enviar_comprobante')}?reserva_id={reserva.id}&tipo=reserva")
        url_mis_reservas = request.build_absolute_uri(reverse('mis_reservas_usuario'))

        asunto = f"¡Tu reserva #{reserva.id} está registrada! - Recuerda realizar tu pago | Monagua"
        nombre_cliente = request.user.first_name or request.user.username
        punto_encuentro = paquete.punto_encuentro or "Por definir (Sujeto a confirmación)"
        hora_encuentro = paquete.hora_encuentro.strftime('%H:%M') if paquete.hora_encuentro else "08:00"

        try:
            monto_num = float(reserva.monto_total)
            monto_txt = f"${monto_num:,.0f} COP".replace(",", ".")
        except (ValueError, TypeError):
            monto_txt = f"${reserva.monto_total} COP"

        mensaje_texto = (
            f"¡Hola, {nombre_cliente}!\n\n"
            f"Hemos recibido con éxito tu solicitud de reserva #{reserva.id} para la experiencia '{paquete.nombre}'.\n\n"
            f"DETALLES DE LA RESERVA:\n"
            f"-----------------------------------------\n"
            f"- Número de Reserva: #{reserva.id}\n"
            f"- Destino / Experiencia: {paquete.nombre}\n"
            f"- Fecha de Salida: {reserva.fecha_inicio.strftime('%d/%m/%Y')}\n"
            f"- Punto de Encuentro: {punto_encuentro}\n"
            f"- Hora de Encuentro: {hora_encuentro}\n"
            f"- Pasajeros: {reserva.numero_adultos} Adulto(s)"
            f"{f', {reserva.numero_menores} Menor(es)' if reserva.numero_menores > 0 else ''}\n"
            f"- Monto Total a Pagar: {monto_txt}\n"
            f"-----------------------------------------\n\n"
            f"⚠️ RECORDATORIO IMPORTANTE DE PAGO:\n"
            f"Tu reserva se encuentra en estado PENDIENTE DE PAGO. Para garantizar tus cupos debes "
            f"realizar el pago correspondiente y adjuntar tu comprobante en la plataforma.\n\n"
            f"🔔 ATENCIÓN: Si no realizas el pago oportunamente, el sistema cancelará y eliminará automáticamente "
            f"tu reserva para liberar los cupos disponibles a otros viajeros.\n\n"
            f"👉 Realiza tu pago y sube tu comprobante en el siguiente enlace:\n"
            f"{url_pago}\n\n"
            f"También puedes consultar y gestionar todas tus reservas en:\n"
            f"{url_mis_reservas}\n\n"
            f"Si tienes dudas o necesitas asistencia, puedes responder directamente a este correo.\n\n"
            f"¡Gracias por elegir Monagua Experiencias!"
        )

        html_bonito = plantilla_reserva_html(
            nombre_cliente=nombre_cliente,
            paquete=paquete.nombre,
            fecha=reserva.fecha_inicio.strftime('%d/%m/%Y'),  
            adultos=reserva.numero_adultos,
            menores=reserva.numero_menores,
            punto_encuentro=punto_encuentro, 
            hora_encuentro=hora_encuentro,
            estado=reserva.estado_reserva,
            reserva_id=reserva.id,
            monto_total=str(reserva.monto_total),
            url_pago=url_pago,
            url_mis_reservas=url_mis_reservas
        )
        
        # Enviar correo de confirmación en hilo en segundo plano para redirección inmediata
        threading.Thread(
            target=enviar_correo_html_monagua,
            args=(asunto, mensaje_texto, request.user.email, html_bonito),
            daemon=True
        ).start()

        messages.success(
            request, "¡Tu reserva ha sido creada exitosamente! Se ha enviado una confirmación a tu correo.", extra_tags='reserva')
        return redirect('mis_reservas_usuario')

    return redirect('reservas')


@login_required(login_url='login')
def mis_facturas(request):
    mis_confirmadas = Reserva.objects.filter(
        usuario=request.user
    ).filter(
        Q(estado_reserva='confirmada') | Q(pago__estado_transaccion='aprobado')
    ).select_related('paquete', 'pago').distinct().order_by('-id')
    
    return render(request, 'usuario/reserva/mis_facturas.html', {
        'reservas': mis_confirmadas
    })


@login_required(login_url='login')
def ver_factura(request, reserva_id):
    from django.urls import reverse
    reserva = get_object_or_404(Reserva.objects.select_related('usuario', 'paquete'), id=reserva_id)
    
    is_admin = bool(request.user.is_staff or getattr(request.user, 'es_admin', False) or getattr(request.user, 'rol', None) in [1, 'ADMIN'])
    if not is_admin and (not reserva.usuario or reserva.usuario != request.user):
        messages.error(request, "No tienes permiso para acceder a esta factura.")
        return redirect('mis_reservas_usuario')
    
    pago = getattr(reserva, 'pago', None)
    es_penalidad = reserva.estado_cancelacion == 'aprobada' and reserva.penalidad and reserva.penalidad > 0
    if pago and getattr(pago, 'estado_transaccion', None) == 'aprobado' and reserva.estado_reserva != 'confirmada' and not es_penalidad:
        reserva.estado_reserva = 'confirmada'
        reserva.save(update_fields=['estado_reserva'])

    if reserva.estado_reserva != 'confirmada':
        messages.error(request, "La factura solo está disponible para reservas confirmadas y pagadas.")
        return redirect('admin_comprobantes' if is_admin else 'mis_reservas_usuario')
        
    metodo_pago = (pago.banco_origen or pago.metodo_pago) if pago else "Transferencia Bancaria"
    
    abs_url = request.build_absolute_uri(reverse('ver_factura', args=[reserva.id]))
    qr_base64 = get_qr_base64(abs_url)
    
    logo_base64 = get_image_base64('static/img/logo_monagua.webp')
    
    cliente_nombre = reserva.nombre_cliente
    cliente_email = reserva.email_cliente
    
    context = {
        'reserva_id': reserva.id,
        'nro_factura': f"FAC-1000{reserva.id}",
        'cliente_nombre': cliente_nombre or 'Cliente',
        'cliente_email': cliente_email or '',
        'fecha_emision': reserva.fecha_registro.strftime('%d/%m/%Y') if hasattr(reserva, 'fecha_registro') and reserva.fecha_registro else (reserva.fecha_inicio.strftime('%d/%m/%Y') if reserva.fecha_inicio else ''),
        'metodo_pago': metodo_pago,
        'paquete_nombre': reserva.paquete.nombre if reserva.paquete else 'Aventura Mongua',
        'subtotal': reserva.monto_total,
        'total': reserva.monto_total,
        'logo_base64': logo_base64,
        'qr_base64': qr_base64,
    }
    return render(request, 'usuario/reserva/factura.html', context)


@login_required(login_url='login')
def descargar_factura(request, reserva_id):
    reserva = get_object_or_404(Reserva.objects.select_related('usuario', 'paquete'), id=reserva_id)
    
    is_admin = bool(request.user.is_staff or getattr(request.user, 'es_admin', False) or getattr(request.user, 'rol', None) in [1, 'ADMIN'])
    if not is_admin and (not reserva.usuario or reserva.usuario != request.user):
        messages.error(request, "No tienes permiso para descargar esta factura.")
        return redirect('mis_reservas_usuario')
    
    pago = getattr(reserva, 'pago', None)
    if pago and getattr(pago, 'estado_transaccion', None) == 'aprobado' and reserva.estado_reserva != 'confirmada':
        reserva.estado_reserva = 'confirmada'
        reserva.save(update_fields=['estado_reserva'])

    if reserva.estado_reserva != 'confirmada':
        messages.error(request, "La factura solo se puede descargar para reservas confirmadas.")
        return redirect('admin_comprobantes' if is_admin else 'mis_reservas_usuario')
        
    password = None if is_admin else (getattr(reserva.usuario, 'numero_documento', None) if reserva.usuario else getattr(reserva, 'cliente_documento', None))
    if password:
        password = str(password).strip()
        
    try:
        pdf_bytes = generar_factura_pdf_bytes(reserva, request=request, password=password)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="factura_FAC-1000{reserva.id}.pdf"'
        return response
    except Exception as e:
        logger.error(f"Error al descargar la factura PDF para la reserva {reserva.id}: {e}", exc_info=True)
        messages.error(request, "Hubo un inconveniente al generar la factura en PDF. Por favor intenta nuevamente.")
        messages.error(request, "Hubo un inconveniente al generar la factura en PDF. Por favor intenta nuevamente.")
        return redirect('ver_factura', reserva_id=reserva.id)

@requiere_administrador
def listar_cancelaciones_admin(request):
    """Listado y filtrado de solicitudes de cancelación."""


    cancelaciones = Reserva.objects.filter(
        estado_cancelacion__in=['pendiente', 'aprobada', 'rechazada']
    ).select_related('usuario', 'paquete').prefetch_related('paquete__actividades').order_by('-id')

    estado_seleccionado = request.GET.get('estado', '')


    if estado_seleccionado in ['pendiente', 'aprobada', 'rechazada']:
        if estado_seleccionado == 'aprobada':
            cancelaciones = cancelaciones.filter(estado_cancelacion='aprobada')
        else:
            cancelaciones = cancelaciones.filter(estado_cancelacion__iexact=estado_seleccionado)

 
    stats = Reserva.objects.filter(
        estado_cancelacion__in=['pendiente', 'aprobada', 'rechazada']
    ).aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado_cancelacion__iexact='pendiente')),
        aprobadas=Count('id', filter=Q(estado_cancelacion__iexact='aprobada')),
        rechazadas=Count('id', filter=Q(estado_cancelacion__iexact='rechazada'))
    )

    stats_list = [
        ('Total', stats['total'], 'text-dark'),
        ('Pendientes', stats['pendientes'], 'text-warning'),
        ('Aprobadas', stats['aprobadas'], 'text-success'),
        ('Rechazadas', stats['rechazadas'], 'text-danger'),
    ]

    context = {
        'cancelaciones': cancelaciones,
        'stats_list': stats_list,
        'estado_seleccionado': estado_seleccionado,
    }
    context.update(stats)

    return render(request, 'admin/reserva/cancelaciones_admin.html', context)

@requiere_administrador
def editar_cancelacion_admin(request, reserva_id):
    """
    Vista administrativa para revisar la cancelación de una Reserva.
    Calcula automáticamente la penalidad y el reembolso según las políticas oficiales
    del proyecto (anticipación de la reserva y reglas de negocio de Monagua).
    """
    reserva = get_object_or_404(
        Reserva.objects.select_related('usuario', 'paquete', 'pago').prefetch_related('reembolsos'),
        id=reserva_id
    )

    reembolso = reserva.reembolsos.order_by('-fecha_solicitud').first()
    pago = getattr(reserva, 'pago', None)

    # Evaluación 100% automática según las políticas oficiales del proyecto Monagua
    politica = reserva.evaluar_politica_cancelacion()
    monto_pagado = politica['monto_pagado']
    penalidad_automatica = politica['penalidad']
    monto_reembolso_automatico = politica['reembolso']

    if request.method == 'POST':
        if reserva.estado_cancelacion == 'aprobada':
            messages.warning(request, "Esta cancelación ya fue aprobada formalmente y no puede ser modificada.")
            return redirect('editar_cancelacion_admin', reserva_id=reserva.id)

        estado = request.POST.get('estado_cancelacion')
        motivo_resolucion = (request.POST.get('motivo_resolucion_cancelacion') or '').strip()
        estado_reembolso = (request.POST.get('estado_reembolso') or '').strip()
        banco_reembolso = (request.POST.get('banco_reembolso') or '').strip()
        referencia_reembolso = (request.POST.get('referencia_reembolso') or '').strip()
        if estado not in {'pendiente', 'aprobada', 'rechazada'}:
            messages.error(request, "El estado de cancelación no es válido.")
            return redirect('editar_cancelacion_admin', reserva_id=reserva.id)
        if estado == 'rechazada' and len(motivo_resolucion) < 5:
            messages.error(request, "Debes indicar un motivo válido para rechazar la solicitud de cancelación.")
            return redirect('editar_cancelacion_admin', reserva_id=reserva.id)

        nota_admin = request.POST.get('nota_admin', '').strip()

        estado_anterior = reserva.estado_cancelacion
        reserva.estado_cancelacion = estado
        reserva.penalidad = penalidad_automatica

        if estado == 'aprobada':
            reserva.estado_reserva = 'cancelada'

            # Gestión o actualización del Reembolso si aplica devolución
            if monto_reembolso_automatico > 0 and pago:
                if not reembolso:
                    reembolso = Reembolso.objects.create(
                        reserva=reserva,
                        usuario=reserva.usuario,
                        pago_asociado=pago,
                        monto_total_reserva=monto_pagado,
                        penalidad_aplicada=penalidad_automatica,
                        monto_reembolsado=monto_reembolso_automatico,
                        motivo=reserva.motivo_cancelacion or 'Cancelación aprobada'
                    )
                else:
                    reembolso.monto_total_reserva = monto_pagado
                    reembolso.penalidad_aplicada = penalidad_automatica
                    reembolso.monto_reembolsado = monto_reembolso_automatico
                    reembolso.pago_asociado = pago

                # Si el administrador adjuntó la captura de transferencia bancaria
                if 'imagen_comprobante' in request.FILES:
                    valido, err = validar_archivo_subido(request.FILES['imagen_comprobante'], validar_comprobante_pago)
                    if not valido:
                        messages.error(request, err)
                        return redirect('gestionar_cancelacion_admin', reserva_id=reserva.id)
                    reembolso.imagen_comprobante = request.FILES['imagen_comprobante']
                    reembolso.banco_emisor = request.POST.get('banco_emisor', '').strip() or reembolso.banco_emisor
                    reembolso.banco_destino = request.POST.get('banco_destino', '').strip() or reembolso.banco_destino
                    reembolso.cuenta_o_telefono = request.POST.get('cuenta_o_telefono', '').strip() or reembolso.cuenta_o_telefono
                    reembolso.referencia_transferencia = request.POST.get('referencia_transferencia', '').strip() or reembolso.referencia_transferencia
                    reembolso.notas_admin = nota_admin or reembolso.notas_admin
                    reembolso.estado = 'completado'
                    reembolso.fecha_reembolso = timezone.now()
                    reembolso.gestionado_por = request.user
                    reembolso.save()
                else:
                    reembolso.banco_emisor = request.POST.get('banco_emisor', '').strip() or reembolso.banco_emisor
                    reembolso.banco_destino = request.POST.get('banco_destino', '').strip() or reembolso.banco_destino
                    reembolso.cuenta_o_telefono = request.POST.get('cuenta_o_telefono', '').strip() or reembolso.cuenta_o_telefono
                    reembolso.referencia_transferencia = request.POST.get('referencia_transferencia', '').strip() or reembolso.referencia_transferencia
                    reembolso.notas_admin = nota_admin or reembolso.notas_admin
                    if reembolso.estado != 'completado':
                        reembolso.estado = 'pendiente'
                    reembolso.gestionado_por = request.user
                    reembolso.save()

            elif monto_reembolso_automatico <= 0 and reembolso:
                reembolso.estado = 'rechazado'
                reembolso.penalidad_aplicada = penalidad_automatica
                reembolso.monto_reembolsado = Decimal('0.00')
                reembolso.notas_admin = nota_admin
                reembolso.save()

        elif estado == 'rechazada':
            if reserva.estado_reserva == 'cancelada':
                if pago and pago.estado_transaccion == 'aprobado':
                    reserva.estado_reserva = 'confirmada'
                else:
                    reserva.estado_reserva = 'pendiente'
            if reembolso and reembolso.estado == 'pendiente':
                reembolso.estado = 'rechazado'
                reembolso.notas_admin = nota_admin
                reembolso.save()

        if estado_reembolso in {'nota_credito', 'pagado'}:
            if reserva.monto_reembolsable <= 0:
                messages.error(request, "Esta reserva no tiene un monto reembolsable.")
                return redirect('editar_cancelacion_admin', reserva_id=reserva.id)
            reserva.estado_reembolso = estado_reembolso
            if estado_reembolso == 'nota_credito':
                reserva.banco_reembolso = ''
                reserva.referencia_reembolso = ''
                reserva.fecha_reembolso = timezone.now()
            else:
                if not banco_reembolso or not referencia_reembolso:
                    messages.error(request, "Para registrar un reembolso pagado debes indicar banco y referencia.")
                    return redirect('editar_cancelacion_admin', reserva_id=reserva.id)
                reserva.banco_reembolso = banco_reembolso
                reserva.referencia_reembolso = referencia_reembolso
                reserva.fecha_reembolso = timezone.now()

        reserva.save()

        # Notificación y Correo al usuario
        if reserva.usuario and (estado_anterior != estado or nota_admin or 'imagen_comprobante' in request.FILES):
            detalle_reembolso = ""
            if estado == 'aprobada':
                if monto_reembolso_automatico > 0:
                    if reembolso and reembolso.estado == 'completado':
                        detalle_reembolso = f" Se realizó el reembolso bancario de COP ${monto_reembolso_automatico:,.0f} con comprobante disponible."
                    else:
                        detalle_reembolso = f" Se programó el reembolso bancario de COP ${monto_reembolso_automatico:,.0f} en estado pendiente de transferencia."
                else:
                    detalle_reembolso = " No aplica reembolso debido a la penalidad del 100% calculada por política."
            elif estado == 'rechazada':
                detalle_reembolso = " Tu itinerario y reserva continúan vigentes."

            nota_texto = f" Mensaje del equipo: '{nota_admin}'" if nota_admin else ""
            mensaje_notif = f"La solicitud de cancelación de tu reserva #{reserva.id} fue '{estado}'.{detalle_reembolso}{nota_texto}"

            crear_notificacion_sistema(
                usuario=reserva.usuario,
                reserva=reserva,
                mensaje=mensaje_notif,
                tipo="Reserva",
                prioridad="alta"
            )

            asunto = f"Resolución de Cancelación - Reserva #{reserva.id} | Monagua"
            mensaje_texto = (
                f"Hola {reserva.usuario.get_full_name() or reserva.usuario.username},\n\n"
                f"La solicitud de cancelación de tu reserva #{reserva.id} ha sido '{estado}'.\n"
                f"{detalle_reembolso}\n"
                f"{nota_texto}\n\n"
                f"Puedes ingresar a tu panel de usuario para consultar los detalles y comprobantes de reembolso."
            )
            html_respuesta = plantilla_cancelacion_html(
                nombre_cliente=reserva.usuario.get_full_name() or reserva.usuario.username,
                paquete=reserva.paquete.nombre if reserva.paquete else 'Paquete',
                estado=estado,
                penalidad=f"{penalidad_automatica:,.0f}"
            )
            try:
                enviar_correo_html_monagua(asunto, mensaje_texto, reserva.usuario.email, html_respuesta)
            except Exception as exc:
                logger.error(f"Error enviando correo de cancelación: {exc}")

        messages.success(request, f"La cancelación de la reserva #{reserva.id} fue actualizada con éxito.")
        return redirect('listar_cancelaciones')

    monto_reembolsable_preview = max((reserva.monto_total or 0) - (reserva.penalidad or 0), 0)
    pago = getattr(reserva, 'pago', None)
    penalidad_pagada = bool(
        pago
        and pago.estado_transaccion == 'aprobado'
        and reserva.penalidad
        and reserva.penalidad > 0
        and pago.monto >= reserva.penalidad
    )

    return render(request, 'admin/reserva/editar_cancelacion_admin.html', {
        'reserva': reserva,
        'reembolso': reembolso,
        'pago': pago,
        'monto_pagado': monto_pagado,
        'politica': politica,
        'penalidad_actual': penalidad_automatica,
        'monto_reembolsar_actual': monto_reembolso_automatico,
    })


@requiere_administrador
def listar_reembolsos_admin(request):
    """
    Vista administrativa para listar, supervisar y auditar los reembolsos bancarios a turistas.
    Permite auditar el estado del desembolso y los comprobantes de transferencia.
    """
    estado_filtro = request.GET.get('estado', '').strip().lower()
    busqueda = request.GET.get('q', '').strip()

    reembolsos = Reembolso.objects.select_related(
        'reserva', 'usuario', 'pago_asociado', 'reserva__paquete', 'gestionado_por'
    ).order_by('-fecha_solicitud')

    if estado_filtro in ['pendiente', 'completado', 'rechazado']:
        reembolsos = reembolsos.filter(estado=estado_filtro)

    if busqueda:
        reembolsos = reembolsos.filter(
            Q(usuario__first_name__icontains=busqueda) |
            Q(usuario__last_name__icontains=busqueda) |
            Q(usuario__username__icontains=busqueda) |
            Q(usuario__email__icontains=busqueda) |
            Q(referencia_transferencia__icontains=busqueda) |
            Q(reserva__id__icontains=busqueda)
        )

    stats = Reembolso.objects.aggregate(
        total=Count('id'),
        pendientes=Count('id', filter=Q(estado='pendiente')),
        completados=Count('id', filter=Q(estado='completado')),
        monto_total_reembolsado=Sum('monto_reembolsado', filter=Q(estado='completado'))
    )

    context = {
        'reembolsos': reembolsos,
        'estado_filtro': estado_filtro,
        'busqueda': busqueda,
        'total': stats['total'] or 0,
        'pendientes': stats['pendientes'] or 0,
        'completados': stats['completados'] or 0,
        'monto_total_reembolsado': stats['monto_total_reembolsado'] or Decimal('0.00'),
    }
    return render(request, 'admin/reserva/reembolsos_admin.html', context)


@requiere_administrador
def registrar_reembolso_admin(request, reembolso_id):
    """
    Registra el desembolso bancario completado de un reembolso, adjuntando
    la captura del comprobante bancario de pago (Nequi, Daviplata, Bancolombia, etc.).
    """
    reembolso = get_object_or_404(
        Reembolso.objects.select_related('reserva', 'usuario'),
        id=reembolso_id
    )

    if request.method == 'POST':
        if reembolso.estado == 'completado':
            messages.warning(request, "Este reembolso ya fue completado y su comprobante bancario no puede ser modificado.")
            return redirect('listar_reembolsos_admin')

        if 'imagen_comprobante' in request.FILES:
            valido, err = validar_archivo_subido(request.FILES['imagen_comprobante'], validar_comprobante_pago)
            if not valido:
                messages.error(request, err)
                return redirect('listar_reembolsos_admin')
            reembolso.imagen_comprobante = request.FILES['imagen_comprobante']

        reembolso.banco_emisor = request.POST.get('banco_emisor', '').strip() or reembolso.banco_emisor
        reembolso.banco_destino = request.POST.get('banco_destino', '').strip() or reembolso.banco_destino
        reembolso.cuenta_o_telefono = request.POST.get('cuenta_o_telefono', '').strip() or reembolso.cuenta_o_telefono
        reembolso.referencia_transferencia = request.POST.get('referencia_transferencia', '').strip() or reembolso.referencia_transferencia
        reembolso.notas_admin = request.POST.get('notas_admin', '').strip() or reembolso.notas_admin
        reembolso.estado = 'completado'
        reembolso.fecha_reembolso = timezone.now()
        reembolso.gestionado_por = request.user
        reembolso.save()

        # Notificar al turista
        mensaje = (
            f"¡Tu reembolso de COP ${reembolso.monto_reembolsado:,.0f} por la reserva #{reembolso.reserva_id} "
            f"ha sido transferido exitosamente! Ya puedes ver el comprobante en 'Mis Reembolsos'."
        )
        crear_notificacion_sistema(
            usuario=reembolso.usuario,
            reserva=reembolso.reserva,
            mensaje=mensaje,
            tipo="Reserva",
            prioridad="alta"
        )

        asunto = f"Reembolso transferido - Reserva #{reembolso.reserva_id} | Monagua"
        mensaje_email = (
            f"Hola {reembolso.usuario.get_full_name() or reembolso.usuario.username},\n\n"
            f"Te confirmamos que se ha realizado la transferencia de tu reembolso por un valor de "
            f"COP ${reembolso.monto_reembolsado:,.0f} correspondiente a la reserva #{reembolso.reserva_id}.\n\n"
            f"Banco emisor: {reembolso.banco_emisor or 'Monagua'}\n"
            f"Referencia de transferencia: {reembolso.referencia_transferencia or 'N/A'}\n\n"
            f"Puedes ingresar a tu cuenta de Monagua en 'Mis Reembolsos' para visualizar la captura del comprobante."
        )
        try:
            enviar_correo_html_monagua(
                asunto,
                mensaje_email,
                reembolso.usuario.email,
                f"<div style='font-family: sans-serif; padding: 20px;'><h2>Reembolso Efectuado</h2><p>{mensaje_email.replace(chr(10), '<br>')}</p></div>"
            )
        except Exception as exc:
            logger.error(f"Error enviando correo de reembolso: {exc}")

        messages.success(request, f"El comprobante de reembolso #{reembolso.id} fue registrado con éxito.")
        return redirect('listar_reembolsos_admin')

    return redirect('listar_reembolsos_admin')


@login_required(login_url='login')
def mis_reembolsos_usuario(request):
    """
    Vista para que el turista consulte sus reembolsos tramitados, verifique el estado
    de desembolso, consulte el comprobante de transferencia bancaria y radique PQRS si lo requiere.
    """
    reembolsos = Reembolso.objects.filter(
        usuario=request.user
    ).select_related(
        'reserva', 'reserva__paquete', 'pago_asociado'
    ).order_by('-fecha_solicitud')

    total_reembolsado = reembolsos.filter(estado='completado').aggregate(
        total=Sum('monto_reembolsado')
    )['total'] or Decimal('0.00')

    pendientes_count = reembolsos.filter(estado='pendiente').count()

    context = {
        'reembolsos': reembolsos,
        'total_reembolsado': total_reembolsado,
        'pendientes_count': pendientes_count,
    }
    return render(request, 'usuario/reserva/mis_reembolsos.html', context)


@login_required(login_url='login')
@solo_turistas_requerido
def modificar_personas_reserva(request, reserva_id):
    if request.method != 'POST':
        return redirect('mis_reservas_usuario')

    with transaction.atomic():
        reserva = Reserva.objects.select_for_update().select_related('paquete').get(
            id=reserva_id,
            usuario=request.user
        )

        if not reserva.puede_modificar_personas():
            messages.error(request, 'No puedes modificar personas: la reserva está cancelada, tiene pago registrado o faltan menos de 48 horas.')
            return redirect('mis_reservas_usuario')

        try:
            adultos = int(request.POST.get('adultos', 0))
            menores = int(request.POST.get('menores', 0))
        except (TypeError, ValueError):
            messages.error(request, 'Los números de adultos y menores no son válidos.')
            return redirect('mis_reservas_usuario')

        if adultos < 1:
            messages.error(request, 'Debe haber al menos 1 adulto en la reserva.')
            return redirect('mis_reservas_usuario')
        if menores < 0:
            messages.error(request, 'El número de menores no puede ser negativo.')
            return redirect('mis_reservas_usuario')
        if adultos > 10:
            messages.error(request, 'El cupo de adultos no puede superar las 10 personas.')
            return redirect('mis_reservas_usuario')
        if menores > 10:
            messages.error(request, 'El cupo de menores no puede superar las 10 personas.')
            return redirect('mis_reservas_usuario')

        adultos_anteriores = reserva.numero_adultos
        menores_anteriores = reserva.numero_menores
        monto_anterior = reserva.monto_total

        reserva.numero_adultos = adultos
        reserva.numero_menores = menores
        reserva.recalcular_monto()
        reserva.save(update_fields=['numero_adultos', 'numero_menores', 'monto_total'])

        ModificacionReserva.objects.create(
            reserva=reserva,
            usuario=request.user,
            adultos_anteriores=adultos_anteriores,
            adultos_nuevos=adultos,
            menores_anteriores=menores_anteriores,
            menores_nuevos=menores,
            monto_anterior=monto_anterior,
            monto_nuevo=reserva.monto_total,
            motivo='Modificación realizada por el turista antes del pago.',
            realizado_por_admin=False
        )

    messages.success(request, 'La cantidad de personas fue modificada correctamente.', extra_tags='reserva')
    return redirect('mis_reservas_usuario')


@login_required(login_url='login')
@solo_turistas_requerido
def reducir_personas_reserva_pagada(request, reserva_id):
    """
    Permite al usuario reducir personas en una reserva ya pagada (cancelación parcial)
    sin cancelar toda la reserva, aplicando la política escalonada de anticipación,
    liberando cupos, procesando reembolso parcial o saldo a favor y emitiendo NotaCredito
    vinculada al pago original (manteniendo intacto el comprobante original).
    """
    if request.method != 'POST':
        return redirect('mis_reservas_usuario')

    with transaction.atomic():
        reserva = Reserva.objects.select_for_update().select_related('paquete', 'pago', 'usuario').filter(
            id=reserva_id,
            usuario=request.user
        ).first()

        if not reserva:
            messages.error(request, 'No se encontró la reserva solicitada.')
            return redirect('mis_reservas_usuario')

        if not reserva.puede_reducir_personas_pagada():
            messages.error(
                request,
                'Esta reserva no cumple las condiciones para reducción parcial (debe estar pagada y aprobada, activa, con más de 1 persona y anterior a la fecha del viaje).'
            )
            return redirect('mis_reservas_usuario')

        try:
            adultos = int(request.POST.get('adultos', 0))
            menores = int(request.POST.get('menores', 0))
        except (TypeError, ValueError):
            messages.error(request, 'Los números de adultos y menores no son válidos.')
            return redirect('mis_reservas_usuario')

        modalidad = (request.POST.get('modalidad') or '').strip().lower()
        if modalidad not in ('reembolso', 'credito'):
            messages.error(request, 'Debes elegir entre reembolso parcial al método original o saldo a favor.')
            return redirect('mis_reservas_usuario')

        if adultos < 1:
            messages.error(request, 'Debe permanecer al menos 1 adulto en la reserva. Si nadie asistirá, usa la opción de cancelación total.')
            return redirect('mis_reservas_usuario')
        if menores < 0:
            messages.error(request, 'El número de menores no puede ser negativo.')
            return redirect('mis_reservas_usuario')
        if adultos > reserva.numero_adultos or menores > reserva.numero_menores:
            messages.error(request, 'En una reserva ya pagada solo puedes reducir la cantidad de adultos o menores, no aumentarla.')
            return redirect('mis_reservas_usuario')

        adultos_anteriores = reserva.numero_adultos
        menores_anteriores = reserva.numero_menores
        cupos_liberados = (adultos_anteriores + menores_anteriores) - (adultos + menores)

        if cupos_liberados <= 0:
            messages.warning(request, 'Debes reducir al menos 1 persona para aplicar una cancelación parcial.')
            return redirect('mis_reservas_usuario')

        politica = reserva.evaluar_politica_reduccion()
        monto_anterior = Decimal(reserva.monto_total or Decimal('0.00'))
        monto_nuevo = reserva.calcular_monto_para_personas(adultos, menores)
        diferencia_bruta = max((monto_anterior - monto_nuevo).quantize(Decimal('0.01')), Decimal('0.00'))

        porcentaje_penalidad = politica['porcentaje_penalidad']
        monto_penalidad = (diferencia_bruta * porcentaje_penalidad / Decimal('100')).quantize(Decimal('0.01'))
        monto_devuelto = (diferencia_bruta - monto_penalidad).quantize(Decimal('0.01'))

        motivo_usuario = (request.POST.get('motivo') or '').strip()
        motivo_final = motivo_usuario or f"Reducción parcial de {adultos_anteriores + menores_anteriores} a {adultos + menores} persona(s) ({politica['tramo']})."

        # Actualizar la reserva liberando los cupos automáticamente (sin tocar el Pago original)
        reserva.numero_adultos = adultos
        reserva.numero_menores = menores
        reserva.monto_total = monto_nuevo
        reserva.save(update_fields=['numero_adultos', 'numero_menores', 'monto_total'])

        modificacion = ModificacionReserva.objects.create(
            reserva=reserva,
            usuario=request.user,
            adultos_anteriores=adultos_anteriores,
            adultos_nuevos=adultos,
            menores_anteriores=menores_anteriores,
            menores_nuevos=menores,
            monto_anterior=monto_anterior,
            monto_nuevo=monto_nuevo,
            motivo=motivo_final,
            realizado_por_admin=False
        )

        if monto_devuelto <= Decimal('0.00'):
            estado_nota = 'sin_reembolso'
        elif modalidad == 'credito':
            estado_nota = 'procesada'
            usuario_locked = Usuario.objects.select_for_update().get(pk=request.user.pk)
            usuario_locked.saldo_favor = (usuario_locked.saldo_favor or Decimal('0.00')) + monto_devuelto
            usuario_locked.save(update_fields=['saldo_favor'])
        else:
            estado_nota = 'pendiente_reembolso'

        nota_credito = NotaCredito.objects.create(
            reserva=reserva,
            pago_original=reserva.pago,
            modificacion=modificacion,
            usuario=request.user,
            modalidad=modalidad,
            estado=estado_nota,
            cupos_liberados=cupos_liberados,
            monto_bruto_diferencia=diferencia_bruta,
            porcentaje_penalidad=porcentaje_penalidad,
            monto_penalidad=monto_penalidad,
            monto_devuelto=monto_devuelto,
            politica_aplicada=politica['descripcion'],
            motivo=motivo_final,
        )

        # Notificar al turista
        if estado_nota == 'procesada':
            detalle_dinero = f"Se acreditaron COP ${monto_devuelto:,.0f} a tu saldo a favor."
        elif estado_nota == 'pendiente_reembolso':
            detalle_dinero = f"Se solicitó reembolso parcial por COP ${monto_devuelto:,.0f} a tu método de pago original."
        else:
            detalle_dinero = "No aplica reembolso según la política de anticipación (<24h)."

        crear_notificacion_sistema(
            usuario=request.user,
            reserva=reserva,
            mensaje=f"Cancelación parcial aplicada en reserva #{reserva.id} (Nota de Crédito {nota_credito.codigo}): se liberaron {cupos_liberados} cupo(s). {detalle_dinero}",
            tipo="Reserva",
            prioridad="alta"
        )

        # Notificar a administradores
        for admin_user in Usuario.objects.filter(Q(is_staff=True) | Q(rol=Usuario.Roles.ADMIN), is_active=True):
            crear_notificacion_sistema(
                usuario=admin_user,
                reserva=reserva,
                mensaje=f"El usuario {request.user.username} redujo la reserva #{reserva.id} en {cupos_liberados} cupo(s) ({nota_credito.codigo} — {nota_credito.get_modalidad_display()}: COP ${monto_devuelto:,.0f}).",
                tipo="Reserva",
                prioridad="media"
            )

    messages.success(
        request,
        f"Reserva actualizada a {adultos} adulto(s) y {menores} menor(es). Se liberaron {cupos_liberados} cupo(s) y se generó la Nota de Crédito {nota_credito.codigo}. {detalle_dinero}",
        extra_tags='reserva'
    )
    return redirect('mis_reservas_usuario')


@login_required(login_url='login')
def ver_nota_credito(request, nota_id):
    """Muestra el comprobante de Nota de Crédito vinculado al pago original."""
    nota = get_object_or_404(
        NotaCredito.objects.select_related('reserva', 'reserva__paquete', 'pago_original', 'usuario', 'modificacion'),
        id=nota_id
    )
    es_admin = request.user.is_staff or getattr(request.user, 'es_admin', False)
    if nota.usuario_id != request.user.id and not es_admin:
        messages.error(request, 'No tienes permisos para ver esta nota de crédito.')
        return redirect('mis_reservas_usuario')

    return render(request, 'usuario/reserva/nota_credito.html', {
        'nota': nota,
    })
