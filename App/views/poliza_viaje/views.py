from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from App.models import PolizaViaje, Usuario
from App.forms.aseguradora.forms import PolizaViajeForm


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_staff or getattr(self.request.user, 'rol', None) == Usuario.Roles.ADMIN
        )


class PolizaViajeListView(StaffRequiredMixin, ListView):
    model = PolizaViaje
    template_name = 'admin/poliza_viaje/listar.html'
    context_object_name = 'polizas'

    def get_queryset(self):
        return PolizaViaje.objects.all().order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stats = PolizaViaje.objects.aggregate(
            total=Count('id'),
            activas=Count('id', filter=Q(estado=True)),
            inactivas=Count('id', filter=Q(estado=False))
        )
        context.update(stats)
        return context


class PolizaViajeCreateView(StaffRequiredMixin, CreateView):
    model = PolizaViaje
    form_class = PolizaViajeForm
    template_name = 'admin/poliza_viaje/crear.html'
    success_url = reverse_lazy('poliza_listar')

    def form_valid(self, form):
        messages.success(self.request, "Póliza de viaje creada con éxito.")
        return super().form_valid(form)


class PolizaViajeUpdateView(StaffRequiredMixin, UpdateView):
    model = PolizaViaje
    form_class = PolizaViajeForm
    template_name = 'admin/poliza_viaje/editar.html'
    success_url = reverse_lazy('poliza_listar')

    def form_valid(self, form):
        messages.success(self.request, "Póliza de viaje actualizada correctamente.")
        return super().form_valid(form)


class PolizaViajeDeleteView(StaffRequiredMixin, DeleteView):
    model = PolizaViaje
    template_name = 'admin/poliza_viaje/eliminar.html'
    success_url = reverse_lazy('poliza_listar')

    def form_valid(self, form):
        messages.success(self.request, "Póliza de viaje eliminada con éxito.")
        return super().form_valid(form)
