from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Q
from App.models import Usuario
from App.utils import crear_notificacion_sistema
from autenticacion.forms import IniciarSesionForm


def login_vista(request):
    """
    Gestiona el inicio de sesión de usuarios (administradores, clientes, guías).
    Permite autenticarse utilizando correo electrónico o nombre de usuario.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or getattr(request.user, 'rol', None) == Usuario.Roles.ADMIN:
            return redirect('dashboard_admin')
        elif getattr(request.user, 'es_turista', False):
            return redirect('panel_rapido')
        return redirect('tours')

    form = IniciarSesionForm()

    import time
    intentos_fallidos = request.session.get('intentos_login_fallidos', 0)
    ultimo_intento = request.session.get('ultimo_intento_login', 0)
    now_ts = time.time()

    # Bloqueo temporal tras 5 intentos fallidos consecutivos (cooldown de 5 minutos)
    if intentos_fallidos >= 5:
        tiempo_restante = int(300 - (now_ts - ultimo_intento))
        if tiempo_restante > 0:
            messages.error(
                request, 
                f"Por seguridad se ha bloqueado temporalmente el inicio de sesión tras múltiples intentos fallidos. "
                f"Por favor espera {tiempo_restante} segundos."
            )
            return render(request, 'autenticacion/login.html', {'form': form})
        else:
            request.session['intentos_login_fallidos'] = 0

    if request.method == 'POST':
        form = IniciarSesionForm(data=request.POST)
        if form.is_valid():
            usuario_input = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user_objs = Usuario.objects.filter(
                Q(username__iexact=usuario_input) | Q(email__iexact=usuario_input)
            )

            if not user_objs.exists():
                request.session['intentos_login_fallidos'] = intentos_fallidos + 1
                request.session['ultimo_intento_login'] = time.time()
                messages.error(request, "Credenciales incorrectas o usuario no registrado.")
            else:
                user = None
                for candidate in user_objs:
                    authenticated_user = authenticate(request, username=candidate.username, password=password)
                    if authenticated_user:
                        user = authenticated_user
                        break

                if user is not None:
                    if user.is_active:
                        # Resetear contador de intentos fallidos al tener éxito
                        request.session.pop('intentos_login_fallidos', None)
                        request.session.pop('ultimo_intento_login', None)
                        
                        login(request, user)
                        messages.success(request, f"¡Bienvenido de nuevo, {user.first_name or user.username}!")
                        
                        next_url = request.GET.get('next') or request.POST.get('next')
                        from django.utils.http import url_has_allowed_host_and_scheme
                        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                            return redirect(next_url)
                        
                        if user.is_staff or getattr(user, 'rol', None) == Usuario.Roles.ADMIN:
                            return redirect('dashboard_admin')
                        elif getattr(user, 'es_turista', False):
                            return redirect('panel_rapido')
                        return redirect('tours')
                    else:
                        messages.error(request, "Tu cuenta se encuentra desactivada. Por favor contacta al administrador.")
                else:
                    request.session['intentos_login_fallidos'] = intentos_fallidos + 1
                    request.session['ultimo_intento_login'] = time.time()
                    messages.error(request, "Contraseña incorrecta. Por favor inténtalo de nuevo.")
        else:
            errores_txt = [str(err[0]) for err in form.errors.values()]
            messages.error(request, f"Por favor corrige los campos: {' '.join(errores_txt)}")

    return render(request, 'autenticacion/login.html', {'form': form})


def logout_vista(request):
    """
    Cierra la sesión activa del usuario y redirige al inicio de la plataforma.
    Soporta peticiones GET y POST para evitar errores 405.
    """
    if request.user.is_authenticated:
        usuario_nombre = request.user.username
        crear_notificacion_sistema(
           usuario=request.user,
            mensaje=f"El usuario '{usuario_nombre}' ha cerrado sesión.",
            tipo="Autenticación",
            prioridad="Alta"
        )
        messages.info(request, "Has cerrado sesión correctamente. ¡Hasta pronto!")
    logout(request)
    return redirect('index')
