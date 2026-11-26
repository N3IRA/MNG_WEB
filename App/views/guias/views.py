from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from App.models import Usuario
from App.utils import crear_notificacion_sistema
from App.validators import validar_archivo_subido, validar_foto_perfil


from django.db.models import Q

def es_administrador(user):
    return user.is_authenticated and user.is_active and (user.is_staff or getattr(user, 'rol', None) == Usuario.Roles.ADMIN)


# ==============================================================================
# GESTIÓN DE GUÍAS TURÍSTICOS (ADMINISTRACIÓN)
# ==============================================================================

@user_passes_test(es_administrador)
def gestion_guias_view(request):
    """Directorio y gestión de guías turísticos con soporte para filtros y métricas."""
    estado = request.GET.get('estado', '').strip().lower()
    query = request.GET.get('q', '').strip()

    guias_base = Usuario.objects.filter(rol=Usuario.Roles.GUIA)
    total_guias = guias_base.count()
    guias_activos = guias_base.filter(is_active=True).count()
    guias_inactivos = guias_base.filter(is_active=False).count()
    guias_con_tarjeta = guias_base.filter(numero_tarjeta_profesional__isnull=False).exclude(numero_tarjeta_profesional='').count()

    guias = guias_base.order_by('-id')

    if estado == 'activos':
        guias = guias.filter(is_active=True)
    elif estado == 'inactivos':
        guias = guias.filter(is_active=False)
    elif estado in ['con_tarjeta', 'licencia']:
        guias = guias.filter(numero_tarjeta_profesional__isnull=False).exclude(numero_tarjeta_profesional='')

    if query:
        guias = guias.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(numero_documento__icontains=query) |
            Q(numero_tarjeta_profesional__icontains=query) |
            Q(telefono__icontains=query)
        )

    contexto = {
        'guias': guias,
        'total_guias': total_guias,
        'guias_activos': guias_activos,
        'guias_inactivos': guias_inactivos,
        'guias_con_tarjeta': guias_con_tarjeta,
        'estado_seleccionado': estado,
    }
    return render(request, 'admin/guias/gestion_guias.html', contexto)


