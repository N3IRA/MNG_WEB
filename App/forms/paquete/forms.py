from App.models import Paquete, Actividades
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.urls import reverse_lazy
import re


class PaqueteForm(ModelForm):
    """Formulario para crear y editar paquetes turísticos incluyendo imagen y actividades."""

    MAX_DIAS = 15
    MAX_NOCHES = 14

    class Meta:
        model = Paquete
        fields = [
            'nombre',
            'categoria',
            'descripcion',
            'imagen',
            'dias_duracion',
            'noches_duracion',
            'punto_encuentro',
            'hora_encuentro',
            'actividades',
            'estado',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del paquete turístico'}),
            'imagen': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe detalladamente el paquete...'
            }),
            'dias_duracion': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '15'}),
            'noches_duracion': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '14'}),
            'punto_encuentro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Plaza Principal de Mongua'
            }),
            'hora_encuentro': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'actividades': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input'
            }),
            'estado': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'role': 'switch',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['actividades'].queryset = Actividades.objects.filter(estado=True)
        if not self.instance.pk:
            self.fields['imagen'].required = True
            self.fields['imagen'].widget.attrs['required'] = 'required'

        # Sincronización reactiva y segura en el servidor mediante HTMX
        sync_url = reverse_lazy('paquete_live_sync')
        self.fields['dias_duracion'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'input changed delay:250ms, change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "dias"}',
            'hx-swap': 'none',
        })
        self.fields['noches_duracion'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'input changed delay:250ms, change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "noches"}',
            'hx-swap': 'none',
        })
        self.fields['nombre'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'input changed delay:300ms, change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "nombre"}',
            'hx-swap': 'none',
        })
        self.fields['categoria'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "categoria"}',
            'hx-swap': 'none',
        })
        self.fields['punto_encuentro'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'input changed delay:300ms, change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "punto"}',
            'hx-swap': 'none',
        })
        self.fields['estado'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "estado"}',
            'hx-swap': 'none',
        })
        self.fields['actividades'].widget.attrs.update({
            'hx-post': sync_url,
            'hx-trigger': 'change',
            'hx-include': '#form-paquete',
            'hx-vals': '{"origen": "actividades"}',
            'hx-swap': 'none',
        })

    def clean_nombre(self):
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre):
            raise ValidationError("El nombre del paquete debe contener texto y no solo números.")
        return nombre

    def clean_descripcion(self):
        descripcion = str(self.cleaned_data.get('descripcion', '')).strip()

        if not descripcion:
            raise ValidationError("La descripción es obligatoria.")

        if descripcion.isdigit():
            raise ValidationError("La descripción no puede contener solo números. Ingresa un texto descriptivo.")

        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', descripcion):
            raise ValidationError("La descripción debe contener letras y detalles explicativos.")

        return descripcion

    def clean_punto_encuentro(self):
        punto = str(self.cleaned_data.get('punto_encuentro', '')).strip()

        if punto.isdigit():
            raise ValidationError("El punto de encuentro no puede contener solo números. Ingresa un lugar o dirección válida.")

        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', punto):
            raise ValidationError("El punto de encuentro debe incluir el nombre de un lugar o texto válido.")

        return punto

    def clean_dias_duracion(self):
        dias = self.cleaned_data.get('dias_duracion')
        if dias is None or dias < 1:
            raise ValidationError("Los días de duración deben ser al menos 1.")
        if dias > self.MAX_DIAS:
            raise ValidationError(f"Los días de duración no pueden superar un máximo de {self.MAX_DIAS} días.")
        return dias

    def clean_noches_duracion(self):
        noches = self.cleaned_data.get('noches_duracion')
        if noches is None or noches < 0:
            raise ValidationError("Las noches de duración deben ser 0 o más (0 para pasadías).")
        if noches > self.MAX_NOCHES:
            raise ValidationError(f"Las noches de duración no pueden superar un máximo de {self.MAX_NOCHES} noches.")
        return noches

    def clean(self):
        cleaned_data = super().clean()
        dias = cleaned_data.get('dias_duracion')
        noches = cleaned_data.get('noches_duracion')

        if dias is not None and noches is not None:
            if noches > dias:
                self.add_error('noches_duracion', "Las noches de duración no pueden ser mayores que los días de duración del paquete.")
        return cleaned_data
