from django.urls import reverse_lazy
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django import forms
from django.db.models import Count, Q
from App.forms.categoria.forms import CategoriaForm
from App.models import Categoria, Paquete
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from App.utils import crear_notificacion_sistema

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Mixin para asegurar que solo usuarios autenticados con permisos
    de staff/administrador puedan acceder a las vistas administrativas.
    """
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff


# Create your views here.

class CategoriaListView(StaffRequiredMixin, ListView):
    model = Categoria
    template_name = 'admin/categoria/categorias.html'
    context_object_name = 'categorias'

    def get_queryset(self):
        return super().get_queryset().order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = Categoria.objects.aggregate(
            total=Count('id'),
            activas=Count('id', filter=Q(estado=True)),
            inactivas=Count('id', filter=Q(estado=False))
        )
        context.update(stats)
        context['stats_list'] = [
            ('Total Categorías', stats['total'], 'text-dark'),
            ('Activas', stats['activas'], 'text-success'),
            ('Inactivas', stats['inactivas'], 'text-danger'),
        ]
        return context


class CategoriaCreateView(StaffRequiredMixin, CreateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'admin/categoria/agregar_categoria.html'
    success_url = reverse_lazy('listar_categorias')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input', 'role': 'switch'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        response = super().form_valid(form)
        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha creado una nueva categoría: '{self.object.nombre}'.",
            tipo="Categoría",
            prioridad="media"
        )
        messages.success(self.request, f"Categoría '{self.object.nombre}' creada exitosamente.", extra_tags='categoria')
        return response


class CategoriaUpdateView(StaffRequiredMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'admin/categoria/editar_categoria.html'
    success_url = reverse_lazy('listar_categorias')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input', 'role': 'switch'})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({'class': 'form-select'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        return form

    def form_valid(self, form):
        cat_antigua = self.get_object()
        valor_viejo = f"Nombre: {cat_antigua.nombre}, Descripción: {cat_antigua.descripcion}"

        response = super().form_valid(form)

        valor_nuevo = f"Nombre: {self.object.nombre}, Descripción: {self.object.descripcion}"

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha actualizado la categoría: '{self.object.nombre}'.",
            tipo="Categoría",
            prioridad="media"
            
        )
        messages.success(self.request, f"Categoría '{self.object.nombre}' actualizada exitosamente.", extra_tags='categoria')
        return response


@login_required(login_url='login')
@require_POST
def toggle_estado_categoria(request, pk):
    """Alterna el estado Activa/Inactiva de una categoría (solo staff)."""
    if not (request.user.is_active and request.user.is_staff):
        messages.error(request, "No tienes permisos para cambiar el estado de las categorías.")
        return redirect('index')

    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.estado = not categoria.estado
    categoria.save(update_fields=['estado'])

    estado_texto = "activada" if categoria.estado else "inactivada"
    crear_notificacion_sistema(
        usuario=request.user,
        mensaje=f"Se ha {estado_texto} la categoría: '{categoria.nombre}'.",
        tipo="Categoría",
        prioridad="media"
    )
    messages.success(request, f"La categoría '{categoria.nombre}' ha sido {estado_texto} correctamente.", extra_tags='categoria')
    return redirect('listar_categorias')


class CategoriaDeleteView(StaffRequiredMixin, DeleteView):
    model = Categoria
    template_name = 'admin/categoria/eliminar_categoria.html'
    success_url = reverse_lazy('listar_categorias')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_paquetes = self.object.paquetes.count()
        context['total_paquetes'] = total_paquetes
        context['puede_eliminar'] = (total_paquetes == 0)
        return context

    def form_valid(self, form):
        self.object = self.get_object()

        # Validar integridad: No eliminar categoría si está asignada a algún paquete
        if self.object.paquetes.exists():
            messages.error(request=self.request, message=f"No se puede eliminar la categoría '{self.object.nombre}' porque contiene paquetes asociados.")
            return redirect('listar_categorias')

        nombre_categoria = self.object.nombre
        valor_viejo = f"ID: {self.object.id}, Nombre: {self.object.nombre}"

        response = super().form_valid(form)

        crear_notificacion_sistema(
            usuario=self.request.user,
            mensaje=f"Se ha eliminado la categoría: '{nombre_categoria}'.",
            tipo="Categoría",
            prioridad="media"
        )
        messages.success(self.request, f"La categoría '{nombre_categoria}' fue eliminada exitosamente.", extra_tags='categoria')
        return response

