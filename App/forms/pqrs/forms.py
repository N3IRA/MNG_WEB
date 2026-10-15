from django import forms
from App.models import PQRS
from App.models import Seguimiento, Reserva
import re

class PqrsForm(forms.ModelForm):
    tipo = forms.ChoiceField(
        choices=[('', '-- Seleccione una opción --'), ('peticion', 'Petición'), ('queja', 'Queja'), ('reclamo', 'Reclamo'), ('sugerencia', 'Sugerencia')],
        label='Tipo de Solicitud',
        required=True,
    )

    reserva = forms.ModelChoiceField(
        queryset=Reserva.objects.none(),
        required=False,
        label="Reserva Afectada (Opcional)",
        empty_label="-- Selecciona la reserva vinculada --"
    )

    class Meta:
        model = PQRS
        fields = ['tipo', 'asunto', 'descripcion', 'nombre_completo', 'correo']
        labels = {
            'asunto': 'Asunto de la PQRS',
            'descripcion': 'Detalle de su solicitud',
            'nombre_completo': 'Nombre Completo',
            'correo': 'Correo Electrónico',
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Cuéntanos más...'}),
            'nombre_completo': forms.TextInput(attrs={'placeholder': 'Ej. Juan Pérez'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'tu@email.com'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.is_authenticated:
            # Si el usuario está logueado, filtramos sus reservas
            self.fields['reserva'].queryset = Reserva.objects.filter(usuario=user)
            # Y ocultamos los campos de visitante anónimo ya que tomaremos sus datos
            self.fields['nombre_completo'].widget = forms.HiddenInput()
            self.fields['nombre_completo'].required = False
            self.fields['correo'].widget = forms.HiddenInput()
            self.fields['correo'].required = False
        else:
            # Si no hay usuario, ocultamos el campo reserva y hacemos obligatorios nombre y correo
            self.fields['reserva'].widget = forms.HiddenInput()
            self.fields['reserva'].required = False
            self.fields['nombre_completo'].required = True
            self.fields['correo'].required = True

    def clean_asunto(self):
        asunto = str(self.cleaned_data.get('asunto', '')).strip()
        if not asunto:
            raise forms.ValidationError("El asunto de la solicitud es obligatorio.")
        if len(asunto) < 5:
            raise forms.ValidationError("El asunto debe contener al menos 5 caracteres.")
        if asunto.isdigit():
            raise forms.ValidationError("El asunto no puede contener únicamente números. Describe brevemente tu solicitud.")
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', asunto):
            raise forms.ValidationError("El asunto debe contener texto descriptivo con letras.")
        return asunto

    def clean_descripcion(self):
        descripcion = str(self.cleaned_data.get('descripcion', '')).strip()
        if not descripcion:
            raise forms.ValidationError("El detalle de la solicitud es obligatorio.")
        if len(descripcion) < 10:
            raise forms.ValidationError("El detalle debe tener al menos 10 caracteres para poder atender tu solicitud.")
        if descripcion.isdigit():
            raise forms.ValidationError("El detalle no puede contener únicamente números. Explica tu solicitud con texto.")
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', descripcion):
            raise forms.ValidationError("El detalle debe contener texto descriptivo con letras.")
        return descripcion

    def clean_nombre_completo(self):
        nombre = str(self.cleaned_data.get('nombre_completo', '') or '').strip()
        # Si el usuario está autenticado el campo viene oculto/vacío y se toma del perfil
        if not nombre:
            return nombre
        if nombre.isdigit():
            raise forms.ValidationError("El nombre no puede contener únicamente números.")
        if not re.search(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ]', nombre):
            raise forms.ValidationError("El nombre debe contener letras (ej: 'Juan Pérez').")
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s\.]+$', nombre):
            raise forms.ValidationError("El nombre solo puede contener letras, espacios y puntos.")
        return nombre

class SeguimientoForm(forms.ModelForm):
    reserva = forms.ModelChoiceField(
        queryset=Reserva.objects.none(),
        required=False,
        empty_label="-- Seleccione una reserva relacionada (Opcional) --",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Reserva Asociada'
    )

    class Meta:
        model = Seguimiento
        fields = ['reserva', 'respuesta']
        labels = {
            'respuesta': 'Detalle / Mensaje de Seguimiento',
        }
        widgets = {
            'respuesta': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Escribe la respuesta o nota de seguimiento...'}),
        }

    def __init__(self, *args, **kwargs):
        # Filtramos las reservas correspondientes al usuario recibido
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.is_authenticated:
            self.fields['reserva'].queryset = Reserva.objects.filter(usuario=user)