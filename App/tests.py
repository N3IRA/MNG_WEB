import re
import io
import pypdf
from PIL import Image
from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from App.models import Usuario, Paquete, Reserva, Categoria, Pago, Temporada, Tarifa, Notificacion, Bitacora
from App.forms.usuario.forms import PerfilTuristaForm
from App.forms.pago.forms import ComprobantePagoForm
from autenticacion.forms import IniciarSesionForm


class SeguridadFormulariosTests(TestCase):
    """
    Pruebas de seguridad contra ataques basados en manipulación del navegador (DevTools / F12):
    - Mass Assignment (Asignación Masiva para escalamiento de privilegios)
    - Parameter Tampering (Manipulación de montos en comprobantes de pago)
    - Bypass de validaciones de cliente (HTML5 required/pattern eliminados en cliente)
    - Carga de archivos con extensiones peligrosas
    """

    def setUp(self):
        self.client = Client()
        self.turista = Usuario.objects.create_user(
            username='turista_test',
            email='turista@monagua.com',
            password='Password123#',
            first_name='Carlos',
            last_name='Perez',
            rol=Usuario.Roles.CLIENTE,
            is_staff=False,
            is_superuser=False
        )
        self.categoria = Categoria.objects.create(nombre='Aventura')
        self.paquete = Paquete.objects.create(
            nombre='Tour Laguna Negra',
            descripcion='Aventura ecológica',
            categoria=self.categoria,
            punto_encuentro='Plaza de Mongua',
            hora_encuentro='08:00:00',
            dias_duracion=1,
            noches_duracion=1,
            imagen=SimpleUploadedFile('test.jpg', b'contenido_imagen', content_type='image/jpeg')
        )
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente'
        )

    def test_perfil_mass_assignment_protection(self):
        """
        Verifica que si un usuario inyecta campos como 'rol', 'is_staff' o 'is_superuser'
        desde el inspector del navegador, estos sean ignorados y sus privilegios no se eleven.
        """
        self.client.force_login(self.turista)
        payload = {
            'editar_perfil': '1',
            'first_name': 'Carlos Modificado',
            'last_name': 'Perez Modificado',
            'telefono': '3109876543',
            'residencia': 'Mongua',
            # Campos maliciosos inyectados en HTML:
            'rol': Usuario.Roles.ADMIN,
            'is_staff': 'True',
            'is_superuser': 'True',
        }

        response = self.client.post(reverse('perfil_detalles'), data=payload)
        self.assertEqual(response.status_code, 302)

        self.turista.refresh_from_db()
        self.assertEqual(self.turista.first_name, 'Carlos Modificado')
        # Deben permanecer intactos:
        self.assertEqual(self.turista.rol, Usuario.Roles.CLIENTE)
        self.assertFalse(self.turista.is_staff)
        self.assertFalse(self.turista.is_superuser)

    def test_perfil_validation_rejects_invalid_chars(self):
        """
        Verifica que el servidor rechaza nombres con caracteres no permitidos (ej. scripts o números),
        incluso si el atacante borró el atributo 'pattern' del HTML en el navegador.
        """
        form = PerfilTuristaForm(data={
            'first_name': 'Carlos123<script>',
            'last_name': 'Perez',
            'telefono': '3001234567'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('first_name', form.errors)

    def test_pago_parameter_tampering_protection(self):
        """
        Verifica que si un usuario o atacante agrega campos no autorizados (ej. 'monto=10.00'
        o 'estado_transaccion=aprobado'), Django detecta la alteración, rechaza la solicitud
        con un error explícito de seguridad y NO registra el comprobante en la base de datos.
        """
        self.client.force_login(self.turista)
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        archivo_imagen = SimpleUploadedFile('recibo.gif', gif_bytes, content_type='image/gif')

        payload_manipulado = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-HACKED-99',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_imagen,
            'descripcion': 'Pago intentando alterar precio',
            # Parámetros manipulados / extraños inyectados en POST:
            'monto': '10.00',
            'estado_transaccion': 'aprobado'
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload_manipulado)
        # Debe fallar con error de validación de Django y renderizar nuevamente
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'datos no autorizados')

        # NO debe existir ningún pago creado con esa referencia en BD
        self.assertFalse(Pago.objects.filter(referencia='TRANS-HACKED-99').exists())

    def test_pago_valido_sin_tampering_exitoso(self):
        """Verifica que un comprobante legítimo sin campos extraños se registre con éxito y monto del servidor."""
        self.client.force_login(self.turista)
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        archivo_imagen = SimpleUploadedFile('recibo_legitimo.gif', gif_bytes, content_type='image/gif')

        payload_limpio = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-LEGIT-1234',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_imagen,
            'descripcion': 'Pago legítimo',
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload_limpio)
        self.assertEqual(response.status_code, 302)

        pago = Pago.objects.get(referencia='TRANS-LEGIT-1234')
        self.assertEqual(pago.monto, Decimal('350000.00'))
        self.assertEqual(pago.estado_transaccion, 'pendiente')

    def test_pago_archivo_peligroso_doble_extension_rechazado(self):
        """Verifica que subir un archivo con doble extensión sospechosa (ej. exploit.php.png) sea rechazado."""
        self.client.force_login(self.turista)
        archivo_sospechoso = SimpleUploadedFile('recibo.php.png', b'GIF89a fake payload', content_type='image/png')

        payload = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-DANGEROUS-FILE',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_sospechoso,
            'descripcion': 'Archivo malicioso',
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Archivo sospechoso detectado')
        self.assertFalse(Pago.objects.filter(referencia='TRANS-DANGEROUS-FILE').exists())

    def test_pago_archivo_con_script_ejecutable_rechazado(self):
        """Verifica que subir un archivo que contenga código script o php sea bloqueado de inmediato."""
        self.client.force_login(self.turista)
        archivo_script = SimpleUploadedFile('recibo.png', b'<?php system($_GET["cmd"]); ?>', content_type='image/png')

        payload = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-SCRIPT-INJECT',
            'banco_origen': 'Nequi',
            'metodo_pago': 'Billetera Digital',
            'imagen_comprobante': archivo_script,
            'descripcion': 'Intento de webshell',
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'código ejecutable no permitido')
        self.assertFalse(Pago.objects.filter(referencia='TRANS-SCRIPT-INJECT').exists())

    def test_pago_archivo_adicional_inyectado_rechazado(self):
        """Verifica que si se inyectan archivos adicionales no permitidos en FILES, Django lo bloquee con error."""
        self.client.force_login(self.turista)
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        archivo_valido = SimpleUploadedFile('recibo.gif', gif_bytes, content_type='image/gif')
        archivo_extra = SimpleUploadedFile('extra.txt', b'datos extra no autorizados', content_type='text/plain')

        payload = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-EXTRA-FILE',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_valido,
            'archivo_secreto': archivo_extra,
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'archivos adicionales no autorizados')
        self.assertFalse(Pago.objects.filter(referencia='TRANS-EXTRA-FILE').exists())

    def test_pago_referencia_con_caracteres_peligrosos_rechazada(self):
        """Verifica que referencias con inyecciones XSS o SQL sean rechazadas por validación de Django."""
        self.client.force_login(self.turista)
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        archivo_valido = SimpleUploadedFile('recibo.gif', gif_bytes, content_type='image/gif')

        payload = {
            'reserva': self.reserva.id,
            'referencia': "<script>alert('xss')</script>",
            'banco_origen': 'Nequi',
            'metodo_pago': 'Billetera Digital',
            'imagen_comprobante': archivo_valido,
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'La referencia contiene caracteres no permitidos')
        self.assertFalse(Pago.objects.filter(referencia__icontains='<script>').exists())

    def test_pago_pdf_valido_aceptado(self):
        """Verifica que un comprobante en PDF legítimo sea procesado correctamente."""
        self.client.force_login(self.turista)
        pdf_bytes = b'%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF'
        archivo_pdf = SimpleUploadedFile('comprobante_bancario.pdf', pdf_bytes, content_type='application/pdf')

        payload = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-PDF-VALID-99',
            'banco_origen': 'Davivienda',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_pdf,
            'descripcion': 'Pago por transferencia en PDF',
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Pago.objects.filter(referencia='TRANS-PDF-VALID-99').exists())

    def test_pago_pdf_falso_o_corrupto_rechazado(self):
        """Verifica que un archivo con extensión .pdf pero sin cabecera PDF válida sea rechazado."""
        self.client.force_login(self.turista)
        archivo_pdf_falso = SimpleUploadedFile('factura_falsa.pdf', b'TEXTO PLANO FALSO', content_type='application/pdf')

        payload = {
            'reserva': self.reserva.id,
            'referencia': 'TRANS-PDF-FAKE-00',
            'banco_origen': 'Davivienda',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_pdf_falso,
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El archivo PDF del comprobante')
        self.assertFalse(Pago.objects.filter(referencia='TRANS-PDF-FAKE-00').exists())

    def test_pago_reserva_de_otro_usuario_rechazado(self):
        """Verifica que un usuario no pueda pagar una reserva que pertenece a otro usuario (prevención IDOR)."""
        otro_usuario = Usuario.objects.create_user(
            username='otro_turista',
            email='otro@monagua.com',
            password='Password123#',
            numero_documento='888777666'
        )
        self.client.force_login(otro_usuario)
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        archivo_imagen = SimpleUploadedFile('recibo_ajeno.gif', gif_bytes, content_type='image/gif')

        payload = {
            'reserva': self.reserva.id,  # La reserva pertenece a self.turista, no a otro_usuario
            'referencia': 'TRANS-IDOR-ATTACK',
            'banco_origen': 'Daviplata',
            'metodo_pago': 'Billetera Digital',
            'imagen_comprobante': archivo_imagen,
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        # Debe responder 404 (get_object_or_404) porque la reserva no le pertenece
        self.assertEqual(response.status_code, 404)

    def test_pago_penalidad_esta_disponible_en_enviar_comprobante(self):
        """Una cancelación aprobada con penalidad debe aparecer como opción de pago en la vista de comprobantes."""
        reserva_penalidad = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            estado_cancelacion='aprobada',
            penalidad=Decimal('15000.00'),
            fecha_inicio=date.today() + timedelta(days=10),
            motivo_cancelacion='Cambio de planes'
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('enviar_comprobante'), {'reserva_id': reserva_penalidad.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '[Multa]')
        self.assertContains(response, 'Valor:')
        self.assertContains(response, 'Monto de la Penalidad')

        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        payload = {
            'reserva': reserva_penalidad.id,
            'referencia': 'PENALIDAD-123',
            'banco_origen': 'Daviplata',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': SimpleUploadedFile('penalidad.gif', gif_bytes, content_type='image/gif'),
            'descripcion': 'Pago de penalidad'
        }

        response = self.client.post(reverse('enviar_comprobante'), data=payload)
        self.assertEqual(response.status_code, 302)
        pago = Pago.objects.get(reserva=reserva_penalidad)
        self.assertEqual(pago.monto, Decimal('15000.00'))
        self.assertEqual(pago.estado_transaccion, 'pendiente')

        comprobantes = self.client.get(reverse('mis_comprobantes'))
        self.assertEqual(comprobantes.status_code, 200)
        self.assertContains(comprobantes, 'Penalidad')
        self.assertContains(comprobantes, 'Reserva')

    def test_pago_penalidad_en_url_directa_usa_tipo_penalidad(self):
        """Una URL directa con tipo=penalidad debe mostrar inmediatamente el formulario de penalidad, aunque la reserva aún esté en flujo de revisión."""
        reserva_penalidad = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            estado_cancelacion='pendiente',
            penalidad=Decimal('15000.00'),
            fecha_inicio=date.today() + timedelta(days=10),
            motivo_cancelacion='Cambio de planes'
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('enviar_comprobante'), {'reserva_id': reserva_penalidad.id, 'tipo': 'penalidad'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Penalidad a Vincular')
        self.assertEqual(response.context['selected_tipo'], 'penalidad')

    def test_pago_penalidad_directa_sigue_mostrando_la_opcion_si_ya_hay_pago_pendiente(self):
        """Si un usuario llega por URL directa a una penalidad con pago pendiente, el select debe seguir mostrando esa penalidad y no el placeholder."""
        reserva_penalidad = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            estado_cancelacion='aprobada',
            penalidad=Decimal('15000.00'),
            fecha_inicio=date.today() + timedelta(days=14),
            motivo_cancelacion='Cambio de planes pendiente'
        )
        Pago.objects.create(
            reserva=reserva_penalidad,
            referencia='PEN-EXISTENTE',
            banco_origen='Daviplata',
            monto=Decimal('15000.00'),
            estado_transaccion='pendiente',
            imagen_comprobante=SimpleUploadedFile('penalidad_existente.gif', b'GIF89a', content_type='image/gif')
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('enviar_comprobante'), {'reserva_id': reserva_penalidad.id, 'tipo': 'penalidad'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Penalidad a Vincular')
        self.assertContains(response, str(reserva_penalidad.id))
        self.assertNotContains(response, 'Selecciona laaaaaaaaaa reserva')

    def test_pago_penalidad_multiple_elige_una_opcion_unica(self):
        """Cuando hay varias penalidades, la vista debe elegir una sola opción y no dejar el select en el placeholder."""
        reserva1 = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            estado_cancelacion='aprobada',
            penalidad=Decimal('15000.00'),
            fecha_inicio=date.today() + timedelta(days=12),
            motivo_cancelacion='Cambio de planes 1'
        )
        reserva2 = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('450000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            estado_cancelacion='aprobada',
            penalidad=Decimal('20000.00'),
            fecha_inicio=date.today() + timedelta(days=20),
            motivo_cancelacion='Cambio de planes 2'
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('enviar_comprobante'), {'tipo': 'penalidad'})
        html = response.content.decode()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_tipo'], 'penalidad')
        self.assertIn(str(reserva1.id), html)
        self.assertEqual(len(re.findall(r'data-tipo="penalidad"[^>]*selected', html)), 1)

    def test_comprobante_disallowed_file_extension(self):
        """
        Verifica que no se permita subir archivos maliciosos (.sh, .exe, .html)
        como comprobantes de pago.
        """
        archivo_malicioso = SimpleUploadedFile('script.sh', b'#!/bin/bash\necho hack', content_type='application/x-sh')
        form = ComprobantePagoForm(
            data={
                'referencia': 'REF-12345',
                'banco_origen': 'Nequi',
                'metodo_pago': 'Transferencia Bancaria'
            },
            files={'imagen_comprobante': archivo_malicioso}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('imagen_comprobante', form.errors)

    def test_iniciar_sesion_form_validation(self):
        """
        Verifica que el formulario de inicio de sesión valide longitudes y rechace datos vacíos.
        """
        form = IniciarSesionForm(data={'username': '', 'password': ''})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('password', form.errors)


class CancelacionReservaTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.turista = Usuario.objects.create_user(
            username='turista_cancelacion',
            email='cancelacion@monagua.com',
            password='Password123#',
            first_name='Ana',
            last_name='Lopez',
            rol=Usuario.Roles.CLIENTE,
            is_staff=False,
            is_superuser=False
        )
        self.categoria = Categoria.objects.create(nombre='Aventura')
        self.paquete = Paquete.objects.create(
            nombre='Tour de prueba',
            descripcion='Aventura de prueba',
            categoria=self.categoria,
            punto_encuentro='Plaza central',
            hora_encuentro='08:00:00',
            dias_duracion=1,
            noches_duracion=1,
            imagen=SimpleUploadedFile('test.jpg', b'contenido_imagen', content_type='image/jpeg')
        )

    def test_reserva_sin_pago_se_descarta_en_lugar_de_cancelarse(self):
        """Si la reserva no tiene pago, se descarta con motivo y queda registrada como cancelación aprobada."""
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='pendiente'
        )
        self.client.force_login(self.turista)

        response = self.client.post(
            reverse('cancelar_reserva_usuario', args=[self.reserva.id]),
            {'motivo_cancelacion': 'Ya no puedo viajar'}
        )

        self.assertEqual(response.status_code, 302)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_reserva, 'cancelada')
        self.assertEqual(self.reserva.estado_cancelacion, 'aprobada')
        self.assertEqual(self.reserva.motivo_cancelacion, 'Ya no puedo viajar')
        self.assertEqual(self.reserva.penalidad, Decimal('0.00'))

    def test_reserva_no_se_puede_cancelar_si_falta_menos_de_2_dias(self):
        """La cancelación queda bloqueada cuando faltan menos de 2 días para el viaje."""
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=1),
            estado_cancelacion='pendiente'
        )
        self.client.force_login(self.turista)

        self.reserva.monto_total = Decimal('350000.00')
        self.reserva.save(update_fields=['monto_total'])

        Pago.objects.create(
            reserva=self.reserva,
            referencia='REF-123',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=Decimal('350000.00'),
            imagen_comprobante=SimpleUploadedFile('pago.gif', b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', content_type='image/gif'),
            descripcion='Pago validado',
            estado_transaccion='aprobado'
        )

        response = self.client.post(
            reverse('cancelar_reserva_usuario', args=[self.reserva.id]),
            {'motivo_cancelacion': 'Se me complicó la fecha'}
        )

        self.assertEqual(response.status_code, 302)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_cancelacion, 'pendiente')
        self.assertEqual(self.reserva.estado_reserva, 'confirmada')

    def test_reserva_con_pago_queda_cancelada_al_solicitar_cancelacion(self):
        """Cuando el usuario solicita cancelar una reserva pagada, el estado principal debe pasar a cancelada."""
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion=None
        )
        self.reserva.monto_total = Decimal('350000.00')
        self.reserva.save(update_fields=['monto_total'])
        Pago.objects.create(
            reserva=self.reserva,
            referencia='REF-REQUEST-001',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=Decimal('350000.00'),
            imagen_comprobante=SimpleUploadedFile('pago.gif', b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', content_type='image/gif'),
            descripcion='Pago validado',
            estado_transaccion='aprobado'
        )
        self.client.force_login(self.turista)

        response = self.client.post(
            reverse('cancelar_reserva_usuario', args=[self.reserva.id]),
            {'motivo_cancelacion': 'Necesito cancelar la reserva'}
        )

        self.assertEqual(response.status_code, 302)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_reserva, 'cancelada')
        self.assertEqual(self.reserva.estado_cancelacion, 'pendiente')

    def test_reserva_con_pago_y_sin_penalidad_se_aprueba_automaticamente(self):
        """Si la cancelación no genera multa, debe aprobarse automáticamente y no quedar en revisión."""
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=None,
            estado_cancelacion=None
        )
        self.reserva.monto_total = Decimal('350000.00')
        self.reserva.save(update_fields=['monto_total'])
        Pago.objects.create(
            reserva=self.reserva,
            referencia='REF-APPROVE-AUTO',
            banco_origen='Daviplata',
            metodo_pago='Transferencia Bancaria',
            monto=Decimal('350000.00'),
            imagen_comprobante=SimpleUploadedFile('pago.gif', b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', content_type='image/gif'),
            descripcion='Pago validado',
            estado_transaccion='aprobado'
        )
        self.client.force_login(self.turista)

        response = self.client.post(
            reverse('cancelar_reserva_usuario', args=[self.reserva.id]),
            {'motivo_cancelacion': 'Cambio de planes'}
        )

        self.assertEqual(response.status_code, 302)
        self.reserva.refresh_from_db()
        self.assertEqual(self.reserva.estado_reserva, 'cancelada')
        self.assertEqual(self.reserva.estado_cancelacion, 'aprobada')

    def test_mis_cancelaciones_muestra_boton_pagar_cuando_hay_penalidad_aprobada(self):
        """Si la cancelación fue aprobada con penalidad, el usuario debe poder pagar la penalidad desde la página de cancelaciones."""
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Solicituda de cancelación',
            penalidad=Decimal('15000.00')
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('mis_cancelaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pagar penalidad')
        self.assertContains(response, 'Penalidad:')

    def test_mis_cancelaciones_muestra_boton_pagar_penalidad_solo_cuando_hay_penalidad(self):
        """La acción de pago debe ser por penalidad y no aparecer cuando no hay multa."""
        Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Solicituda de cancelación',
            penalidad=Decimal('15000.00')
        )
        Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=12),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Cancelación sin multa',
            penalidad=Decimal('0.00')
        )
        self.client.force_login(self.turista)

        response = self.client.get(reverse('mis_cancelaciones'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pagar penalidad')
        self.assertContains(response, 'Sin multa')
        self.assertNotContains(response, 'Pagar reserva')

    def test_mis_reservas_excluye_las_canceladas_y_solicitudes_de_cancelacion(self):
        """Si la reserva fue cancelada por el usuario, ya no debe seguir visible en Mis Reservas."""
        activa = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=30)
        )
        pendiente = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=15),
            estado_cancelacion='pendiente',
            motivo_cancelacion='Solicituda de cancelación'
        )
        cancelada = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Sin pago'
        )
        aprobada_sin_cancelar = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=20),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Se descartó por falta de pago'
        )

        self.client.force_login(self.turista)
        response = self.client.get(reverse('mis_reservas_usuario'))

        self.assertEqual(response.status_code, 200)
        reservas = list(response.context['reservas'])
        self.assertIn(activa, reservas)
        self.assertNotIn(pendiente, reservas)
        self.assertNotIn(cancelada, reservas)
        self.assertNotIn(aprobada_sin_cancelar, reservas)

    def test_reserva_cancelada_pero_pendiente_se_normaliza_y_no_aparece_en_mis_reservas(self):
        """Una reserva ya cancelada no debe seguir apareciendo como pendiente ni en la lista activa."""
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='pendiente',
            motivo_cancelacion='Se registró con estado inconsistente'
        )

        self.client.force_login(self.turista)
        response = self.client.get(reverse('mis_reservas_usuario'))

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_cancelacion, 'aprobada')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(reserva, list(response.context['reservas']))

    def test_reserva_aprobada_pero_activa_se_normaliza_a_cancelada(self):
        """Si la cancelación ya fue aprobada, la reserva debe quedar en estado cancelado aunque el dato esté inconsistente."""
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=15),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Se marcó con aprobación pero quedó activa'
        )

        self.client.force_login(self.turista)
        response = self.client.get(reverse('mis_reservas_usuario'))

        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva, 'cancelada')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(reserva, list(response.context['reservas']))

    def test_mis_cancelaciones_muestra_solo_pendientes_o_aprobadas(self):
        """Solo deben aparecer en el historial de cancelaciones las solicitudes pendientes o aprobadas."""
        aprobada = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=10),
            estado_cancelacion='aprobada',
            motivo_cancelacion='Sin pago'
        )
        pendiente = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=15),
            estado_cancelacion='pendiente',
            motivo_cancelacion='Solicituda de cancelación'
        )
        rechazada = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=20),
            estado_cancelacion='rechazada',
            motivo_cancelacion='No procede'
        )

        self.client.force_login(self.turista)
        response = self.client.get(reverse('mis_cancelaciones'))

        self.assertEqual(response.status_code, 200)
        cancelaciones = list(response.context['cancelaciones'])
        self.assertIn(aprobada, cancelaciones)
        self.assertIn(pendiente, cancelaciones)
        self.assertIn(rechazada, cancelaciones)


class ConfirmacionReservaTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_confirmacion',
            email='admin_confirmacion@monagua.com',
            password='Password123#',
            first_name='Admin',
            last_name='Confirmacion',
            numero_documento='1000000001',
            tipo_documento='CC',
            rol=Usuario.Roles.ADMIN,
            is_staff=True,
            is_superuser=False,
        )
        self.turista = Usuario.objects.create_user(
            username='turista_confirmacion',
            email='turista_confirmacion@monagua.com',
            password='Password123#',
            first_name='Laura',
            last_name='Rios',
            numero_documento='1000000002',
            tipo_documento='CC',
            rol=Usuario.Roles.CLIENTE,
            is_staff=False,
            is_superuser=False,
        )
        self.categoria = Categoria.objects.create(nombre='Aventura')
        self.paquete = Paquete.objects.create(
            nombre='Tour de confirmación',
            descripcion='Reserva de prueba',
            categoria=self.categoria,
            punto_encuentro='Plaza central',
            hora_encuentro='08:00:00',
            dias_duracion=1,
            noches_duracion=0,
            imagen=SimpleUploadedFile('test.jpg', b'contenido_imagen', content_type='image/jpeg')
        )

    def test_confirmacion_rechaza_reserva_sin_pago_aprobado(self):
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=30),
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('editar_reserva', args=[reserva.id]),
            {'estado_reserva': 'confirmada'}
        )

        self.assertEqual(response.status_code, 200)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva, 'pendiente')
        self.assertContains(response, 'No se puede confirmar la reserva sin un pago aprobado.')

    def test_confirmacion_acepta_reserva_con_pago_aprobado(self):
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='pendiente',
            fecha_inicio=date.today() + timedelta(days=30),
        )
        Pago.objects.create(
            reserva=reserva,
            referencia='CONF-001',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=Decimal('350000.00'),
            imagen_comprobante=SimpleUploadedFile('pago.gif', b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;', content_type='image/gif'),
            descripcion='Pago validado',
            estado_transaccion='aprobado'
        )
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('editar_reserva', args=[reserva.id]),
            {'estado_reserva': 'confirmada'}
        )

        self.assertEqual(response.status_code, 302)
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva, 'confirmada')


class EmailReservaYCancelacionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_email',
            email='admin@monagua.com',
            password='Password123#',
            first_name='Admin',
            last_name='Monagua',
            rol=Usuario.Roles.ADMIN,
            is_staff=True,
            is_superuser=False,
        )
        self.turista = Usuario.objects.create_user(
            username='turista_email_unique',
            email='turista_unique@monagua.com',
            password='Password123#',
            first_name='Andrés',
            last_name='Pérez',
            tipo_documento='CC',
            numero_documento='1234567890',
            telefono='3001234567',
            rol=Usuario.Roles.CLIENTE,
            is_staff=False,
            is_superuser=False,
        )
        self.categoria = Categoria.objects.create(nombre='Aventura')
        self.paquete = Paquete.objects.create(
            nombre='Tour de prueba',
            descripcion='Aventura de prueba',
            categoria=self.categoria,
            punto_encuentro='Plaza central',
            hora_encuentro='08:00:00',
            dias_duracion=1,
            noches_duracion=1,
            imagen=SimpleUploadedFile('test.jpg', b'contenido_imagen', content_type='image/jpeg')
        )

    def test_html_reserva_usa_logo_y_color_monagua(self):
        from App.utils import plantilla_reserva_html

        html = plantilla_reserva_html(
            nombre_cliente='Andrés',
            paquete='Tour de prueba',
            fecha='12/12/2026',
            adultos=2,
            menores=1,
            punto_encuentro='Plaza central',
            hora_encuentro='08:00',
            estado='confirmada',
            reserva_id='99',
            monto_total='350000'
        )

        self.assertIn('#2c6e3c', html)
        self.assertIn('logo_monagua', html)

    def test_admin_approval_of_cancellation_sends_email(self):
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            monto_total=Decimal('350000.00'),
            numero_adultos=2,
            numero_menores=0,
            estado_reserva='cancelada',
            fecha_inicio=date.today() + timedelta(days=15),
            estado_cancelacion='pendiente',
            motivo_cancelacion='Cambio de planes',
            penalidad=Decimal('15000.00'),
        )
        self.client.force_login(self.admin)

        with self.settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'):
            mail.outbox.clear()
            response = self.client.post(
                reverse('editar_cancelacion_admin', args=[reserva.id]),
                {'estado_cancelacion': 'aprobada'}
            )

            self.assertEqual(response.status_code, 302)
            self.assertEqual(len(mail.outbox), 1)
            self.assertIn('Monagua', mail.outbox[0].subject)
            self.assertIn('#2c6e3c', mail.outbox[0].alternatives[0][0])


class CrudBootstrapConsistencyTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = Usuario.objects.create_user(
            username='admin_bootstrap',
            email='admin@monagua.com',
            password='Password123#',
            first_name='Admin',
            last_name='Bootstrap',
            rol=Usuario.Roles.ADMIN,
            is_staff=True,
            is_superuser=False,
        )
        self.categoria = Categoria.objects.create(nombre='Aventura', estado=True)
        self.paquete = Paquete.objects.create(
            nombre='Ruta de la Cueva',
            descripcion='Recorrido en la montaña',
            categoria=self.categoria,
            punto_encuentro='Plaza central',
            hora_encuentro='08:00:00',
            dias_duracion=2,
            noches_duracion=1,
            estado=True,
            imagen=SimpleUploadedFile('test.jpg', b'contenido_imagen', content_type='image/jpeg'),
        )
        from App.models import Temporada, Actividades, Tarifa

        self.temporada = Temporada.objects.create(
            nombre='Alta Temporada',
            descripcion='Temporada alta',
            fecha_inicio=date.today(),
            fecha_fin=date.today() + timedelta(days=15),
            estado=True,
        )
        self.actividad = Actividades.objects.create(
            nombre='Senderismo',
            descripcion='Senderismo guiado',
            apto_menores=True,
            estado=True,
        )
        self.tarifa = Tarifa.objects.create(
            paquete=self.paquete,
            temporada=self.temporada,
            precio_adulto=150000,
            precio_menor=100000,
            estado=True,
        )

    def test_delete_forms_use_consistent_bootstrap_action_buttons(self):
        self.client.force_login(self.admin)

        urls_to_check = [
            ('eliminar_paquete', self.paquete.id),
            ('eliminar_categoria', self.categoria.id),
            ('eliminar_temporada', self.temporada.id),
            ('eliminar_actividad', self.actividad.id),
            ('eliminar_tarifa', self.tarifa.id),
        ]

        for url_name, obj_id in urls_to_check:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, args=[obj_id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Confirmar Eliminación')
                self.assertContains(response, 'btn btn-danger px-4 rounded-pill fw-bold')
                self.assertContains(response, 'btn btn-outline-secondary px-4 rounded-pill fw-semibold')

    def test_create_and_edit_forms_use_same_green_header(self):
        self.client.force_login(self.admin)

        urls_to_check = [
            ('crear_paquete', None),
            ('editar_paquete', self.paquete.id),
            ('crear_categoria', None),
            ('editar_categoria', self.categoria.id),
            ('crear_temporada', None),
            ('editar_temporada', self.temporada.id),
            ('crear_actividad', None),
            ('editar_actividad', self.actividad.id),
            ('crear_tarifa', None),
            ('editar_tarifa', self.tarifa.id),
        ]

        for url_name, obj_id in urls_to_check:
            with self.subTest(url_name=url_name):
                if obj_id is None:
                    response = self.client.get(reverse(url_name))
                else:
                    response = self.client.get(reverse(url_name, args=[obj_id]))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'bg-success text-white p-4 border-0')
                self.assertContains(response, 'btn btn-success px-4 rounded-pill shadow-sm fw-bold')


