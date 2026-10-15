from App.models import Actividades
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
import re

class ActividadesForm(ModelForm):
    """Formulario para crear y editar actividades turísticas."""

    class Meta:
        model = Actividades
        fields = ['nombre', 'descripcion', 'equipo_requerimiento', 'recomendaciones', 'apto_menores', 'estado']
        labels = {
            'nombre': 'Nombre de la Actividad',
            'descripcion': 'Descripción',
            'equipo_requerimiento': 'Equipo Requerido',
            'recomendaciones': 'Recomendaciones / Salud',
            'apto_menores': '¿Apto para Menores?',
            'estado': '¿Está Activa?',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'equipo_requerimiento': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'recomendaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'apto_menores': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_nombre(self):
        nombre = str(self.cleaned_data.get('nombre', '')).strip()

        if not nombre:
            raise ValidationError("El nombre de la actividad es obligatorio.")

        if nombre.isdigit():
            raise ValidationError("El nombre de la actividad no puede ser solo números.")

        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre):
            raise ValidationError("El nombre de la actividad debe contener letras.")

        return nombre

    def clean_descripcion(self):
        descripcion = str(self.cleaned_data.get('descripcion', '')).strip()

        if not descripcion:
            raise ValidationError("La descripción es obligatoria.")

        if descripcion.isdigit():
            raise ValidationError("La descripción no puede contener únicamente números.")

        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', descripcion):
            raise ValidationError("La descripción debe incluir un texto explicativo con letras.")

        return descripcion

    def clean_equipo_requerimiento(self):
        equipo = str(self.cleaned_data.get('equipo_requerimiento', '') or '').strip()
        if equipo and equipo.isdigit():
            raise ValidationError("El equipo requerido no puede contener únicamente números. Describe los elementos necesarios.")
        if equipo and not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', equipo):
            raise ValidationError("El equipo requerido debe incluir texto descriptivo con letras.")
        return equipo

    def clean_recomendaciones(self):
        recomendaciones = str(self.cleaned_data.get('recomendaciones', '') or '').strip()
        if recomendaciones and recomendaciones.isdigit():
            raise ValidationError("Las recomendaciones no pueden contener únicamente números. Escribe indicaciones en texto.")
        if recomendaciones and not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', recomendaciones):
            raise ValidationError("Las recomendaciones deben incluir texto descriptivo con letras.")
        return recomendaciones
