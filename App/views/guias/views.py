from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from App.models import Usuario, Paquete, PlanGuia
from App.utils import crear_notificacion_sistema


def es_administrador(user):
    return (
        user.is_authenticated
        and user.is_active
        and (user.is_staff or getattr(user, 'rol', None) == Usuario.Roles.ADMIN)
    )


# ==============================================================================
# GESTIÓN DE GUÍAS TURÍSTICOS (ADMINISTRACIÓN)
# ==============================================================================

@user_passes_test(es_administrador)
def gestion_guias_view(request):
    """Directorio y gestión integral de guías turísticos y sus asignaciones."""
    guias = (
        Usuario.objects.filter(rol=Usuario.Roles.GUIA)
        .prefetch_related('planes_guia__paquete')
        .order_by('-id')
    )
    guias_activos = guias.filter(is_active=True).count()
    paquetes_disponibles = Paquete.objects.filter(estado=True).order_by('nombre')
    planes_activos = (
        PlanGuia.objects.filter(estado=True)
        .select_related('usuario', 'paquete')
        .order_by('-fecha_inicio_plan')
    )

    contexto = {
        'guias': guias,
        'guias_activos': guias_activos,
        'paquetes_disponibles': paquetes_disponibles,
        'planes_activos': planes_activos,
    }
    return render(request, 'admin/guias/gestion_guias.html', contexto)


@user_passes_test(es_administrador)
def guias_guardar(request):
    """Registra o actualiza la información y credenciales de un guía turístico."""
    if request.method == 'POST':
        user_id = request.POST.get('id') or request.POST.get('guia_id')
        first_name = (
            request.POST.get('first_name')
            or request.POST.get('nombre', '')
        ).strip()
        last_name = (
            request.POST.get('last_name')
            or request.POST.get('apellido', '')
        ).strip()
        email = (
            request.POST.get('email')
            or request.POST.get('correo', '')
        ).strip()
        telefono = request.POST.get('telefono', '').strip()
        tipo_documento = request.POST.get('tipo_documento', 'CC').strip()
        numero_documento = (
            request.POST.get('numero_documento')
            or request.POST.get('documento', '')
        ).strip()
        residencia = request.POST.get('residencia', '').strip()
        tarjeta_profesional = (
            request.POST.get('numero_tarjeta_profesional')
            or request.POST.get('licencia_turismo', '')
        ).strip()
        experiencia_anos_raw = (
            request.POST.get('experiencia_anos')
            or request.POST.get('experiencia', 0)
        )
        descripcion_experiencia = (
            request.POST.get('descripcion_experiencia')
            or request.POST.get('biografia', '')
        ).strip()
        entidad_salud = request.POST.get('entidad_salud', '').strip()
        password = request.POST.get('password', '').strip()
        imagen_perfil = request.FILES.get('imagen_perfil')

        # Formateo complementario si viene de modal de perfil extendido
        especialidad = request.POST.get('especialidad', '').strip()
        idiomas = request.POST.get('idiomas', '').strip()
        certificaciones = request.POST.get('certificaciones', '').strip()
        notas = request.POST.get('notas', '').strip()

        detalles_extra = []
        if especialidad:
            detalles_extra.append(f"Especialidad: {especialidad}")
        if idiomas:
            detalles_extra.append(f"Idiomas: {idiomas}")
        if certificaciones:
            detalles_extra.append(f"Certificaciones: {certificaciones}")
        if notas:
            detalles_extra.append(f"Notas: {notas}")

        if detalles_extra:
            texto_extra = "\n".join(detalles_extra)
            if descripcion_experiencia:
                if especialidad not in descripcion_experiencia:
                    descripcion_experiencia = (
                        f"{descripcion_experiencia}\n\n{texto_extra}"
                    )
            else:
                descripcion_experiencia = texto_extra

        try:
            experiencia_anos = int(experiencia_anos_raw) if experiencia_anos_raw else 0
        except (ValueError, TypeError):
            experiencia_anos = 0

        if user_id:
            user_obj = get_object_or_404(Usuario, pk=user_id)
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
                mensaje=(
                    f"Se ha actualizado la información del guía turístico: "
                    f"'{user_obj.get_full_name() or user_obj.username}'."
                ),
                tipo="Guía Turístico",
                prioridad="media"
            )
            messages.success(
                request,
                f"Guía '{user_obj.get_full_name() or user_obj.username}' "
                f"actualizado correctamente."
            )
        else:
            username = request.POST.get('username', '').strip()
            if not username:
                username = email.split('@')[0] if email else f"guia_{numero_documento}"

            if Usuario.objects.filter(username=username).exists():
                messages.error(request, f"El nombre de usuario '{username}' ya está en uso.")
                return redirect('gestion_guias')

            if email and Usuario.objects.filter(email=email).exists():
                messages.error(request, f"El correo '{email}' ya se encuentra registrado.")
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
                mensaje=(
                    f"Se ha registrado un nuevo guía turístico: "
                    f"'{user_obj.get_full_name() or user_obj.username}'."
                ),
                tipo="Guía Turístico",
                prioridad="media"
            )
            messages.success(
                request,
                f"Guía '{user_obj.get_full_name() or user_obj.username}' "
                f"registrado exitosamente."
            )

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
            msg = (
                f"Se ha retirado el rol de guía a '{user_obj.username}' "
                f"(ahora es Cliente/Turista)."
            )
        else:
            user_obj.rol = Usuario.Roles.GUIA
            msg = f"Se ha asignado el rol de guía turístico a '{user_obj.username}'."

        user_obj.save()

        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"Cambio de rol para '{user_obj.username}': {msg}",
            tipo="Guía Turístico",
            prioridad="media"
        )
        messages.success(request, msg)

    return redirect('gestion_guias')


