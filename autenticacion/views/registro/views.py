import random
import time
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib import messages
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from App.models import Usuario
from App.utils import crear_notificacion_sistema
from autenticacion.forms import RegistroForm

logger = logging.getLogger(__name__)

OTP_COOLDOWN_SEGUNDOS = 60


def registro_vista(request):
    """
    Renderiza y procesa el formulario de registro de nuevos clientes.
    Valida duplicados y envía un código OTP de verificación por correo electrónico.
    Protegido contra envíos múltiples/doble clic mediante caché atómica y reutilización de OTP activo.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or getattr(request.user, 'rol', None) == Usuario.Roles.ADMIN:
            return redirect('dashboard_admin')
        elif getattr(request.user, 'es_turista', False):
            return redirect('panel_rapido')
        return redirect('panel_rapido')

    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].strip().lower()

            # Filtrar y almacenar en sesión exclusivamente campos de la lista blanca de RegistroForm
            campos_permitidos = set(RegistroForm.Meta.fields) | {'password', 'confirmar_password'}
            datos_filtrados = {k: v for k, v in request.POST.items() if k in campos_permitidos}
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                datos_filtrados['next'] = next_url

            request.session['registro_data'] = datos_filtrados
            request.session['registro_email'] = email

            # Comprobar si ya se envió un OTP recientemente a este correo (en sesión o caché)
            last_email = (request.session.get('registro_email') or '').strip().lower()
            last_otp = request.session.get('registro_otp')
            last_otp_time = request.session.get('registro_otp_time', 0)
            tiempo_desde_ultimo = time.time() - last_otp_time

            cache_lock_key = f"reg_lock_{email}"
            cache_otp_sent_key = f"reg_sent_{email}"
            cache_otp_code_key = f"reg_otp_{email}"

            cached_otp = cache.get(cache_otp_code_key)

            # Si ya se envió un código hace menos de OTP_COOLDOWN_SEGUNDOS, reutilizarlo y redirigir
            if (last_email == email and last_otp and tiempo_desde_ultimo < OTP_COOLDOWN_SEGUNDOS) or cached_otp:
                active_otp = cached_otp or last_otp
                request.session['registro_otp'] = active_otp
                if not request.session.get('registro_otp_time'):
                    request.session['registro_otp_time'] = time.time()
                request.session.modified = True
                messages.info(request, "Ya hemos generado y enviado un código de verificación a tu correo. Por favor ingrésalo a continuación.")
                return redirect('verificar_otp_registro')

            # Bloqueo atómico para prevenir ráfagas concurrentes de peticiones simultáneas
            lock_acquired = cache.add(cache_lock_key, True, timeout=15)
            if not lock_acquired:
                # Otra petición concurrente está enviando el correo para este email; esperar brevemente
                for _ in range(12):
                    time.sleep(0.25)
                    if not cache.get(cache_lock_key):
                        break
                active_otp = cache.get(cache_otp_code_key) or request.session.get('registro_otp')
                if active_otp:
                    request.session['registro_otp'] = active_otp
                    if not request.session.get('registro_otp_time'):
                        request.session['registro_otp_time'] = time.time()
                    request.session.modified = True
                    messages.info(request, "Hemos generado tu código OTP de verificación. Por favor ingrésalo para activar tu cuenta.")
                    return redirect('verificar_otp_registro')

            try:
                # Comprobar nuevamente tras obtener el lock
                cached_otp = cache.get(cache_otp_code_key)
                if cached_otp:
                    request.session['registro_otp'] = cached_otp
                    request.session.modified = True
                    return redirect('verificar_otp_registro')

                otp = str(random.randint(100000, 999999))
                request.session['registro_otp'] = otp
                request.session['registro_otp_time'] = time.time()
                request.session['registro_otp_intentos'] = 0
                request.session.modified = True

                # Registrar en caché con ventana de enfriamiento
                cache.set(cache_otp_code_key, otp, timeout=OTP_COOLDOWN_SEGUNDOS)
                cache.set(cache_otp_sent_key, True, timeout=OTP_COOLDOWN_SEGUNDOS)

                # Enviar correo con plantilla HTML
                asunto = 'Código de verificación para tu cuenta - Monagua'
                html_mensaje = render_to_string('autenticacion/email_otp_registro.html', {'otp': otp})
                texto_plano = strip_tags(html_mensaje)

                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'webmonagua@gmail.com'))
                send_mail(
                    asunto,
                    texto_plano,
                    from_email,
                    [email],
                    html_message=html_mensaje,
                    fail_silently=False,
                )
                messages.info(request, "Hemos generado tu código OTP de verificación. Por favor ingrésalo para activar tu cuenta.")
                return redirect('verificar_otp_registro')
            except Exception as e:
                logger.error(f"Error al enviar correo de verificación: {e}")
                cache.delete(cache_otp_code_key)
                cache.delete(cache_otp_sent_key)
                messages.error(request, f"No se pudo enviar el correo de verificación a {email}: {e}")
                return redirect('registro')
            finally:
                cache.delete(cache_lock_key)
        else:
            errores_detalles = []
            for field, err_list in form.errors.items():
                err_text = str(err_list[0])
                if field == '__all__':
                    errores_detalles.append(err_text)
                else:
                    field_label = form.fields[field].label if field in form.fields else field
                    errores_detalles.append(f"{field_label}: {err_text}")
            
            error_msg = " | ".join(errores_detalles) if errores_detalles else "Por favor verifica los campos resaltados en el formulario."
            messages.error(request, error_msg)
    else:
        form = RegistroForm()

    return render(request, 'autenticacion/registro.html', {
        'titulo': 'Crear Cuenta en Monagua',
        'form': form
    })


def verificar_otp_registro_vista(request):
    """
    Verifica el código OTP ingresado por el usuario en el proceso de registro.
    Al ser válido, crea formalmente la cuenta del usuario en la base de datos y lo autentica.
    """
    if 'registro_data' not in request.session or 'registro_otp' not in request.session:
        messages.error(request, 'Tu sesión ha expirado o no has iniciado un registro.')
        return redirect('registro')

    # Expiración a los 10 minutos (600 segundos)
    otp_time = request.session.get('registro_otp_time', 0)
    if time.time() - otp_time > 600:
        request.session.pop('registro_data', None)
        request.session.pop('registro_otp', None)
        request.session.pop('registro_email', None)
        request.session.pop('registro_otp_time', None)
        messages.error(request, 'El código de verificación ha expirado. Por favor inicia tu registro nuevamente.')
        return redirect('registro')

    error_otp = False

    if request.method == 'POST':
        otp_intentos = request.session.get('registro_otp_intentos', 0) + 1
        request.session['registro_otp_intentos'] = otp_intentos

        if otp_intentos > 5:
            request.session.pop('registro_data', None)
            request.session.pop('registro_otp', None)
            request.session.pop('registro_email', None)
            request.session.pop('registro_otp_time', None)
            request.session.pop('registro_otp_intentos', None)
            messages.error(request, 'Has superado el límite de intentos permitidos por seguridad. Por favor inicia nuevamente tu registro.')
            return redirect('registro')

        otp_ingresado = request.POST.get('otp', '').strip()
        if otp_ingresado == request.session['registro_otp']:
            form = RegistroForm(request.session['registro_data'])
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.rol = Usuario.Roles.CLIENTE
                user.is_staff = False
                user.is_superuser = False

                # Asegurar persistencia de campos geográficos
                reg_data = request.session.get('registro_data', {})
                if 'pais' in reg_data and reg_data['pais']:
                    user.pais = str(reg_data['pais']).strip()
                if 'departamento' in reg_data and reg_data['departamento']:
                    d_val = str(reg_data['departamento']).strip()
                    user.departamento = int(d_val) if d_val.isdigit() else None
                if 'ciudad' in reg_data and reg_data['ciudad']:
                    c_val = str(reg_data['ciudad']).strip()
                    user.ciudad = int(c_val) if c_val.isdigit() else None

                user.save()

                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'¡Registro exitoso! Bienvenido a la familia Monagua, {user.first_name}.')

                next_url = request.session['registro_data'].get('next')

                # Limpiar llaves de caché y datos de sesión temporales
                clean_email = user.email.strip().lower()
                cache.delete(f"reg_otp_{clean_email}")
                cache.delete(f"reg_sent_{clean_email}")
                cache.delete(f"reg_lock_{clean_email}")

                request.session.pop('registro_data', None)
                request.session.pop('registro_otp', None)
                request.session.pop('registro_email', None)
                request.session.pop('registro_otp_time', None)
                request.session.pop('registro_otp_intentos', None)

                response = redirect(next_url if next_url else 'panel_rapido')
                response.set_cookie('ha_registrado', 'true', max_age=31536000)  # 1 año
                return response
            else:
                errores = " | ".join([f"{f}: {err[0]}" for f, err in form.errors.items()])
                messages.error(request, f'Ocurrió un error al procesar los datos de registro: {errores}')
                return redirect('registro')
        else:
            error_otp = True
            intentos_restantes = max(0, 5 - otp_intentos)
            messages.error(request, f'El código OTP ingresado es incorrecto. Intentos restantes: {intentos_restantes}.')

    email = request.session.get('registro_email', '')
    partes = email.split('@')
    email_oculto = f"{partes[0][0]}***@{partes[1]}" if len(partes) == 2 else email

    tiempo_transcurrido = time.time() - otp_time
    cooldown_restante = max(0, int(OTP_COOLDOWN_SEGUNDOS - tiempo_transcurrido))

    return render(request, 'autenticacion/registro_otp.html', {
        'email_oculto': email_oculto,
        'error_otp': error_otp,
        'cooldown_restante': cooldown_restante
    })


def reenviar_otp_registro_vista(request):
    """
    Genera y reenvía un nuevo código OTP para el registro activo sin perder los datos.
    Aplica cooldown de 60 segundos y exclusión mutua para evitar envíos duplicados.
    """
    if 'registro_data' not in request.session or 'registro_email' not in request.session:
        messages.error(request, 'Tu sesión de registro ha expirado. Por favor inicia nuevamente.')
        return redirect('registro')

    email = request.session['registro_email']
    clean_email = email.strip().lower()
    last_time = request.session.get('registro_otp_time', 0)
    tiempo_transcurrido = time.time() - last_time

    if tiempo_transcurrido < OTP_COOLDOWN_SEGUNDOS:
        segundos_restantes = int(OTP_COOLDOWN_SEGUNDOS - tiempo_transcurrido)
        messages.warning(request, f'Por favor espera {segundos_restantes} segundos antes de solicitar un nuevo código.')
        return redirect('verificar_otp_registro')

    cache_lock = f"reg_lock_{clean_email}"
    if not cache.add(cache_lock, True, timeout=15):
        messages.warning(request, 'Ya estamos procesando el reenvío de tu código. Por favor espera un momento.')
        return redirect('verificar_otp_registro')

    try:
        nuevo_otp = str(random.randint(100000, 999999))
        request.session['registro_otp'] = nuevo_otp
        request.session['registro_otp_time'] = time.time()
        request.session['registro_otp_intentos'] = 0
        request.session.modified = True

        cache.set(f"reg_otp_{clean_email}", nuevo_otp, timeout=OTP_COOLDOWN_SEGUNDOS)
        cache.set(f"reg_sent_{clean_email}", True, timeout=OTP_COOLDOWN_SEGUNDOS)

        asunto = 'Nuevo código de verificación para tu cuenta - Monagua'
        html_mensaje = render_to_string('autenticacion/email_otp_registro.html', {'otp': nuevo_otp})
        texto_plano = strip_tags(html_mensaje)

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'webmonagua@gmail.com'))
        send_mail(
            asunto,
            texto_plano,
            from_email,
            [email],
            html_message=html_mensaje,
            fail_silently=False,
        )
        messages.success(request, f'Se ha generado y enviado un nuevo código OTP a {email}.')
    except Exception as e:
        logger.error(f"Error reenviando OTP de registro: {e}")
        messages.error(request, f"No se pudo reinsertar/enviar el código a {email}: {e}")
    finally:
        cache.delete(cache_lock)

    return redirect('verificar_otp_registro')
