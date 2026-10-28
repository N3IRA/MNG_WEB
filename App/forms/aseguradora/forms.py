from django import forms
from App.models import Aseguradora, PolizaViaje


class PolizaViajeForm(forms.ModelForm):
    class Meta:
        model = PolizaViaje
        fields = [
            'nombre_poliza', 'descripcion', 'cobertura_medica_max', 
            'cubre_perdida_equipaje', 'cubre_cancelacion_vuelo', 
            'precio_diario', 'condiciones_generales', 'estado'
        ]
        widgets = {
            'nombre_poliza': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Póliza Integral Mongua'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción detallada de coberturas'}),
            'cobertura_medica_max': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'cubre_perdida_equipaje': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'cubre_cancelacion_vuelo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'precio_diario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'condiciones_generales': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'estado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AseguradoraForm(forms.ModelForm):
    class Meta:
        model = Aseguradora
        fields = [
            'reserva', 'poliza_viaje', 'nombre_empresa', 
            'numero_poliza', 'fecha_inicio_cobertura', 
            'fecha_fin_cobertura', 'telefono_emergencia', 'estado_emision'
        ]
        widgets = {
            'reserva': forms.Select(attrs={'class': 'form-select'}),
            'poliza_viaje': forms.Select(attrs={'class': 'form-select'}),
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Seguros del Estado'}),
            'numero_poliza': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Opcional (se autogenera si se deja vacío)'}),
            'fecha_inicio_cobertura': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin_cobertura': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'telefono_emergencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+57 ...'}),
            'estado_emision': forms.Select(choices=[('Pendiente', 'Pendiente'), ('Emitida', 'Emitida'), ('Cancelada', 'Cancelada')], attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['numero_poliza'].required = False
