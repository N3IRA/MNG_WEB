import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from App.models import Pago


class ComprobantePagoForm(forms.ModelForm):
    """
    Formulario con seguridad reforzada para la carga de comprobantes de pago.
    Implementa:
    1. Lista Blanca estricta de campos: si el usuario o un atacante inyecta campos
       adicionales (ej. monto, estado_transaccion, is_staff, id) se genera un ValidationError explícito.
    2. Validación de extensiones, dobles extensiones y tamaño máximo de archivo.
    3. Inspección de contenido malicioso y scripts en el comprobante.
    4. Validación de caracteres permitidos en la referencia bancaria.
    """
    BANCOS_CHOICES = [
        ('', '— Selecciona el banco o medio de pago —'),
        ('Nequi', 'Nequi'),
        ('Daviplata', 'Daviplata'),
        ('Bancolombia', 'Bancolombia'),
        ('Banco de Bogotá', 'Banco de Bogotá'),
        ('Davivienda', 'Davivienda'),
        ('BBVA', 'BBVA'),
        ('Banco de Occidente', 'Banco de Occidente'),
        ('Lulo Bank', 'Lulo Bank'),
        ('RappiPay', 'RappiPay'),
        ('Otro', 'Otro (Especificar en descripción)'),
    ]

    METODOS_CHOICES = [
        ('Transferencia Bancaria', 'Transferencia Bancaria'),
        ('Billetera Digital', 'Billetera Digital (Nequi / Daviplata / etc.)'),
        ('Depósito en Corresponsal', 'Depósito en Corresponsal'),
        ('PSE / Enlace de Pago', 'PSE / Enlace de Pago'),
        ('Otro', 'Otro Método'),
    ]

    # Conjunto estricto de campos permitidos en la petición POST
    CAMPOS_PERMITIDOS = {
        'csrfmiddlewaretoken',
        'referencia',
        'banco_origen',
        'metodo_pago',
        'descripcion',
        'reserva',
        'imagen_comprobante',
    }

    banco_origen = forms.ChoiceField(
        choices=BANCOS_CHOICES,
        required=True,
        widget=forms.Select(attrs={
            'class': 'select form-select',
            'id': 'id_banco_origen',
            'required': True
        }),
        error_messages={'required': 'Por favor selecciona un banco o medio de pago.'}
    )

    metodo_pago = forms.ChoiceField(
        choices=METODOS_CHOICES,
        required=False,
        initial='Transferencia Bancaria',
        widget=forms.Select(attrs={
            'class': 'select form-select',
            'id': 'id_metodo_pago'
        })
    )

    imagen_comprobante = forms.ImageField(
        required=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf'])],
        widget=forms.ClearableFileInput(attrs={
            'class': 'clearablefileinput form-control',
            'id': 'id_imagen_comprobante',
            'accept': 'image/png, image/jpeg, image/webp, image/gif, application/pdf',
            'required': True
        }),
        error_messages={
            'required': 'Debes adjuntar la imagen o PDF del comprobante de pago.',
            'invalid_image': 'El archivo subido no es una imagen o archivo válido.'
        }
    )

    class Meta:
        model = Pago
        fields = [
            'referencia',
            'banco_origen',
            'metodo_pago',
            'imagen_comprobante',
            'descripcion'
        ]
        widgets = {
            'referencia': forms.TextInput(attrs={
                'class': 'textinput form-control',
                'id': 'id_referencia',
                'placeholder': 'Ej. CUS-123456789 o Nº Aprobación',
                'maxlength': '100',
                'required': True
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'textarea form-control',
                'id': 'id_descripcion',
                'rows': 3,
                'placeholder': 'Detalles adicionales o especificación de banco si seleccionaste Otro'
            }),
        }
        error_messages = {
            'referencia': {
                'required': 'El número de referencia o transacción es obligatorio.',
                'max_length': 'La referencia no puede exceder 100 caracteres.'
            }
        }

    def clean(self):
        cleaned_data = super().clean()

        # Validación estricta de seguridad: si se agregan otros datos o parámetros extraños
        campos_enviados = set(self.data.keys())
        campos_no_permitidos = campos_enviados - self.CAMPOS_PERMITIDOS
        if campos_no_permitidos:
            nombres = ', '.join(sorted(campos_no_permitidos))
            raise ValidationError(
                f"Error de seguridad: Se detectaron campos o datos no autorizados en la solicitud ({nombres}). "
                "La operación ha sido bloqueada por Django para garantizar la integridad financiera."
            )

        return cleaned_data

    def clean_referencia(self):
        referencia = self.cleaned_data.get('referencia', '').strip()
        if not referencia:
            raise ValidationError("La referencia de pago no puede estar vacía.")
        if len(referencia) < 3:
            raise ValidationError("La referencia debe contener al menos 3 caracteres.")
        if not re.match(r'^[A-Za-z0-9\-_#\s\.]+$', referencia):
            raise ValidationError("La referencia contiene caracteres no permitidos. Solo se admiten letras, números y guiones.")
        return referencia

    def clean_imagen_comprobante(self):
        archivo = self.cleaned_data.get('imagen_comprobante')
        if archivo:
            # 1. Límite de tamaño: 10 MB
            max_mb = 10
            if archivo.size > max_mb * 1024 * 1024:
                raise ValidationError(f"El comprobante no puede pesar más de {max_mb} MB.")

            # 2. Protección contra dobles extensiones peligrosas (ej. archivo.php.png, exploit.sh.jpg)
            nombre = archivo.name.lower()
            extensiones_peligrosas = ('.php', '.exe', '.sh', '.bat', '.py', '.pl', '.jsp', '.asp', '.aspx', '.cgi', '.cmd', '.vbs', '.phtml')
            for ext in extensiones_peligrosas:
                if ext in nombre:
                    raise ValidationError(
                        f"Archivo sospechoso detectado con extensión no permitida ({ext}). Solo se admiten imágenes limpias o PDF."
                    )

            # 3. Inspección de código o scripts maliciosos en los primeros bytes del archivo
            pos = archivo.tell() if hasattr(archivo, 'tell') else 0
            archivo.seek(0)
            primeros_bytes = archivo.read(1024)
            archivo.seek(pos)

            patrones_maliciosos = [b'<?php', b'<script', b'eval(', b'base64_decode', b'system(', b'shell_exec(']
            for patron in patrones_maliciosos:
                if patron in primeros_bytes.lower():
                    raise ValidationError("El archivo adjunto contiene código ejecutable no permitido por seguridad.")

        return archivo