@user_passes_test(es_administrador)
def guias_guardar(request):
    """Registra o actualiza la información y credenciales de un guía turístico."""
    if request.method == 'POST':
        user_id = request.POST.get('id') or request.POST.get('guia_id')
        first_name = (request.POST.get('first_name') or request.POST.get('nombre') or '').strip()
        last_name = (request.POST.get('last_name') or request.POST.get('apellido') or '').strip()
        email = (request.POST.get('email') or request.POST.get('correo') or '').strip()
        telefono = request.POST.get('telefono', '').strip()
        tipo_documento = request.POST.get('tipo_documento', 'CC').strip()
        numero_documento = (request.POST.get('numero_documento') or request.POST.get('documento') or '').strip()
        residencia = request.POST.get('residencia', '').strip()
        tarjeta_profesional = (request.POST.get('numero_tarjeta_profesional') or request.POST.get('licencia_turismo') or '').strip()
        experiencia_anos_raw = request.POST.get('experiencia_anos') or request.POST.get('experiencia') or 0
        descripcion_experiencia = (request.POST.get('descripcion_experiencia') or request.POST.get('biografia') or '').strip()
        entidad_salud = request.POST.get('entidad_salud', '').strip()
        password = request.POST.get('password', '').strip()
        imagen_perfil = request.FILES.get('imagen_perfil')

        if imagen_perfil:
            valido, err = validar_archivo_subido(imagen_perfil, validar_foto_perfil)
            if not valido:
                messages.error(request, err)
                return redirect('gestion_guias')

        try:
            experiencia_anos = int(experiencia_anos_raw) if experiencia_anos_raw else 0
        except (ValueError, TypeError):
            experiencia_anos = 0

        if user_id:
            # Actualización
            user_obj = get_object_or_404(Usuario, pk=user_id)

            if email and Usuario.objects.filter(email=email).exclude(pk=user_obj.pk).exists():
                messages.error(request, f"El correo '{email}' ya se encuentra registrado por otro usuario.")
                return redirect('gestion_guias')

            if numero_documento and Usuario.objects.filter(numero_documento=numero_documento).exclude(pk=user_obj.pk).exists():
                messages.error(request, f"El número de documento '{numero_documento}' ya pertenece a otro usuario.")
                return redirect('gestion_guias')

            user_obj.first_name = first_name
            user_obj.last_name = last_name
            if email:
                user_obj.email = email
            user_obj.telefono = telefono
            user_obj.tipo_documento = tipo_documento
            user_obj.numero_documento = numero_documento
            user_obj.residencia = residencia
            user_obj.numero_tarjeta_profesional = tarjeta_profesional
            user_obj.experiencia_anos = experiencia_anos
            user_obj.descripcion_experiencia = descripcion_experiencia
            user_obj.entidad_salud = entidad_salud
            user_obj.rol = Usuario.Roles.GUIA

            if password:
                user_obj.set_password(password)

            if imagen_perfil:
                user_obj.imagen_perfil = imagen_perfil

            user_obj.save()

            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"Se ha actualizado la información del guía turístico: '{user_obj.get_full_name() or user_obj.username}'.",
                tipo="Guía Turístico",
                prioridad="media"
            )
            messages.success(request, f"Guía '{user_obj.get_full_name() or user_obj.username}' actualizado correctamente.")
        else:
            # Nuevo Registro
            username = request.POST.get('username', '').strip()
            if not username:
                username = email.split('@')[0] if email else f"guia_{numero_documento}"

            if Usuario.objects.filter(username=username).exists():
                messages.error(request, f"El nombre de usuario '{username}' ya está en uso.")
                return redirect('gestion_guias')

            if email and Usuario.objects.filter(email=email).exists():
                messages.error(request, f"El correo '{email}' ya se encuentra registrado.")
                return redirect('gestion_guias')

            if numero_documento and Usuario.objects.filter(numero_documento=numero_documento).exists():
                messages.error(request, f"El documento '{numero_documento}' ya se encuentra registrado.")
                return redirect('gestion_guias')

            user_obj = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password or 'MonaguaGuia2026*',
                first_name=first_name,
                last_name=last_name,
                rol=Usuario.Roles.GUIA,
                telefono=telefono,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                residencia=residencia,
                numero_tarjeta_profesional=tarjeta_profesional,
                experiencia_anos=experiencia_anos,
                descripcion_experiencia=descripcion_experiencia,
                entidad_salud=entidad_salud,
            )

            if imagen_perfil:
                user_obj.imagen_perfil = imagen_perfil
                user_obj.save()

            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"Se ha registrado un nuevo guía turístico: '{user_obj.get_full_name() or user_obj.username}'.",
                tipo="Guía Turístico",
                prioridad="media"
            )
            messages.success(request, f"Guía '{user_obj.get_full_name() or user_obj.username}' registrado exitosamente.")

    return redirect('gestion_guias')


@user_passes_test(es_administrador)
def guias_toggle_estado(request, id):
    """Activa o desactiva la cuenta de un guía turístico."""
    if request.method == 'POST':
        user_obj = get_object_or_404(Usuario, pk=id)
        if user_obj.id == request.user.id:
            messages.error(request, "No puedes desactivar tu propia cuenta de administrador.")
            return redirect('gestion_guias')

        user_obj.is_active = not user_obj.is_active
        user_obj.save()

        estado_txt = "activada" if user_obj.is_active else "desactivada"
        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"La cuenta del guía '{user_obj.username}' ha sido {estado_txt}.",
            tipo="Guía Turístico",
            prioridad="media"
        )
        messages.success(request, f"La cuenta del guía '{user_obj.username}' ha sido {estado_txt}.")

    return redirect('gestion_guias')


@user_passes_test(es_administrador)
def asignar_rol_guia(request, id):
    """Alterna el rol de un usuario entre Guía Turístico y Cliente."""
    if request.method == 'POST':
        user_obj = get_object_or_404(Usuario, pk=id)
        if user_obj.id == request.user.id:
            messages.error(request, "No puedes alterar tu propio rol de administrador.")
            return redirect('gestion_guias')

        if user_obj.rol == Usuario.Roles.GUIA:
            user_obj.rol = Usuario.Roles.CLIENTE
            accion = "ROL DE GUÍA RETIRADO"
            msg = f"Se ha retirado el rol de guía a '{user_obj.username}' (ahora es Cliente/Turista)."
        else:
            user_obj.rol = Usuario.Roles.GUIA
            accion = "ROL DE GUÍA ASIGNADO"
            msg = f"Se ha asignado el rol de guía turístico a '{user_obj.username}'."

        user_obj.save()

        crear_notificacion_sistema(
            usuario=user_obj,
            mensaje=msg,
            tipo="Guía Turístico",
            prioridad="media"
        )
        messages.success(request, msg)

    return redirect('gestion_guias')
