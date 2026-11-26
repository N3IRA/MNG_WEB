from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm
import re
from datetime import date
from App.models import Promocion, Paquete


class PromocionForm(ModelForm):
    """Formulario para crear y editar promociones conforme a models.py y asociar paquetes turísticos."""

    paquetes = forms.ModelMultipleChoiceField(
        queryset=Paquete.objects.filter(estado=True),
        required=False,
        label="Paquetes a los que aplica",
        help_text="Selecciona uno o varios paquetes turísticos para vincular a esta promoción.",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Promocion
        fields = [
            'nombre',
            'codigo_promocion',
            'porcentaje_descuento',
            'fecha_inicio',
            'fecha_fin',
            'descripcion',
            'condiciones',
            'activa',
        ]
        labels = {
            'nombre': 'Nombre de la Promoción',
            'codigo_promocion': 'Código de Promoción',
            'porcentaje_descuento': 'Porcentaje de Descuento (%)',
            'fecha_inicio': 'Fecha de Inicio',
            'fecha_fin': 'Fecha de Finalización',
            'descripcion': 'Descripción de la Oferta',
            'condiciones': 'Términos y Condiciones (Opcional)',
            'activa': '¿Promoción Activa?',
        }
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Descuento Semana Santa 2026'}),
            'codigo_promocion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. PROM-SEMANASANTA-26'}),
            'porcentaje_descuento': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 100, 'placeholder': 'Ej. 20'}),
            'fecha_inicio': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe los beneficios de esta promoción...'}),
            'condiciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Aplica sólo para fines de semana, no acumulable con otras ofertas...'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        hoy_str = date.today().strftime('%Y-%m-%d')
        if not self.instance or not self.instance.pk:
            self.fields['fecha_inicio'].widget.attrs['min'] = hoy_str
            self.fields['fecha_fin'].widget.attrs['min'] = hoy_str
        else:
            min_inicio = min(self.instance.fecha_inicio, date.today()).strftime('%Y-%m-%d') if self.instance.fecha_inicio else hoy_str
            min_fin = min(self.instance.fecha_fin, date.today()).strftime('%Y-%m-%d') if self.instance.fecha_fin else hoy_str
            self.fields['fecha_inicio'].widget.attrs['min'] = min_inicio
            self.fields['fecha_fin'].widget.attrs['min'] = min_fin

        if self.instance and self.instance.pk:
            # Inicializar los paquetes asociados actuales
            paquetes_ids = self.instance.paquetepromocion_set.values_list('paquete_id', flat=True)
            self.fields['paquetes'].initial = list(paquetes_ids)

    def clean_nombre(self):
        nombre = str(self.cleaned_data.get('nombre', '')).strip()
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre):
            raise ValidationError("El nombre de la promoción debe contener letras.")
        return nombre

    def clean_codigo_promocion(self):
        codigo = str(self.cleaned_data.get('codigo_promocion', '')).strip().upper()
        if not codigo:
            raise ValidationError("El código de la promoción es obligatorio.")
        
        # Validar unicidad excluyendo la instancia actual
        qs = Promocion.objects.filter(codigo_promocion=codigo)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe una promoción con este código de promoción.")
        return codigo

    def clean_porcentaje_descuento(self):
        descuento = self.cleaned_data.get('porcentaje_descuento')
        if descuento is None or descuento < 1 or descuento > 100:
            raise ValidationError("El porcentaje de descuento debe encontrarse entre 1 y 100.")
        return descuento

    def clean(self):
        cleaned_data = super().clean()
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')
        hoy = date.today()

        if fecha_inicio:
            # En creación o si se modificó la fecha de inicio en edición
            if not self.instance.pk or (self.instance.pk and fecha_inicio != self.instance.fecha_inicio):
                if fecha_inicio < hoy:
                    self.add_error('fecha_inicio', "La fecha de inicio no puede ser anterior a la fecha actual.")

        if fecha_fin:
            # En creación o si se modificó la fecha de fin en edición
            if not self.instance.pk or (self.instance.pk and fecha_fin != self.instance.fecha_fin):
                if fecha_fin < hoy:
                    self.add_error('fecha_fin', "La fecha de finalización no puede ser anterior a la fecha actual.")

        if fecha_inicio and fecha_fin:
            if fecha_fin < fecha_inicio:
                self.add_error('fecha_fin', "La fecha de finalización no puede ser anterior a la fecha de inicio.")

        return cleaned_data
