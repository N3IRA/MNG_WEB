from App.models import Temporada
from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
from django.utils import timezone
from datetime import timedelta
import re

class TemporadaForm(ModelForm):
    """Formulario para crear y editar temporadas turísticas con fechas de vigencia."""

    class Meta:
        model = Temporada
        fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'estado']
        labels = {
            'nombre': 'Nombre de la Temporada',
            'descripcion': 'Descripción',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Finalización',
            'estado': '¿Está Activa?',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'fecha_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'fecha_fin': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limite_inicio = timezone.localdate() - timedelta(days=7)
        limite_fin = timezone.localdate() + timedelta(days=1)
        if not self.instance.pk:
            self.fields['fecha_inicio'].widget.attrs['min'] = limite_inicio.isoformat()
            self.fields['fecha_fin'].widget.attrs['min'] = limite_fin.isoformat()
        else:
            min_inicio = min(self.instance.fecha_inicio, limite_inicio) if self.instance.fecha_inicio else limite_inicio
            min_fin = min(self.instance.fecha_fin, limite_fin) if self.instance.fecha_fin else limite_fin
            self.fields['fecha_inicio'].widget.attrs['min'] = min_inicio.isoformat()
            self.fields['fecha_fin'].widget.attrs['min'] = min_fin.isoformat()

    def clean_nombre(self):
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre):
            raise ValidationError("El nombre de la temporada debe contener letras (ej: 'Temporada Alta 2026').")
        if nombre.isdigit():
            raise ValidationError("El nombre de la temporada no puede contener únicamente números.")
        return nombre

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        hoy = timezone.localdate()
        limite_minimo_inicio = hoy - timedelta(days=7)

        if fecha_inicio:
            # En creación, permitir hasta una semana antes de la fecha actual
            if not self.instance.pk and fecha_inicio < limite_minimo_inicio:
                self.add_error('fecha_inicio', f"La fecha de inicio ({fecha_inicio.strftime('%d/%m/%Y')}) no puede ser anterior a una semana antes de la fecha actual ({limite_minimo_inicio.strftime('%d/%m/%Y')}).")
            # En edición, no permitir moverla a una fecha previa a una semana antes de hoy
            elif self.instance.pk and self.instance.fecha_inicio != fecha_inicio and fecha_inicio < limite_minimo_inicio:
                self.add_error('fecha_inicio', f"No puedes modificar la fecha de inicio a una fecha anterior a una semana antes de hoy ({limite_minimo_inicio.strftime('%d/%m/%Y')}).")

        if fecha_fin:
            # La fecha de finalización no puede ser anterior ni igual a la fecha actual (debe ser posterior a hoy)
            if not self.instance.pk and fecha_fin <= hoy:
                self.add_error('fecha_fin', f"La fecha de finalización ({fecha_fin.strftime('%d/%m/%Y')}) no puede ser anterior ni el mismo día que hoy ({hoy.strftime('%d/%m/%Y')}). Debe ser posterior a la fecha actual.")
            elif self.instance.pk and self.instance.fecha_fin != fecha_fin and fecha_fin <= hoy:
                self.add_error('fecha_fin', f"No puedes modificar la fecha de finalización a una fecha anterior o igual a hoy ({hoy.strftime('%d/%m/%Y')}). Debe ser posterior a la fecha actual.")

        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                self.add_error('fecha_fin', "La fecha de finalización no puede ser anterior ni igual a la fecha de inicio.")

        return cleaned_data
    