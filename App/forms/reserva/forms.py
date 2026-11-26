from datetime import date, timedelta
import re
from django import forms
from django.core.exceptions import ValidationError
from App.models import Reserva, Usuario, Paquete, Temporada, Tarifa

PATRON_INYECCION = re.compile(
    r'(<|>|script|javascript:|vbscript:|onerror|onload|onclick|onmouseover|--|;|/\*|\*/|\x00|\r|\n|union\s+select|drop\s+table|insert\s+into|delete\s+from)',
    re.IGNORECASE
)
TIPOS_DOCUMENTO_VALIDOS = {'CC', 'CE', 'PASAPORTE', 'TI', 'OTRO'}
MODALIDADES_CLIENTE_VALIDAS = {'presencial', 'registrado'}


class ReservaForm(forms.ModelForm):
    tipo_cliente = forms.ChoiceField(
        label='Modalidad del Cliente',
        choices=[
            ('presencial', 'Cliente Presencial (Sin cuenta registrada)'),
            ('registrado', 'Cliente Registrado (Con cuenta en el sistema)'),
        ],
        initial='presencial',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        required=False,
    )

    class Meta:
        model = Reserva
        fields = [
            'tipo_cliente',
            'usuario',
            'cliente_nombre',
            'cliente_email',
            'cliente_tipo_documento',
            'cliente_documento',
            'cliente_telefono',
            'paquete',
            'fecha_inicio',
            'numero_adultos',
            'numero_menores',
            'estado_reserva',
        ]
        labels = {
            'usuario': 'Cliente Registrado',
            'cliente_nombre': 'Nombre Completo del Cliente',
            'cliente_email': 'Correo Electrónico',
            'cliente_tipo_documento': 'Tipo de Documento',
            'cliente_documento': 'Número de Documento',
            'cliente_telefono': 'Teléfono de Contacto',
            'paquete': 'Paquete / Tour',
            'fecha_inicio': 'Fecha del Viaje',
            'numero_adultos': 'Número de Adultos',
            'numero_menores': 'Número de Menores',
            'estado_reserva': 'Estado de la Reserva',
        }
        widgets = {
            'usuario': forms.Select(attrs={'class': 'form-select'}),
            'cliente_nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. Juan Pérez Gómez',
                'maxlength': '150',
                'autocomplete': 'off',
            }),
            'cliente_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'cliente@ejemplo.com',
                'maxlength': '254',
                'autocomplete': 'off',
            }),
            'cliente_tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'cliente_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 1020304050',
                'maxlength': '30',
                'autocomplete': 'off',
            }),
            'cliente_telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej. 3101234567',
                'maxlength': '20',
                'autocomplete': 'off',
            }),
            'paquete': forms.Select(attrs={'class': 'form-select form-select-lg bg-light border-0 shadow-sm'}),
            'fecha_inicio': forms.DateInput(
                format='%Y-%m-%d',
                attrs={
                    'class': 'form-control form-control-lg bg-light border-0 px-3',
                    'type': 'text',
                    'placeholder': 'Selecciona la fecha de tu aventura...',
                    'readonly': 'readonly',
                    'style': 'cursor: pointer;'
                }
            ),
            'numero_adultos': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '10'}),
            'numero_menores': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '10'}),
            'estado_reserva': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'usuario' in self.fields:
            self.fields['usuario'].queryset = Usuario.objects.filter(
                rol=Usuario.Roles.CLIENTE,
                is_active=True
            ).order_by('first_name', 'last_name', 'username')
            self.fields['usuario'].empty_label = 'Seleccione un cliente registrado'
            self.fields['usuario'].label_from_instance = lambda obj: (
                f"{obj.nombre_completo} — Doc: {obj.numero_documento} — {obj.email}"
            )
            self.fields['usuario'].required = False

        if 'paquete' in self.fields:
            self.fields['paquete'].queryset = Paquete.objects.filter(estado=True).order_by('nombre')
            self.fields['paquete'].empty_label = 'Seleccione un paquete'
            self.fields['paquete'].required = True

        if 'estado_reserva' in self.fields:
            if not self.instance.pk:
                # Al crear una reserva nueva sin pago aprobado, siempre es predeterminada como 'pendiente'
                self.fields['estado_reserva'].widget = forms.HiddenInput(attrs={'value': 'pendiente'})
                self.fields['estado_reserva'].choices = [
                    ('pendiente', 'Pendiente'),
                ]
                self.fields['estado_reserva'].initial = 'pendiente'
                self.fields['estado_reserva'].required = False
            else:
                self.fields['estado_reserva'].empty_label = 'Seleccione un estado'
                self.fields['estado_reserva'].choices = [
                    ('', 'Seleccione un estado'),
                    ('pendiente', 'Pendiente'),
                    ('confirmada', 'Confirmada'),
                    ('cancelada', 'Cancelada'),
                ]

        for opt_field in ('cliente_nombre', 'cliente_email', 'cliente_documento', 'cliente_telefono', 'cliente_tipo_documento'):
            if opt_field in self.fields:
                self.fields[opt_field].required = False

        if self.instance.pk:
            for field_name in list(self.fields):
                if field_name not in ('numero_adultos', 'numero_menores', 'estado_reserva'):
                    self.fields.pop(field_name)
            self.fields['numero_adultos'].required = False
            self.fields['numero_menores'].required = False
            self.fields['numero_adultos'].widget.attrs.update({'min': '1', 'max': '10'})
            self.fields['numero_menores'].widget.attrs.update({'min': '0', 'max': '10'})

            if hasattr(self.instance, 'puede_modificar_personas') and not self.instance.puede_modificar_personas():
                self.fields['numero_adultos'].widget.attrs['readonly'] = 'readonly'
                self.fields['numero_menores'].widget.attrs['readonly'] = 'readonly'
                self.fields['numero_adultos'].help_text = 'La cantidad de personas no puede modificarse: la reserva tiene un pago registrado, está cancelada o faltan menos de 48 horas.'
                self.fields['numero_menores'].help_text = 'La cantidad de personas no puede modificarse: la reserva tiene un pago registrado, está cancelada o faltan menos de 48 horas.'

        if not self.instance.pk:
            fecha_minima = date.today() + timedelta(days=5)
            if 'fecha_inicio' in self.fields:
                self.fields['fecha_inicio'].widget.attrs['min'] = fecha_minima.strftime('%Y-%m-%d')

    def _validar_sin_inyeccion(self, valor, nombre_campo):
        if not valor:
            return valor
        texto = str(valor).strip()
        if PATRON_INYECCION.search(texto):
            raise ValidationError(f"El campo {nombre_campo} contiene caracteres o código no permitido por seguridad.")
        return texto

    def clean_tipo_cliente(self):
        tipo = (self.cleaned_data.get('tipo_cliente') or '').strip()
        if tipo and tipo not in MODALIDADES_CLIENTE_VALIDAS:
            raise ValidationError("La modalidad de cliente seleccionada no es válida.")
        return tipo

    def clean_cliente_nombre(self):
        nombre = self._validar_sin_inyeccion(self.cleaned_data.get('cliente_nombre'), 'nombre completo')
        if not nombre:
            return ''
        nombre = re.sub(r'\s+', ' ', nombre)
        if len(nombre) < 3 or len(nombre) > 150:
            raise ValidationError("El nombre completo debe tener entre 3 y 150 caracteres.")
        if not re.match(r'^[A-Za-záéíóúÁÉÍÓÚñÑüÜ\s]+$', nombre):
            raise ValidationError("El nombre solo puede contener letras y espacios (sin números ni símbolos especiales).")
        return nombre

    def clean_cliente_email(self):
        email = self._validar_sin_inyeccion(self.cleaned_data.get('cliente_email'), 'correo electrónico')
        if not email:
            return ''
        email = email.lower()
        if len(email) > 254 or not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError("Ingresa una dirección de correo electrónico con formato válido y seguro.")
        return email

    def clean_cliente_tipo_documento(self):
        tipo_doc = (self.cleaned_data.get('cliente_tipo_documento') or 'CC').strip().upper()
        if tipo_doc not in TIPOS_DOCUMENTO_VALIDOS:
            raise ValidationError("El tipo de documento seleccionado no es válido.")
        return tipo_doc

    def clean_cliente_documento(self):
        doc = self._validar_sin_inyeccion(self.cleaned_data.get('cliente_documento'), 'número de documento')
        if not doc:
            return ''
        if not re.match(r'^[0-9]{5,20}$', doc):
            raise ValidationError("El número de documento debe contener únicamente números (entre 5 y 20 dígitos).")
        return doc

    def clean_cliente_telefono(self):
        tel = self._validar_sin_inyeccion(self.cleaned_data.get('cliente_telefono'), 'teléfono')
        if not tel:
            return ''
        if not re.match(r'^\+?[0-9]{7,15}$', tel):
            raise ValidationError("El teléfono solo puede contener números (entre 7 y 15 dígitos, opcional prefijo '+').")
        return tel

    def clean_paquete(self):
        paquete = self.cleaned_data.get('paquete')
        if not paquete:
            raise ValidationError("Debes seleccionar un paquete turístico válido.")
        if not getattr(paquete, 'estado', True):
            raise ValidationError("El paquete seleccionado no se encuentra activo ni disponible para reservas.")
        return paquete

    def clean_usuario(self):
        usuario = self.cleaned_data.get('usuario')
        if usuario:
            if not usuario.is_active:
                raise ValidationError("El usuario seleccionado se encuentra inactivo.")
            if getattr(usuario, 'rol', None) != Usuario.Roles.CLIENTE:
                raise ValidationError("Solo se pueden asignar reservas a usuarios con rol de Cliente.")
        return usuario

    def clean_estado_reserva(self):
        estado = (self.cleaned_data.get('estado_reserva') or '').strip()
        if not self.instance.pk:
            return 'pendiente'
        return estado

    def clean_fecha_inicio(self):
        fecha_reserva = self.cleaned_data.get('fecha_inicio')

        if not fecha_reserva:
            raise ValidationError("Debes seleccionar una fecha de viaje válida en el calendario.")

        if self.instance.pk and self.instance.fecha_inicio == fecha_reserva:
            return fecha_reserva

        hoy = date.today()
        fecha_minima = hoy + timedelta(days=5)

        if fecha_reserva < hoy:
            raise ValidationError("No puedes seleccionar una fecha pasada.")

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
        if adultos > 10:
            raise ValidationError("El cupo de adultos no puede superar las 10 personas.")
        return adultos

    def clean_numero_menores(self):
        menores = self.cleaned_data.get('numero_menores')
        if self.instance.pk and menores is None:
            return self.instance.numero_menores
        if menores is None or menores < 0:
            raise ValidationError("El número de menores no puede ser negativo.")
        if menores > 10:
            raise ValidationError("El cupo de menores no puede superar las 10 personas.")
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

        if not self.instance.pk:
            cleaned_data['estado_reserva'] = 'pendiente'
            self.instance.estado_reserva = 'pendiente'

        raw_tipo = self.data.get('tipo_cliente')
        if raw_tipo and raw_tipo not in MODALIDADES_CLIENTE_VALIDAS:
            self.add_error('tipo_cliente', 'La modalidad de cliente fue alterada a un valor no permitido.')
            return cleaned_data

        tipo_cliente = cleaned_data.get('tipo_cliente') or ('presencial' if not cleaned_data.get('usuario') else 'registrado')
        usuario = cleaned_data.get('usuario')
        cliente_nombre = cleaned_data.get('cliente_nombre')
        cliente_email = cleaned_data.get('cliente_email')
        cliente_tipo_doc = cleaned_data.get('cliente_tipo_documento') or 'CC'
        cliente_doc = cleaned_data.get('cliente_documento')

        if tipo_cliente == 'registrado':
            if not usuario:
                self.add_error('usuario', 'Debes seleccionar un cliente registrado con cuenta.')
            cleaned_data['cliente_nombre'] = None
            cleaned_data['cliente_email'] = None
            cleaned_data['cliente_telefono'] = None
            cleaned_data['cliente_documento'] = None
            self.instance.es_presencial = False
        else:
            cleaned_data['usuario'] = None
            self.instance.usuario = None
            self.instance.es_presencial = True

            cliente_telefono = cleaned_data.get('cliente_telefono')
            if not cliente_nombre:
                if 'cliente_nombre' not in self.errors:
                    self.add_error('cliente_nombre', 'El nombre completo del cliente presencial es obligatorio.')
            if not cliente_email:
                if 'cliente_email' not in self.errors:
                    self.add_error('cliente_email', 'El correo electrónico es obligatorio para el registro y envío de información.')
            if not cliente_tipo_doc:
                if 'cliente_tipo_documento' not in self.errors:
                    self.add_error('cliente_tipo_documento', 'El tipo de documento es obligatorio.')
            if not cliente_doc:
                if 'cliente_documento' not in self.errors:
                    self.add_error('cliente_documento', 'El número de documento es obligatorio.')
            elif not re.match(r'^[0-9]{5,20}$', str(cliente_doc)):
                self.add_error('cliente_documento', 'El número de documento debe contener únicamente números (entre 5 y 20 dígitos).')
            if not cliente_telefono:
                if 'cliente_telefono' not in self.errors:
                    self.add_error('cliente_telefono', 'El teléfono de contacto es obligatorio.')

        paquete = cleaned_data.get('paquete')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        adultos_val = adultos or 0
        menores_val = menores or 0

        if adultos_val + menores_val <= 0:
            raise ValidationError("La reserva debe incluir al menos una persona.")

        if paquete and fecha_inicio:
            # Validar en servidor (Zero-Trust contra manipulación en DevTools) que la fecha tenga temporada y tarifa activa
            tiene_tarifa = Tarifa.objects.filter(
                paquete=paquete,
                estado=True,
                temporada__estado=True,
                temporada__fecha_inicio__lte=fecha_inicio,
                temporada__fecha_fin__gte=fecha_inicio,
            ).exists()
            if not tiene_tarifa:
                self.add_error(
                    'fecha_inicio',
                    'No hay una temporada o tarifa activa disponible para este paquete en la fecha indicada.'
                )

            if tipo_cliente == 'registrado' and usuario:
                qs = Reserva.objects.filter(usuario=usuario, paquete=paquete, fecha_inicio=fecha_inicio)
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError("Este usuario ya tiene una reserva registrada para el mismo paquete en la fecha seleccionada.")
            elif tipo_cliente == 'presencial' and cliente_email:
                qs = Reserva.objects.filter(cliente_email__iexact=cliente_email.strip(), paquete=paquete, fecha_inicio=fecha_inicio)
                if self.instance.pk:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise ValidationError("Ya existe una reserva presencial registrada con este correo para el mismo paquete en la fecha seleccionada.")

        return cleaned_data

    def validate_unique(self):
        super().validate_unique()
        # Consolidar mensajes duplicados de unicidad para evitar que aparezca el mensaje genérico y técnico de Django
        if self._errors and forms.forms.NON_FIELD_ERRORS in self._errors:
            mensajes_unicos = []
            ya_existe_reserva = False
            for err in self._errors[forms.forms.NON_FIELD_ERRORS]:
                texto_err = str(err)
                if 'Ya existe un/a Reserva con este/a Usuario' in texto_err or 'Este usuario ya tiene una reserva' in texto_err:
                    if not ya_existe_reserva:
                        mensajes_unicos.append("Este usuario ya tiene una reserva registrada para el mismo paquete en la fecha seleccionada.")
                        ya_existe_reserva = True
                else:
                    if texto_err not in mensajes_unicos:
                        mensajes_unicos.append(texto_err)
            self._errors[forms.forms.NON_FIELD_ERRORS] = self.error_class(mensajes_unicos)
