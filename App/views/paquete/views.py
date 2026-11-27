from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden
from django.utils.html import format_html
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Count, Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from datetime import date
from App.forms.paquete.forms import PaqueteForm
from App.utils import crear_notificacion_sistema
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from App.models import Paquete, Categoria, Actividades, Tarifa, Temporada
from decimal import Decimal, InvalidOperation


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para asegurar que solo usuarios autenticados con permisos
    de staff/administrador puedan acceder a las vistas administrativas.
    """
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff

def tours(request):
    """
    Vista pública que filtra y devuelve el catálogo de tours y paquetes turísticos disponibles.
    Aplica sanitización y validaciones exhaustivas a los parámetros de búsqueda y filtrado GET.
    """
    lista_tours = Paquete.objects.filter(estado=True)
    sugerencias_tours = Paquete.objects.filter(estado=True).values('nombre').distinct()

    # 1. Filtro de búsqueda textual por nombre del tour
    busqueda = request.GET.get('q', '').strip()
    if busqueda and len(busqueda) <= 100:
        lista_tours = lista_tours.filter(nombre__icontains=busqueda)

    # 2. Filtro de precio máximo permitido (solo tarifas activas y vigentes)
    precio_max = request.GET.get('precio_max', '').strip()
    if precio_max:
        try:
            precio_decimal = Decimal(precio_max)
            if precio_decimal >= 0:
                lista_tours = lista_tours.filter(
                    tarifas__estado=True,
                    tarifas__temporada__estado=True,
                    tarifas__temporada__fecha_inicio__lte=date.today(),
                    tarifas__temporada__fecha_fin__gte=date.today(),
                    tarifas__precio_adulto__lte=precio_decimal
                ).distinct()
        except (InvalidOperation, TypeError):
            pass

    # 3. Filtro según aptitud para menores de edad
    # 'si'  -> paquetes donde TODAS las actividades son aptas para menores
    # 'no'  -> paquetes donde ninguna actividad es apta para menores
    # (todas las actividades son solo para adultos; no puede haber ni una sola)
    apto_menores = request.GET.get('apto_menores', '').strip().lower()
    if apto_menores == 'si':
        lista_tours = lista_tours.exclude(actividades__apto_menores=False).distinct()
    elif apto_menores == 'no':
        lista_tours = lista_tours.exclude(actividades__apto_menores=True).distinct()

    # 4. Filtro por categoría del tour
    categoria_id = request.GET.get('categoria', '').strip()
    if categoria_id:
        try:
            cat_id = int(categoria_id)
            if cat_id > 0:
                lista_tours = lista_tours.filter(categoria_id=cat_id)
        except (ValueError, TypeError):
            pass

    lista_tours = lista_tours.select_related('categoria').prefetch_related('actividades', 'tarifas__temporada', 'paquetepromocion_set__promocion')
    lista_categorias = Categoria.objects.filter(estado=True)

    contexto = {
        'tours': lista_tours,
        'sugerencias_tours': sugerencias_tours,
        'categorias': lista_categorias,
    }
    return render(request, 'admin/paquete/destinos.html', contexto)


# ==========================================
# PAQUETES (ADMINISTRACIÓN)
# ==========================================

class PaqueteListView(StaffRequiredMixin, ListView):
    model = Paquete
    template_name = 'admin/paquete/paquetes.html'
    context_object_name = 'paquetes'

    def get_queryset(self):
        queryset = super().get_queryset().select_related('categoria').prefetch_related('actividades', 'tarifas')
        categoria_id = self.request.GET.get('categoria', '').strip()
        if categoria_id:
            try:
                cat_id = int(categoria_id)
                if cat_id > 0:
                    queryset = queryset.filter(categoria_id=cat_id)
            except (ValueError, TypeError):
                pass

        estado = self.request.GET.get('estado', '').strip()
        if estado == 'activos':
            queryset = queryset.filter(estado=True)
        elif estado == 'inactivos':
            queryset = queryset.filter(estado=False)

        return queryset.order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = Paquete.objects.aggregate(
            total=Count('id'),
            activos=Count('id', filter=Q(estado=True)),
            inactivos=Count('id', filter=Q(estado=False))
        )
        context.update(stats)
        context['total_categorias'] = Categoria.objects.count()
        context['stats_list'] = [
            ('Total Paquetes', stats['total'], 'text-dark'),
            ('Activos', stats['activos'], 'text-success'),
            ('Inactivos', stats['inactivos'], 'text-danger'),
        ]
        context['categorias'] = Categoria.objects.all()
        context['categoria_seleccionada'] = self.request.GET.get('categoria', '')
        context['estado_seleccionado'] = self.request.GET.get('estado', '')
        return context


class PaqueteCreateView(StaffRequiredMixin, CreateView):
    model = Paquete
    form_class = PaqueteForm
    template_name = 'admin/paquete/agregar_paquete.html'
    success_url = reverse_lazy('listar_paquetes')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha creado un nuevo paquete: '{self.object.nombre}'.",
            tipo="Paquete",
            prioridad="media"
        )
        messages.success(self.request, f"Paquete '{self.object.nombre}' creado exitosamente.", extra_tags='paquete')
        return response


class PaqueteUpdateView(StaffRequiredMixin, UpdateView):
    model = Paquete
    form_class = PaqueteForm
    template_name = 'admin/paquete/editar_paquete.html'
    success_url = reverse_lazy('listar_paquetes')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        paquete_antiguo = self.get_object()
        valor_viejo = f"Nombre: {paquete_antiguo.nombre}, Categoría: {paquete_antiguo.categoria}, Estado: {'Activo' if paquete_antiguo.estado else 'Inactivo'}"

        response = super().form_valid(form)

        valor_nuevo = f"Nombre: {self.object.nombre}, Categoría: {self.object.categoria}, Estado: {'Activo' if self.object.estado else 'Inactivo'}"

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha actualizado el paquete: '{self.object.nombre}'.",
            tipo="Paquete",
            prioridad="media"
        )
        messages.success(self.request, f"Cambios guardados en el paquete '{self.object.nombre}'.", extra_tags='paquete')
        return response


@login_required(login_url='login')
@require_POST
def paquete_live_sync(request):
    """
    Endpoint HTMX para sincronizar de forma reactiva y segura la duración (días/noches)
    y la tarjeta de vista previa del paquete turístico.
    Todas las validaciones, cálculos y renderizado se ejecutan en el servidor para evitar
    manipulaciones indebidas desde el navegador y prevenir inyecciones de código.
    """
    if not (request.user.is_active and request.user.is_staff):
        return HttpResponseForbidden("Acceso restringido a administradores.")

    origen = request.POST.get('origen', '').strip()

    # 1. Días y Noches (Cálculo bidireccional seguro en el servidor usando los límites de PaqueteForm)
    max_dias = PaqueteForm.MAX_DIAS
    max_noches = PaqueteForm.MAX_NOCHES
    dias_ajustado = False
    noches_ajustado = False

    try:
        raw_dias = request.POST.get('dias_duracion')
        dias_input = int(raw_dias) if raw_dias is not None and str(raw_dias).strip() != '' else 1
    except (ValueError, TypeError):
        dias_input = 1
        dias_ajustado = True

    try:
        raw_noches = request.POST.get('noches_duracion')
        noches_input = int(raw_noches) if raw_noches is not None and str(raw_noches).strip() != '' else 0
    except (ValueError, TypeError):
        noches_input = 0
        noches_ajustado = True

    if origen == 'dias':
        dias = max(1, min(max_dias, dias_input))
        if dias != dias_input:
            dias_ajustado = True
        noches = max(0, min(max_noches, dias - 1))
    elif origen == 'noches':
        noches = max(0, min(max_noches, noches_input))
        if noches != noches_input:
            noches_ajustado = True
        dias = max(1, min(max_dias, noches + 1))
    else:
        dias = max(1, min(max_dias, dias_input))
        noches = max(0, min(max_noches, noches_input))
        if dias != dias_input:
            dias_ajustado = True
        if noches != noches_input:
            noches_ajustado = True

    txt_dias = f"{dias} día" if dias == 1 else f"{dias} días"
    txt_noches = f"{noches} noche" if noches == 1 else f"{noches} noches"
    duracion_texto = f"{txt_dias} / {txt_noches}"

    # 2. Nombre del paquete
    nombre = request.POST.get('nombre', '').strip()

    # 3. Punto de encuentro
    punto_encuentro = request.POST.get('punto_encuentro', '').strip() or 'Sin definir'

    # 4. Categoría
    categoria_id = request.POST.get('categoria', '').strip()
    categoria_nombre = "Sin categoría"
    if categoria_id:
        try:
            cat = Categoria.objects.filter(pk=int(categoria_id), estado=True).first()
            if cat:
                categoria_nombre = cat.nombre
        except (ValueError, TypeError):
            pass

    # 5. Conteo seguro de actividades seleccionadas
    actividades_ids = request.POST.getlist('actividades')
    actividades_count = 0
    if actividades_ids:
        try:
            ids_validos = [int(x) for x in actividades_ids if str(x).isdigit()]
            actividades_count = Actividades.objects.filter(id__in=ids_validos, estado=True).count()
        except Exception:
            actividades_count = 0

    # 6. Estado activo/inactivo
    estado_val = request.POST.get('estado')
    estado = estado_val in ['on', 'true', 'True', '1', True]

    # 7. Renderizar inputs desde PaqueteForm y fragmentos OOB sanitizados con format_html (sin archivo parcial)
    form_sync = PaqueteForm(initial={'dias_duracion': dias, 'noches_duracion': noches})
    fragmentos = [
        format_html(
            '<span id="preview-duracion" class="fw-bold text-dark small" hx-swap-oob="innerHTML">{}</span>',
            duracion_texto,
        ),
        format_html(
            '<span id="preview-titulo-nombre" hx-swap-oob="innerHTML">{}</span>',
            nombre or 'Sin nombre',
        ),
        format_html(
            '<span id="preview-punto-encuentro" class="text-dark small text-truncate fw-semibold" style="max-width: 150px;" title="{}" hx-swap-oob="outerHTML">{}</span>',
            punto_encuentro,
            punto_encuentro,
        ),
        format_html(
            '<span id="preview-actividades-count" class="badge bg-success bg-opacity-10 text-success fw-bold" hx-swap-oob="outerHTML">{} {}</span>',
            actividades_count,
            'actividad' if actividades_count == 1 else 'actividades',
        ),
        format_html(
            '<span id="preview-badge-estado" class="badge {} text-white rounded-pill px-3 py-1 small fw-semibold" hx-swap-oob="outerHTML"><i class="bi {} me-1"></i> {}</span>',
            'bg-success' if estado else 'bg-danger',
            'bi-check-circle-fill' if estado else 'bi-x-circle-fill',
            'Paquete Activo' if estado else 'Inactivo',
        ),
    ]

    if origen == 'dias' or noches_ajustado:
        form_sync.fields['noches_duracion'].widget.attrs['hx-swap-oob'] = 'outerHTML'
        fragmentos.append(str(form_sync['noches_duracion']))

    if origen == 'noches' or dias_ajustado:
        form_sync.fields['dias_duracion'].widget.attrs['hx-swap-oob'] = 'outerHTML'
        fragmentos.append(str(form_sync['dias_duracion']))

    return HttpResponse('\n'.join(fragmentos))


@login_required(login_url='login')
@require_POST
def toggle_estado_paquete(request, pk):
    """Alterna el estado Activo/Inactivo de un paquete turístico (solo staff)."""
    if not (request.user.is_active and request.user.is_staff):
        messages.error(request, "No tienes permisos para cambiar el estado de los paquetes.")
        return redirect('index')

    paquete = get_object_or_404(Paquete, pk=pk)
    paquete.estado = not paquete.estado
    paquete.save(update_fields=['estado'])

    estado_texto = "activado" if paquete.estado else "inactivado"
    crear_notificacion_sistema(
        usuario=request.user,
        mensaje=f"Se ha {estado_texto} el paquete: '{paquete.nombre}'.",
        tipo="Paquete",
        prioridad="media"
    )
    messages.success(request, f"El paquete '{paquete.nombre}' ha sido {estado_texto} correctamente.", extra_tags='paquete')
    return redirect('listar_paquetes')


class PaqueteDeleteView(StaffRequiredMixin, DeleteView):
    model = Paquete
    template_name = 'admin/paquete/eliminar_paquete.html'
    success_url = reverse_lazy('listar_paquetes')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_tarifas = self.object.tarifas.count()
        total_reservas = self.object.reservas.count()
        context['total_tarifas'] = total_tarifas
        context['total_reservas'] = total_reservas
        context['puede_eliminar'] = (total_tarifas == 0 and total_reservas == 0)
        return context

    def form_valid(self, form):
        self.object = self.get_object()

        # Validar integridad referencial: Prevenir borrado si el paquete tiene tarifas asociadas
        if self.object.tarifas.exists():
            messages.error(request=self.request, message=f"No se puede eliminar el paquete '{self.object.nombre}' porque tiene tarifas asociadas. Elimina las tarifas primero o inactiva el paquete.")
            return redirect('listar_paquetes')

        if self.object.reservas.exists():
            messages.error(request=self.request, message=f"No se puede eliminar el paquete '{self.object.nombre}' porque tiene reservas vinculadas. Puedes inactivarlo en su lugar.")
            return redirect('listar_paquetes')

        nombre_paquete = self.object.nombre
        valor_viejo = f"ID: {self.object.id}, Nombre: {self.object.nombre}, Categoría: {self.object.categoria}"

        response = super().form_valid(form)

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha eliminado el paquete: '{nombre_paquete}'.",
            tipo="Paquete",
            prioridad="media"
        )
        messages.success(self.request, f"El paquete '{nombre_paquete}' fue eliminado permanentemente.", extra_tags='paquete')
        return response


