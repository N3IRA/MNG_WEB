from App.forms.temporada.forms import TemporadaForm
from django.db.models import Count, Q
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from App.models import Temporada, Tarifa
from App.utils import crear_notificacion_sistema
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from datetime import datetime, timedelta
from django.utils import timezone


# Create your views here.
class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para asegurar que solo usuarios autenticados con permisos
    de staff/administrador puedan acceder a las vistas administrativas.
    """
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff

class TemporadaListView(StaffRequiredMixin, ListView):
    model = Temporada
    template_name = 'admin/temporada/temporada.html'
    context_object_name = 'temporadas'

    def get_queryset(self):
        queryset = Temporada.objects.all()
        fecha_inicio = self.request.GET.get("fecha_inicio", "").strip()
        fecha_fin = self.request.GET.get("fecha_fin", "").strip()

      
        if fecha_inicio:
            try:
                f_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha_inicio__gte=f_inicio)
            except ValueError:
                pass

        if fecha_fin:
            try:
                f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                queryset = queryset.filter(fecha_fin__lte=f_fin)
            except ValueError:
                pass

        return queryset.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        hoy = timezone.localdate()
        stats = Temporada.objects.aggregate(
            total=Count('id'),
            activas=Count('id', filter=Q(estado=True)),
            inactivas=Count('id', filter=Q(estado=False)),
            programadas=Count('id', filter=Q(fecha_inicio__gt=hoy)),
            finalizadas=Count('id', filter=Q(fecha_fin__lt=hoy))
        )

        context.update(stats)

        context['stats_list'] = [
            ('Total Temporadas', stats['total'], 'text-dark'),
            ('Activas', stats['activas'], 'text-success'),
            ('Inactivas', stats['inactivas'], 'text-danger'),
        ]


        return context
class TemporadaCreateView(StaffRequiredMixin, CreateView):
    model = Temporada
    form_class = TemporadaForm
    template_name = 'admin/temporada/agregar_temporada.html'
    success_url = reverse_lazy('listar_temporadas')

    def form_valid(self, form):
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        hoy = timezone.localdate()
        limite_minimo_inicio = hoy - timedelta(days=7)

        if fecha_inicio and fecha_inicio < limite_minimo_inicio:
            form.add_error('fecha_inicio', f"La fecha de inicio no puede ser anterior a una semana antes de la fecha actual ({limite_minimo_inicio.strftime('%d/%m/%Y')}).")
            return self.form_invalid(form)

        if fecha_fin and fecha_fin <= hoy:
            form.add_error('fecha_fin', f"La fecha de finalización no puede ser anterior ni el mismo día que hoy ({hoy.strftime('%d/%m/%Y')}). Debe ser posterior a la fecha actual.")
            return self.form_invalid(form)

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            form.add_error('fecha_fin', "La fecha de finalización no puede ser anterior ni igual a la fecha de inicio.")
            return self.form_invalid(form)

        response = super().form_valid(form)
        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha creado una nueva temporada: '{self.object.nombre}' con fecha de inicio {self.object.fecha_inicio} y fecha de fin {self.object.fecha_fin}.",
            tipo="Temporada",
            prioridad="media",
        )
        messages.success(self.request, f"Temporada '{self.object.nombre}' creada exitosamente.", extra_tags='temporada')
        return response


class TemporadaUpdateView(StaffRequiredMixin, UpdateView):
    model = Temporada
    form_class = TemporadaForm
    template_name = 'admin/temporada/editar_temporada.html'
    success_url = reverse_lazy('listar_temporadas')

    def form_valid(self, form):
        fecha_inicio = form.cleaned_data.get('fecha_inicio')
        fecha_fin = form.cleaned_data.get('fecha_fin')
        hoy = timezone.localdate()
        limite_minimo_inicio = hoy - timedelta(days=7)

        if fecha_inicio and self.object.fecha_inicio != fecha_inicio and fecha_inicio < limite_minimo_inicio:
            form.add_error('fecha_inicio', f"No puedes modificar la fecha de inicio a una fecha anterior a una semana antes de hoy ({limite_minimo_inicio.strftime('%d/%m/%Y')}).")
            return self.form_invalid(form)

        if fecha_fin and self.object.fecha_fin != fecha_fin and fecha_fin <= hoy:
            form.add_error('fecha_fin', f"No puedes modificar la fecha de finalización a una fecha anterior o igual a hoy ({hoy.strftime('%d/%m/%Y')}). Debe ser posterior a la fecha actual.")
            return self.form_invalid(form)

        if fecha_inicio and fecha_fin and fecha_fin <= fecha_inicio:
            form.add_error('fecha_fin', "La fecha de finalización no puede ser anterior ni igual a la fecha de inicio.")
            return self.form_invalid(form)

        temp_antigua = self.get_object()
        valor_viejo = f"Nombre: {temp_antigua.nombre}, Inicio: {temp_antigua.fecha_inicio}, Fin: {temp_antigua.fecha_fin}, Estado: {temp_antigua.estado}"

        response = super().form_valid(form)

        valor_nuevo = f"Nombre: {self.object.nombre}, Inicio: {self.object.fecha_inicio}, Fin: {self.object.fecha_fin}, Estado: {self.object.estado}"

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha editado la temporada '{self.object.nombre}'. Detalles previos: {valor_viejo}. Nuevos detalles: {valor_nuevo}.",
            tipo="Temporada",
            prioridad="media",
        )
        messages.success(self.request, f"Temporada '{self.object.nombre}' actualizada exitosamente.", extra_tags='temporada')
        return response


@login_required(login_url='login')
@require_POST
def toggle_estado_temporada(request, pk):
    """Alterna el estado Activa/Inactiva de una temporada (solo staff)."""
    if not (request.user.is_active and request.user.is_staff):
        messages.error(request, "No tienes permisos para cambiar el estado de las temporadas.")
        return redirect('index')

    temporada = get_object_or_404(Temporada, pk=pk)
    temporada.estado = not temporada.estado
    temporada.save(update_fields=['estado'])

    estado_texto = "activada" if temporada.estado else "inactivada"
    crear_notificacion_sistema(
        usuario=request.user,
        mensaje=f"Se ha {estado_texto} la temporada: '{temporada.nombre}'.",
        tipo="Temporada",
        prioridad="media"
    )
    messages.success(request, f"La temporada '{temporada.nombre}' ha sido {estado_texto} correctamente.", extra_tags='temporada')
    return redirect('listar_temporadas')


class TemporadaDeleteView(StaffRequiredMixin, DeleteView):
    model = Temporada
    template_name = 'admin/temporada/eliminar_temporada.html'
    success_url = reverse_lazy('listar_temporadas')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_tarifas = self.object.tarifas.count()
        context['total_tarifas'] = total_tarifas
        context['puede_eliminar'] = (total_tarifas == 0)
        return context

    def form_valid(self, form):
        self.object = self.get_object()

        if self.object.tarifas.exists():
            messages.error(request=self.request, message=f"No se puede eliminar la temporada '{self.object.nombre}' porque contiene tarifas asociadas.")
            return redirect('listar_temporadas')

        nombre_temporada = self.object.nombre
        valor_viejo = f"ID: {self.object.id}, Nombre: {self.object.nombre}"

        response = super().form_valid(form)

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha eliminado la temporada '{nombre_temporada}'. Detalles previos: {valor_viejo}.",
            tipo="Temporada",
            prioridad="media"
        )
        messages.success(self.request, f"La temporada '{nombre_temporada}' fue eliminada exitosamente.", extra_tags='temporada')
        return response