@user_passes_test(es_administrador)
def asignar_tour_guia(request, guia_id):
    """
    Asigna un paquete turístico a un guía para fechas específicas.
    Previene solapamientos con asignaciones activas previas.
    """
    if request.method == 'POST':
        guia = get_object_or_404(Usuario, pk=guia_id, rol=Usuario.Roles.GUIA)
        paquete_id = request.POST.get('paquete_id')
        fecha_inicio_raw = (
            request.POST.get('fecha_servicio')
            or request.POST.get('fecha_inicio_plan')
        )
        fecha_fin_raw = request.POST.get('fecha_fin_plan')
        idioma = request.POST.get('idioma_servicio', 'Español').strip() or 'Español'

        if not paquete_id or not fecha_inicio_raw:
            messages.error(
                request,
                "Debe seleccionar un paquete y la fecha de inicio del servicio."
            )
            return redirect('gestion_guias')

        paquete = get_object_or_404(Paquete, pk=paquete_id)

        try:
            fecha_inicio = datetime.strptime(fecha_inicio_raw, '%Y-%m-%d').date()
            if fecha_fin_raw:
                fecha_fin = datetime.strptime(fecha_fin_raw, '%Y-%m-%d').date()
            else:
                duracion_dias = getattr(paquete, 'dias_duracion', 1) or 1
                fecha_fin = fecha_inicio + timedelta(days=max(duracion_dias - 1, 0))
        except ValueError:
            messages.error(request, "Formato de fecha inválido. Use AAAA-MM-DD.")
            return redirect('gestion_guias')

        if fecha_fin < fecha_inicio:
            messages.error(
                request,
                "La fecha de fin no puede ser anterior a la fecha de inicio."
            )
            return redirect('gestion_guias')

        # Verificar solapamiento de fechas
        solapamiento = PlanGuia.objects.filter(
            usuario=guia,
            estado=True,
            fecha_inicio_plan__lte=fecha_fin,
            fecha_fin_plan__gte=fecha_inicio
        )
        if solapamiento.exists():
            conflicto = solapamiento.first()
            messages.warning(
                request,
                f"El guía '{guia.get_full_name() or guia.username}' ya tiene "
                f"una asignación activa en esas fechas: "
                f"'{conflicto.paquete.nombre}' del "
                f"{conflicto.fecha_inicio_plan.strftime('%d/%m/%Y')} al "
                f"{conflicto.fecha_fin_plan.strftime('%d/%m/%Y')}."
            )
            return redirect('gestion_guias')

        PlanGuia.objects.create(
            usuario=guia,
            paquete=paquete,
            fecha_inicio_plan=fecha_inicio,
            fecha_fin_plan=fecha_fin,
            idioma_servicio=idioma,
            estado=True
        )

        crear_notificacion_sistema(
            usuario=guia,
            mensaje=(
                f"Has sido asignado como guía oficial para el paquete "
                f"'{paquete.nombre}' del "
                f"{fecha_inicio.strftime('%d/%m/%Y')} al "
                f"{fecha_fin.strftime('%d/%m/%Y')}."
            ),
            tipo="Asignación de Tour",
            prioridad="alta"
        )

        messages.success(
            request,
            f"Asignación registrada: {guia.get_full_name() or guia.username} "
            f"— {paquete.nombre} "
            f"({fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')})."
        )

    return redirect('gestion_guias')


@user_passes_test(es_administrador)
def toggle_plan_guia(request, plan_id):
    """Activa o desactiva una asignación de tour (PlanGuia)."""
    if request.method == 'POST':
        plan = get_object_or_404(PlanGuia, pk=plan_id)
        plan.estado = not plan.estado
        plan.save(update_fields=['estado'])
        estado_desc = "activada" if plan.estado else "desactivada"
        messages.success(
            request,
            f"La asignación del paquete '{plan.paquete.nombre}' a "
            f"'{plan.usuario.get_full_name() or plan.usuario.username}' "
            f"ha sido {estado_desc}."
        )
    return redirect('gestion_guias')


# ==============================================================================
# PANEL Y ASIGNACIONES DEL GUÍA TURÍSTICO (VISTA PERSONAL)
# ==============================================================================

@login_required
def dashboard_guia(request):
    """Panel de control personal del guía turístico autenticado."""
    if not getattr(request.user, 'es_guia', False):
        return redirect('index')

    hoy = timezone.now().date()
    mis_planes = (
        PlanGuia.objects.filter(usuario=request.user)
        .select_related('paquete')
        .order_by('fecha_inicio_plan')
    )
    planes_activos = mis_planes.filter(estado=True, fecha_fin_plan__gte=hoy)
    planes_pasados = mis_planes.filter(estado=True, fecha_fin_plan__lt=hoy)
    plan_proximo = planes_activos.order_by('fecha_inicio_plan').first()

    return render(request, 'usuario/guia/dashboard_guia.html', {
        'mis_planes': mis_planes,
        'planes_activos': planes_activos,
        'planes_pasados': planes_pasados,
        'plan_proximo': plan_proximo,
        'hoy': hoy,
    })


@login_required
def mis_asignaciones_guia(request):
    """Lista completa de los tours asignados al guía autenticado."""
    if not getattr(request.user, 'es_guia', False):
        return redirect('index')

    hoy = timezone.now().date()
    mis_planes = (
        PlanGuia.objects.filter(usuario=request.user)
        .select_related('paquete')
        .order_by('-fecha_inicio_plan')
    )
    return render(request, 'usuario/guia/mis_asignaciones.html', {
        'mis_planes': mis_planes,
        'hoy': hoy,
    })
