from datetime import date, timedelta
from django import forms
from django.core.exceptions import ValidationError
from App.models import Reserva

class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['usuario', 'paquete', 'fecha_inicio', 'numero_adultos', 'numero_menores', 'estado_reserva']
        labels = {
            'usuario': 'Cliente / Titular',
            'paquete': 'Paquete / Tour',
            'fecha_inicio': 'Fecha del Viaje',
            'numero_adultos': 'Número de Adultos',
            'numero_menores': 'Número de Menores',
            'estado_reserva': 'Estado de la Reserva',
        }
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'paquete': forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'class': 'form-control', 'type': 'date'}
            ),
            'numero_adultos': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'numero_menores': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'estado_reserva': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'usuario' in self.fields:
            self.fields['usuario'].empty_label = 'Seleccione un cliente'
        if 'paquete' in self.fields:
            self.fields['paquete'].empty_label = 'Seleccione un paquete'
        if 'estado_reserva' in self.fields:
            self.fields['estado_reserva'].empty_label = 'Seleccione un estado'
            self.fields['estado_reserva'].choices = [
                ('', 'Seleccione un estado'),
                ('pendiente', 'Pendiente'),
                ('confirmada', 'Confirmada'),
                ('cancelada', 'Cancelada'),
            ]

        if self.instance.pk:
            for field_name in list(self.fields):
                if field_name not in ('numero_adultos', 'numero_menores', 'estado_reserva'):
                    self.fields.pop(field_name)
            self.fields['numero_adultos'].required = False
            self.fields['numero_menores'].required = False

        # Se exigen al menos 5 días de anticipación para reservas nuevas
        if not self.instance.pk:
            fecha_minima = date.today() + timedelta(days=5)
            if 'fecha_inicio' in self.fields:
                self.fields['fecha_inicio'].widget.attrs['min'] = fecha_minima.strftime('%Y-%m-%d')
    def clean_fecha_inicio(self):
        fecha_reserva = self.cleaned_data.get('fecha_inicio')

        if not fecha_reserva:
            return fecha_reserva

        # Si estás editando una reserva ya guardada y no cambias la fecha, la permite sin exigir los 5 días
        if self.instance.pk and self.instance.fecha_inicio == fecha_reserva:
            return fecha_reserva

        hoy = date.today()
        fecha_minima = hoy + timedelta(days=5)

        # 1. Validar que no sea fecha pasada
        if fecha_reserva < hoy:
            raise ValidationError("No puedes seleccionar una fecha pasada.")

        # 2. Validar mínimo 5 días de anticipación
        if fecha_reserva < fecha_minima:
            raise ValidationError(
                f"La reserva debe realizarse con al menos 5 días de anticipación "
                f"(a partir del {fecha_minima.strftime('%d/%m/%Y')})."
            )

        return fecha_reserva

    def clean_numero_adultos(self):
        adultos = self.cleaned_data.get('numero_adultos')
        if self.instance.pk and adultos is None:
            return self.instance.numero_adultos
        if adultos is None or adultos < 1:
            raise ValidationError("Debe haber al menos 1 adulto en la reserva.")
        return adultos

    def clean_numero_menores(self):
        menores = self.cleaned_data.get('numero_menores')
        if self.instance.pk and menores is None:
            return self.instance.numero_menores
        if menores is None or menores < 0:
            raise ValidationError("El número de menores no puede ser negativo.")
        return menores

    def clean(self):
        cleaned_data = super().clean()
        adultos = cleaned_data.get('numero_adultos')
        menores = cleaned_data.get('numero_menores')
        if adultos is not None and adultos > 10:
            raise ValidationError("El cupo de adultos no puede superar las 10 personas.")
        if menores is not None and menores > 10:
            raise ValidationError("El cupo de menores no puede superar las 10 personas.")

        if self.instance.pk:
            return cleaned_data

        usuario = cleaned_data.get('usuario')
        paquete = cleaned_data.get('paquete')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        adultos = cleaned_data.get('numero_adultos') or 0
        menores = cleaned_data.get('numero_menores') or 0

        if adultos + menores <= 0:
            raise ValidationError("La reserva debe incluir al menos una persona.")

        if usuario and paquete and fecha_inicio:
            # Validar unicidad para evitar duplicados en la misma fecha
            qs = Reserva.objects.filter(usuario=usuario, paquete=paquete, fecha_inicio=fecha_inicio)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Este usuario ya tiene una reserva registrada para el mismo paquete en la fecha seleccionada.")

        return cleaned_data