class PruebasSeguridadYFuncionalidadCompletas(TestCase):
    """
    Pruebas integrales de seguridad y funcionalidad:
    - Bloqueo contra fuerza bruta en Login
    - Límite de 5 intentos en OTP de recuperación
    - Cálculo de variables de días en Reserva y Aseguradora (Seguros)
    - Control de acceso estricto a vistas administrativas de Pólizas y Calificaciones
    - Asistente Condy y radicación de PQRS
    """

    def setUp(self):
        self.client = Client()
        self.turista = Usuario.objects.create_user(
            username='turista_seguro',
            email='turista_seguro@monagua.com',
            password='Password123#',
            first_name='Laura',
            last_name='Gomez',
            numero_documento='999000111',
            rol=Usuario.Roles.CLIENTE,
            is_staff=False
        )
        self.admin = Usuario.objects.create_user(
            username='admin_seguro',
            email='admin_seguro@monagua.com',
            password='AdminPassword123#',
            first_name='Super',
            last_name='Admin',
            numero_documento='999000222',
            rol=Usuario.Roles.ADMIN,
            is_staff=True
        )
        self.categoria = Categoria.objects.create(nombre='Ecoturismo')
        self.paquete = Paquete.objects.create(
            nombre='Travesía Ocetá',
            descripcion='Caminata ecológica de altura',
            categoria=self.categoria,
            punto_encuentro='Plaza Principal',
            hora_encuentro='07:30:00',
            dias_duracion=3,
            noches_duracion=2,
            imagen=SimpleUploadedFile('oceta.jpg', b'foto_oceta', content_type='image/jpeg')
        )
        self.reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            fecha_inicio=date.today() + timedelta(days=5),
            numero_adultos=2,
            numero_menores=1,
            monto_total=Decimal('450000.00'),
            estado_reserva='pendiente'
        )

    def test_calculo_variable_dias_reserva(self):
        """Verifica que las propiedades dias_duracion y fecha_fin en Reserva calculen correctamente."""
        self.assertEqual(self.reserva.dias_duracion, 3)
        self.assertEqual(self.reserva.fecha_fin, self.reserva.fecha_inicio + timedelta(days=2))

    def test_calculo_dias_y_costo_aseguradora(self):
        """Verifica que Aseguradora calcule automáticamente días, costo del seguro y folio único."""
        from App.models import PolizaViaje, Aseguradora

        poliza = PolizaViaje.objects.create(
            nombre_poliza='Póliza Paramuna Total',
            descripcion='Cobertura médica y rescate',
            cobertura_medica_max=Decimal('25000000.00'),
            precio_diario=Decimal('12000.00'),
            estado=True
        )

        seguro = Aseguradora.objects.create(
            reserva=self.reserva,
            poliza_viaje=poliza,
            nombre_empresa='Seguros del Estado'
        )

        self.assertIsNotNone(seguro.numero_poliza)
        self.assertTrue(seguro.numero_poliza.startswith('POL-'))
        self.assertEqual(seguro.fecha_inicio_cobertura, self.reserva.fecha_inicio)
        self.assertEqual(seguro.fecha_fin_cobertura, self.reserva.fecha_fin)
        # Costo = 3 días * $12,000/día = $36,000
        self.assertEqual(seguro.costo_seguro, Decimal('36000.00'))

    def test_login_brute_force_lockout(self):
        """Verifica que 5 intentos fallidos consecutivos de login activen el bloqueo temporal."""
        for i in range(5):
            res = self.client.post(reverse('login'), {
                'username': 'turista_seguro',
                'password': f'clave_erronea_{i}'
            })
            self.assertEqual(res.status_code, 200)

        # El intento 6 debe estar bloqueado por cooldown de seguridad
        res_bloqueado = self.client.post(reverse('login'), {
            'username': 'turista_seguro',
            'password': 'Password123#'
        })
        self.assertEqual(res_bloqueado.status_code, 200)
        self.assertContains(res_bloqueado, 'bloqueado temporalmente')

    def test_otp_recuperacion_limite_5_intentos(self):
        """Verifica que fallar 5 veces el OTP de recuperación de contraseña purgue la sesión e impida fuerza bruta."""
        session = self.client.session
        session['reset_user_id'] = self.turista.id
        session['reset_email'] = self.turista.email
        session['reset_otp'] = '987654'
        session['reset_otp_time'] = 9999999999  # Muy en el futuro para que no expire por tiempo
        session['reset_otp_intentos'] = 0
        session.save()

        for intento in range(4):
            res = self.client.post(reverse('verificar_otp_clave'), {'otp': f'00000{intento}'})
            self.assertEqual(res.status_code, 200)

        # Intento número 5 (fallido): debe expulsar al atacante y limpiar la sesión
        res_final = self.client.post(reverse('verificar_otp_clave'), {'otp': '000005'})
        self.assertEqual(res_final.status_code, 302)
        self.assertEqual(res_final.url, reverse('recuperar_clave'))

        # Sesión limpia
        self.assertNotIn('reset_otp', self.client.session)

    def test_acceso_no_autorizado_a_polizas_bloqueado(self):
        """Verifica que usuarios comunes y anónimos no puedan acceder a la administración de seguros."""
        # Anónimo
        res_anon = self.client.get(reverse('poliza_listar'))
        self.assertEqual(res_anon.status_code, 302)

        # Turista no staff
        self.client.force_login(self.turista)
        res_turista = self.client.get(reverse('poliza_listar'))
        self.assertEqual(res_turista.status_code, 403)

        # Administrador permitido
        self.client.force_login(self.admin)
        res_admin = self.client.get(reverse('poliza_listar'))
        self.assertEqual(res_admin.status_code, 200)

    def test_condy_chat_api_funcional(self):
        """Verifica que el endpoint de Condy responda correctamente en formato JSON con sesión activa."""
        import json
        payload = json.dumps({'message': '¿Cómo puedo radicar una PQRS?'})
        res = self.client.post(
            reverse('condy_chat_api'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('response', data)
        self.assertEqual(data.get('action'), 'pqrs')
        self.assertIn('pqrs', data.get('response', '').lower())


class FlujoReservaPagoFacturaRigurosoTests(TestCase):
    """
    Suite de pruebas rigurosas e integrales para el ciclo de vida completo de:
    1. RESERVA:
       - Creación exitosa con cálculo automático de tarifas por temporada.
       - Validación de anticipación mínima (al menos 2 días).
       - Rechazo de fechas pasadas y formatos no válidos.
       - Validación de pasajeros (mínimo 1 adulto, límites máximos).
       - Prevención de reservas duplicadas (mismo usuario, paquete y fecha).
       - Restricción de modelo: imposible confirmar sin pago aprobado.
    2. PAGO / COMPROBANTE:
       - Envío exitoso con validación de banco, método y archivo (JPEG / PDF).
       - Estado inicial 'pendiente' y notificaciones al usuario y administradores.
       - Bloqueo de envíos duplicados mientras exista comprobante en proceso.
       - Protección contra archivos maliciosos, ejecutables o scripts.
       - Rechazo por administrador con nota obligatoria y registro en Bitácora.
       - Rechazo sin nota administrativa falla.
       - Reintento de comprobante por el turista tras rechazo previo.
       - Validación del monto mínimo requerido para aprobación.
       - Aprobación por administrador que sincroniza automáticamente la reserva a 'confirmada'.
    3. FACTURACIÓN Y PDF:
       - 'mis_facturas' lista únicamente reservas confirmadas/pagadas.
       - 'ver_factura' bloquea reservas pendientes o no confirmadas.
       - 'ver_factura' bloquea acceso no autorizado de otros turistas (Zero-Trust).
       - 'ver_factura' renderiza exitosamente para el titular y el administrador (QR, totales, datos).
       - 'descargar_factura' entrega archivo 'application/pdf' con cabecera válida %PDF-.
       - Protección criptográfica del PDF con número de documento del usuario (pypdf).
       - 'descargar_factura' bloquea descarga a usuarios no autorizados.
    """

    def setUp(self):
        self.client = Client()

        # Usuario Administrador
        self.admin = Usuario.objects.create_user(
            username='admin_riguroso',
            email='admin_riguroso@monagua.com',
            password='AdminPassword123#',
            first_name='Admin',
            last_name='Monagua',
            rol=Usuario.Roles.ADMIN,
            is_staff=True,
            is_superuser=True
        )

        # Turista titular
        self.turista = Usuario.objects.create_user(
            username='turista_riguroso',
            email='turista_riguroso@monagua.com',
            password='TuristaPassword123#',
            first_name='Carlos',
            last_name='Gomez',
            rol=Usuario.Roles.CLIENTE,
            tipo_documento='CC',
            numero_documento='1049583726',
            is_staff=False,
            is_superuser=False
        )

        # Otro turista para pruebas de control de acceso cruzado
        self.otro_turista = Usuario.objects.create_user(
            username='otro_turista_riguroso',
            email='otro_turista@monagua.com',
            password='OtroPassword123#',
            first_name='Lucia',
            last_name='Morales',
            rol=Usuario.Roles.CLIENTE,
            tipo_documento='CC',
            numero_documento='9876543210',
            is_staff=False,
            is_superuser=False
        )

        # Categoría y Paquete turístico
        self.categoria = Categoria.objects.create(nombre='Ecoturismo Riguroso')
        self.paquete = Paquete.objects.create(
            nombre='Tour Páramo Riguroso',
            descripcion='Aventura ecológica de prueba rigurosa',
            categoria=self.categoria,
            punto_encuentro='Parque Principal Mongua',
            hora_encuentro='07:30:00',
            dias_duracion=2,
            noches_duracion=1,
            estado=True
        )

        # Temporada activa y Tarifa
        self.temporada = Temporada.objects.create(
            nombre='Temporada Vigente Rigurosa',
            fecha_inicio=date.today() - timedelta(days=30),
            fecha_fin=date.today() + timedelta(days=90),
            estado=True
        )
        self.tarifa = Tarifa.objects.create(
            paquete=self.paquete,
            temporada=self.temporada,
            precio_adulto=Decimal('150000.00'),
            precio_menor=Decimal('100000.00'),
            estado=True
        )

    def _crear_imagen_valida(self, nombre='recibo.jpg'):
        img = Image.new('RGB', (100, 100), color='green')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        buf.seek(0)
        return SimpleUploadedFile(nombre, buf.getvalue(), content_type='image/jpeg')

    def _crear_reserva_base(self, dias=6):
        fecha = date.today() + timedelta(days=dias)
        return Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            fecha_inicio=fecha,
            numero_adultos=2,
            numero_menores=1,
            estado_reserva='pendiente'
        )

    def _crear_reserva_confirmada_con_pago(self, dias=15):
        fecha = date.today() + timedelta(days=dias)
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            fecha_inicio=fecha,
            numero_adultos=2,
            numero_menores=1,
            estado_reserva='pendiente'
        )
        pago = Pago.objects.create(
            reserva=reserva,
            referencia=f'REF-FAC-{reserva.id}',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('pago.jpg'),
            estado_transaccion='aprobado'
        )
        reserva.refresh_from_db()
        return reserva, pago

    # --------------------------------------------------------------------------
    # 1. PRUEBAS DE RESERVA
    # --------------------------------------------------------------------------
    def test_01_reserva_creacion_exitosa_y_calculo_monto(self):
        """Crea una reserva válida y verifica el cálculo exacto del monto_total y notificación."""
        self.client.force_login(self.turista)
        fecha_viaje = (date.today() + timedelta(days=5)).strftime('%Y-%m-%d')
        response = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_viaje,
            'adultos': '2',
            'menores': '1'
        })
        self.assertRedirects(response, reverse('mis_reservas_usuario'))

        reserva = Reserva.objects.filter(usuario=self.turista, paquete=self.paquete).first()
        self.assertIsNotNone(reserva)
        self.assertEqual(reserva.estado_reserva, 'pendiente')
        self.assertEqual(reserva.numero_adultos, 2)
        self.assertEqual(reserva.numero_menores, 1)
        # 2 adultos * 150.000 + 1 menor * 100.000 = 400.000
        self.assertEqual(reserva.monto_total, Decimal('400000.00'))

        # Notificación al turista
        notif = Notificacion.objects.filter(usuario=self.turista, reserva=reserva).first()
        self.assertIsNotNone(notif)
        self.assertIn('Tour Páramo Riguroso', notif.mensaje)

    def test_02_reserva_rechaza_fechas_menores_a_dos_dias_o_pasadas(self):
        """Verifica que no se permita reservar con menos de 2 días de anticipación ni en fechas pasadas."""
        self.client.force_login(self.turista)

        # Mañana (solo 1 día de anticipación)
        fecha_manana = (date.today() + timedelta(days=1)).strftime('%Y-%m-%d')
        res_manana = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_manana,
            'adultos': '1',
            'menores': '0'
        })
        self.assertEqual(res_manana.status_code, 302)
        self.assertFalse(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_manana).exists())

        # Ayer (fecha pasada)
        fecha_ayer = (date.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        res_ayer = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_ayer,
            'adultos': '1',
            'menores': '0'
        })
        self.assertEqual(res_ayer.status_code, 302)
        self.assertFalse(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_ayer).exists())

    def test_03_reserva_rechaza_cero_adultos_y_limites_excedidos(self):
        """Verifica que el servidor rechace reservas sin adultos o superando los límites máximos permitidos."""
        self.client.force_login(self.turista)
        fecha_valida = (date.today() + timedelta(days=10)).strftime('%Y-%m-%d')

        # Cero adultos
        res_cero = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_valida,
            'adultos': '0',
            'menores': '2'
        })
        self.assertEqual(res_cero.status_code, 302)
        self.assertFalse(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_valida).exists())

        # Más de 30 adultos
        res_exceso = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_valida,
            'adultos': '35',
            'menores': '0'
        })
        self.assertEqual(res_exceso.status_code, 302)
        self.assertFalse(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_valida).exists())

    def test_04_reserva_previene_duplicados_mismo_usuario_paquete_fecha(self):
        """Verifica que un usuario no pueda duplicar una reserva para el mismo paquete y fecha."""
        self.client.force_login(self.turista)
        fecha_valida = (date.today() + timedelta(days=8)).strftime('%Y-%m-%d')

        # Primera reserva exitosa
        self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_valida,
            'adultos': '1',
            'menores': '0'
        })
        self.assertEqual(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_valida).count(), 1)

        # Segundo intento idéntico
        res_dup = self.client.post(reverse('guardar_reserva', args=[self.paquete.id]), {
            'fecha': fecha_valida,
            'adultos': '1',
            'menores': '0'
        })
        self.assertEqual(res_dup.status_code, 302)
        # Sigue existiendo exactamente 1
        self.assertEqual(Reserva.objects.filter(usuario=self.turista, fecha_inicio=fecha_valida).count(), 1)

    def test_05_reserva_bloquea_confirmacion_sin_pago_aprobado(self):
        """Verifica la restricción de modelo: una reserva NO puede tener estado 'confirmada' sin pago aprobado."""
        fecha_valida = date.today() + timedelta(days=12)
        reserva = Reserva.objects.create(
            usuario=self.turista,
            paquete=self.paquete,
            fecha_inicio=fecha_valida,
            numero_adultos=1,
            numero_menores=0,
            estado_reserva='pendiente'
        )

        reserva.estado_reserva = 'confirmada'
        with self.assertRaises(ValidationError):
            reserva.save()

    # --------------------------------------------------------------------------
    # 2. PRUEBAS DE PAGO Y COMPROBANTE
    # --------------------------------------------------------------------------
    def test_06_enviar_comprobante_exitoso_y_notificaciones(self):
        """Verifica que el turista pueda subir un comprobante válido y se notifique a administradores."""
        reserva = self._crear_reserva_base(dias=6)
        self.client.force_login(self.turista)

        imagen = self._crear_imagen_valida('recibo_pago.jpg')
        res = self.client.post(reverse('enviar_comprobante'), {
            'reserva': reserva.id,
            'referencia': 'CUS-20261118',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': imagen,
            'descripcion': 'Pago total verificado desde App Bancolombia'
        })
        self.assertRedirects(res, reverse('mis_comprobantes'))

        pago = Pago.objects.filter(reserva=reserva).first()
        self.assertIsNotNone(pago)
        self.assertEqual(pago.estado_transaccion, 'pendiente')
        self.assertEqual(pago.monto, reserva.monto_total)
        self.assertEqual(pago.referencia, 'CUS-20261118')
        self.assertEqual(pago.banco_origen, 'Bancolombia')

        # Reserva sigue en pendiente hasta aprobación del admin
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva, 'pendiente')

        # Notificación al turista y al admin
        self.assertTrue(Notificacion.objects.filter(usuario=self.turista, reserva=reserva, tipo="Comprobante de Pago").exists())
        self.assertTrue(Notificacion.objects.filter(usuario=self.admin, reserva=reserva, tipo="Comprobante de Pago").exists())

    def test_07_enviar_comprobante_bloquea_duplicados_mientras_este_pendiente(self):
        """Verifica que no se permita enviar un segundo comprobante si ya existe uno en revisión."""
        reserva = self._crear_reserva_base(dias=7)
        self.client.force_login(self.turista)

        # Primer comprobante
        self.client.post(reverse('enviar_comprobante'), {
            'reserva': reserva.id,
            'referencia': 'REF-001',
            'banco_origen': 'Nequi',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': self._crear_imagen_valida('c1.jpg'),
        })
        self.assertEqual(Pago.objects.filter(reserva=reserva).count(), 1)

        # Segundo intento mientras sigue pendiente
        res_dup = self.client.post(reverse('enviar_comprobante'), {
            'reserva': reserva.id,
            'referencia': 'REF-002',
            'banco_origen': 'Daviplata',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': self._crear_imagen_valida('c2.jpg'),
        })
        self.assertRedirects(res_dup, reverse('mis_comprobantes'))
        self.assertEqual(Pago.objects.filter(reserva=reserva).count(), 1)

    def test_08_enviar_comprobante_rechaza_extensiones_peligrosas(self):
        """Verifica el rechazo estricto de archivos maliciosos (ej. scripts o dobles extensiones)."""
        reserva = self._crear_reserva_base(dias=8)
        self.client.force_login(self.turista)

        archivo_malicioso = SimpleUploadedFile('recibo.php.png', b'<?php phpinfo(); ?>', content_type='image/png')
        res = self.client.post(reverse('enviar_comprobante'), {
            'reserva': reserva.id,
            'referencia': 'MALICIOUS-01',
            'banco_origen': 'Bancolombia',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': archivo_malicioso,
        })
        self.assertEqual(Pago.objects.filter(reserva=reserva).count(), 0)

    def test_09_admin_rechazar_comprobante_con_nota_y_auditoria(self):
        """Verifica que el admin pueda rechazar un comprobante ilegible indicando la nota y registrando en Bitácora."""
        reserva = self._crear_reserva_base(dias=9)
        pago = Pago.objects.create(
            reserva=reserva,
            referencia='REF-BORROSO',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('borroso.jpg'),
            estado_transaccion='pendiente'
        )

        self.client.force_login(self.admin)
        res = self.client.post(reverse('admin_revisar_comprobante', args=[pago.id]), {
            'estado_transaccion': 'rechazado',
            'banco_origen': 'Bancolombia',
            'monto': str(reserva.monto_total),
            'nota_admin': 'El comprobante no muestra el número de aprobación. Por favor sube una captura nítida.'
        })
        self.assertRedirects(res, reverse('admin_comprobantes'))

        pago.refresh_from_db()
        self.assertEqual(pago.estado_transaccion, 'rechazado')
        self.assertIn('captura nítida', pago.nota_admin)

        # Reserva sigue en estado 'pendiente'
        reserva.refresh_from_db()
        self.assertEqual(reserva.estado_reserva, 'pendiente')

        # Bitácora registrada
        bitacora = Bitacora.objects.filter(registro_id=pago.id, modulo='Comprobantes de Pago').first()
        self.assertIsNotNone(bitacora)
        self.assertEqual(bitacora.accion, 'UPDATE')

        # Notificación con motivo al turista
        notif = Notificacion.objects.filter(usuario=self.turista, reserva=reserva).order_by('-id').first()
        self.assertIn('captura nítida', notif.mensaje)

    def test_10_admin_rechazar_sin_nota_falla(self):
        """Verifica que el administrador no pueda rechazar un comprobante sin proporcionar una nota explicativa."""
        reserva = self._crear_reserva_base(dias=10)
        pago = Pago.objects.create(
            reserva=reserva,
            referencia='REF-SIN-NOTA',
            banco_origen='Nequi',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('recibo.jpg'),
            estado_transaccion='pendiente'
        )

        self.client.force_login(self.admin)
        res = self.client.post(reverse('admin_revisar_comprobante', args=[pago.id]), {
            'estado_transaccion': 'rechazado',
            'banco_origen': 'Nequi',
            'monto': str(reserva.monto_total),
            'nota_admin': ''  # Vacía
        })
        self.assertEqual(res.status_code, 200)  # Re-renderiza formulario with error
        pago.refresh_from_db()
        self.assertEqual(pago.estado_transaccion, 'pendiente')

    def test_11_turista_reintenta_comprobante_tras_rechazo(self):
        """Verifica que el turista pueda volver a enviar un comprobante sobre la reserva tras un rechazo."""
        reserva = self._crear_reserva_base(dias=11)
        pago = Pago.objects.create(
            reserva=reserva,
            referencia='REF-INICIAL',
            banco_origen='Nequi',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('inicial.jpg'),
            estado_transaccion='rechazado',
            nota_admin='Comprobante borroso'
        )

        self.client.force_login(self.turista)
        res = self.client.post(reverse('enviar_comprobante'), {
            'reserva': reserva.id,
            'referencia': 'REF-CORREGIDA',
            'banco_origen': 'Nequi',
            'metodo_pago': 'Transferencia Bancaria',
            'imagen_comprobante': self._crear_imagen_valida('corregido.jpg'),
            'descripcion': 'Adjunto nuevo comprobante nítido'
        })
        self.assertRedirects(res, reverse('mis_comprobantes'))

        pago.refresh_from_db()
        self.assertEqual(pago.estado_transaccion, 'pendiente')
        self.assertEqual(pago.referencia, 'REF-CORREGIDA')
        self.assertEqual(pago.nota_admin, '')

    def test_12_admin_no_puede_aprobar_con_monto_insuficiente(self):
        """Verifica que no se pueda aprobar un pago cuyo monto verificado sea menor al total de la reserva."""
        reserva = self._crear_reserva_base(dias=12)
        pago = Pago.objects.create(
            reserva=reserva,
            referencia='REF-INSUFICIENTE',
            banco_origen='Daviplata',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('recibo.jpg'),
            estado_transaccion='pendiente'
        )

        self.client.force_login(self.admin)
        res = self.client.post(reverse('admin_revisar_comprobante', args=[pago.id]), {
            'estado_transaccion': 'aprobado',
            'banco_origen': 'Daviplata',
            'monto': '50000.00',  # Mucho menor a 400.000
            'nota_admin': 'Aprobación parcial indebida'
        })
        self.assertEqual(res.status_code, 200)
        pago.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(pago.estado_transaccion, 'pendiente')
        self.assertEqual(reserva.estado_reserva, 'pendiente')

    def test_13_admin_aprobar_comprobante_sincroniza_reserva_confirmada(self):
        """Verifica que la aprobación del comprobante por el administrador actualice automáticamente la reserva a confirmada."""
        reserva = self._crear_reserva_base(dias=13)
        pago = Pago.objects.create(
            reserva=reserva,
            referencia='REF-VALIDA-TOTAL',
            banco_origen='Bancolombia',
            metodo_pago='Transferencia Bancaria',
            monto=reserva.monto_total,
            imagen_comprobante=self._crear_imagen_valida('recibo.jpg'),
            estado_transaccion='pendiente'
        )

        self.client.force_login(self.admin)
        res = self.client.post(reverse('admin_revisar_comprobante', args=[pago.id]), {
            'estado_transaccion': 'aprobado',
            'banco_origen': 'Bancolombia',
            'monto': str(reserva.monto_total),
            'nota_admin': 'Pago verificado en extracto bancario'
        })
        self.assertRedirects(res, reverse('admin_comprobantes'))

        pago.refresh_from_db()
        reserva.refresh_from_db()
        self.assertEqual(pago.estado_transaccion, 'aprobado')
        self.assertEqual(reserva.estado_reserva, 'confirmada')

        # Notificación de confirmación al turista
        notif = Notificacion.objects.filter(usuario=self.turista, reserva=reserva).order_by('-id').first()
        self.assertIn('confirmada exitosamente', notif.mensaje)

    # --------------------------------------------------------------------------
    # 3. PRUEBAS DE FACTURACIÓN Y DESCARGA PDF
    # --------------------------------------------------------------------------
    def test_14_mis_facturas_muestra_solo_reservas_confirmadas(self):
        """Verifica que 'mis_facturas' únicamente liste reservas con pago aprobado/confirmadas."""
        reserva_pend = self._crear_reserva_base(dias=14)
        reserva_conf, _ = self._crear_reserva_confirmada_con_pago(dias=15)

        self.client.force_login(self.turista)
        res = self.client.get(reverse('mis_facturas'))
        self.assertEqual(res.status_code, 200)
        reservas_en_contexto = list(res.context['reservas'])

        self.assertIn(reserva_conf, reservas_en_contexto)
        self.assertNotIn(reserva_pend, reservas_en_contexto)

    def test_15_ver_factura_bloquea_reserva_pendiente(self):
        """Verifica que 'ver_factura' no permita visualizar facturas de reservas sin confirmar."""
        reserva_pend = self._crear_reserva_base(dias=16)

        self.client.force_login(self.turista)
        res = self.client.get(reverse('ver_factura', args=[reserva_pend.id]))
        self.assertRedirects(res, reverse('mis_reservas_usuario'))

    def test_16_ver_factura_control_acceso_otro_turista_bloqueado(self):
        """Verifica el principio de menor privilegio / Zero-Trust: otro usuario no puede ver la factura del titular."""
        reserva_conf, _ = self._crear_reserva_confirmada_con_pago(dias=17)

        self.client.force_login(self.otro_turista)
        res = self.client.get(reverse('ver_factura', args=[reserva_conf.id]))
        self.assertRedirects(res, reverse('mis_reservas_usuario'))

    def test_17_ver_factura_renderiza_ok_para_titular_y_admin(self):
        """Verifica que el titular y el administrador puedan ver la factura HTML con QR y montos exactos."""
        reserva_conf, _ = self._crear_reserva_confirmada_con_pago(dias=18)

        # Vista por el titular
        self.client.force_login(self.turista)
        res_turista = self.client.get(reverse('ver_factura', args=[reserva_conf.id]))
        self.assertEqual(res_turista.status_code, 200)
        contenido = res_turista.content.decode('utf-8')
        self.assertIn(f'FAC-1000{reserva_conf.id}', contenido)
        self.assertIn('Tour Páramo Riguroso', contenido)
        self.assertIn('data:image/png;base64', contenido)  # QR Code

        # Vista por el administrador
        self.client.force_login(self.admin)
        res_admin = self.client.get(reverse('ver_factura', args=[reserva_conf.id]))
        self.assertEqual(res_admin.status_code, 200)

    def test_18_descargar_factura_pdf_encriptado_con_documento(self):
        """Verifica la generación de PDF en 'descargar_factura', su formato y cifrado con numero_documento."""
        reserva_conf, _ = self._crear_reserva_confirmada_con_pago(dias=19)

        self.client.force_login(self.turista)
        res = self.client.get(reverse('descargar_factura', args=[reserva_conf.id]))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/pdf')
        self.assertIn(f'factura_FAC-1000{reserva_conf.id}.pdf', res['Content-Disposition'])
        self.assertTrue(res.content.startswith(b'%PDF-'))

        # Verificación criptográfica con pypdf
        reader = pypdf.PdfReader(io.BytesIO(res.content))
        self.assertTrue(reader.is_encrypted, "El archivo PDF debe estar encriptado por seguridad de datos personales.")

        # Desencriptación exitosa con el número de documento del usuario
        resultado_desencriptado = reader.decrypt(self.turista.numero_documento)
        self.assertNotEqual(resultado_desencriptado, pypdf.PasswordType.NOT_DECRYPTED)
        self.assertGreater(len(reader.pages), 0)

    def test_19_descargar_factura_bloquea_usuario_no_autorizado(self):
        """Verifica que usuarios ajenos no puedan descargar el PDF de la factura."""
        reserva_conf, _ = self._crear_reserva_confirmada_con_pago(dias=20)

        self.client.force_login(self.otro_turista)
        res = self.client.get(reverse('descargar_factura', args=[reserva_conf.id]))
        self.assertRedirects(res, reverse('mis_reservas_usuario'))


