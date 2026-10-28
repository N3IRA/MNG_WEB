from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Sum
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from App.models import Aseguradora, Usuario
from App.forms.aseguradora.forms import AseguradoraForm


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or getattr(self.request.user, 'rol', None) == Usuario.Roles.ADMIN
        )


class AseguradoraListView(StaffRequiredMixin, ListView):
    model = Aseguradora
    template_name = 'admin/aseguradora/listar.html'
    context_object_name = 'seguros'

    def get_queryset(self):
        return Aseguradora.objects.select_related('reserva', 'poliza_viaje').order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = Aseguradora.objects.aggregate(
            total=Count('id'),
            total_costo=Sum('costo_seguro')
        )
        context.update(stats)
        return context


class AseguradoraCreateView(StaffRequiredMixin, CreateView):
    model = Aseguradora
    form_class = AseguradoraForm
    template_name = 'admin/aseguradora/crear.html'
    success_url = reverse_lazy('aseguradora_listar')

    def form_valid(self, form):
        messages.success(self.request, "Seguro emitido registrado con éxito.")
        return super().form_valid(form)


class AseguradoraUpdateView(StaffRequiredMixin, UpdateView):
    model = Aseguradora
    form_class = AseguradoraForm
    template_name = 'admin/aseguradora/editar.html'
    success_url = reverse_lazy('aseguradora_listar')

    def form_valid(self, form):
        messages.success(self.request, "Registro de seguro actualizado correctamente.")
        return super().form_valid(form)


class AseguradoraDeleteView(StaffRequiredMixin, DeleteView):
    model = Aseguradora
    template_name = 'admin/aseguradora/eliminar.html'
    success_url = reverse_lazy('aseguradora_listar')

    def form_valid(self, form):
        messages.success(self.request, "Registro de seguro eliminado con éxito.")
        return super().form_valid(form)
