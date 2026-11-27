import json
import random
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from App.models import Usuario, Paquete, Reserva, Pago, Bitacora, PQRS, Calificacion
from App.utils import crear_notificacion_sistema, registrar_bitacora
from App.forms.usuario.forms import PerfilTuristaForm, PerfilGuiaForm, CambiarClaveSeguraForm
from App.validators import validar_archivo_subido, validar_foto_perfil


def es_administrador(user):
    return user.is_authenticated and user.is_active and (user.is_staff or getattr(user, 'rol', None) == Usuario.Roles.ADMIN)


@login_required
def panel_rapido_view(request):
    if not getattr(request.user, 'es_turista', False):
        if request.user.is_staff or getattr(request.user, 'rol', None) == Usuario.Roles.ADMIN:
            return redirect('dashboard_admin')
        return redirect('index')

    user = request.user

    # 1. Recomendación dinámica de paquetes con imagen
    paquetes_activos = list(Paquete.objects.filter(estado=True))
    paquetes_con_imagen = [p for p in paquetes_activos if p.imagen]
    if not paquetes_con_imagen:
        paquetes_con_imagen = paquetes_activos

    recomendacion = random.choice(paquetes_con_imagen) if paquetes_con_imagen else None

    recomendaciones_data = []
    for p in paquetes_con_imagen:
        if p.imagen:
            recomendaciones_data.append({
                'nombre': p.nombre,
                'imagen_url': p.imagen.url
            })

    # 2. Métricas y estadísticas del viajero
    reservas_qs = Reserva.objects.filter(usuario=user).select_related('paquete')
    total_reservas = reservas_qs.count()
    reservas_confirmadas = reservas_qs.filter(estado_reserva='confirmada').count()
    reservas_pendientes = reservas_qs.filter(estado_reserva='pendiente').count()
    total_pqrs = PQRS.objects.filter(usuario=user).count()
    total_calificaciones = Calificacion.objects.filter(reserva__usuario=user).count()

    # 3. Próxima aventura o última reserva activa
    hoy = timezone.now().date()
    proxima_reserva = reservas_qs.filter(
        estado_reserva__in=['confirmada', 'pendiente'],
        fecha_inicio__gte=hoy
    ).order_by('fecha_inicio').first()

    if not proxima_reserva:
        proxima_reserva = reservas_qs.order_by('-fecha_registro').first()

    # 4. Historial reciente de reservas (últimas 4)
    ultimas_reservas = reservas_qs.order_by('-id')[:4]

    contexto = {
        'recomendacion': recomendacion,
        'recomendaciones_data': recomendaciones_data,
        'total_reservas': total_reservas,
        'reservas_confirmadas': reservas_confirmadas,
        'reservas_pendientes': reservas_pendientes,
        'total_pqrs': total_pqrs,
        'total_calificaciones': total_calificaciones,
        'proxima_reserva': proxima_reserva,
        'ultimas_reservas': ultimas_reservas,
        'recomendaciones_json': json.dumps(recomendaciones_data),
    }

    return render(request, 'usuario/dashboard/panel_rapido.html', contexto)


@login_required
def perfil_turista_view(request):
    """
    Renderiza y gestiona la actualización segura del perfil unificado (Turista, Admin, Guía).
    Utiliza ModelForms con listas blancas estrictas para neutralizar cualquier inyección
    de campos privilegiados (rol, is_staff, is_superuser, password, email) desde DevTools.
    """
    user = request.user
    form_class = PerfilGuiaForm if getattr(user, 'es_guia', False) else PerfilTuristaForm

    if request.method == 'POST' and request.POST.get('editar_perfil') == '1':
        form = form_class(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado correctamente.')
            return redirect(request.path)
        else:
            errores_txt = [str(err[0]) for err in form.errors.values()]
            messages.error(request, f"Error al actualizar perfil: {' '.join(errores_txt)}")

    reservas_recientes = []
    stats_turista = {}
    stats_admin = {}

    if getattr(user, 'es_admin', False) or user.is_staff or user.is_superuser:
        from App.models import Reserva, Pago, PQRS, Paquete
        stats_admin = {
            'total_reservas': Reserva.objects.count(),
            'reservas_pendientes': Reserva.objects.filter(estado_reserva__in=['pendiente', 'PENDIENTE']).count(),
            'total_paquetes': Paquete.objects.filter(estado=True).count(),
            'total_pqrs_pendientes': PQRS.objects.exclude(estado__in=['cerrado', 'cerrada', 'resuelto']).count(),
        }
    else:
        from App.models import Reserva, Pago
        reservas_qs = Reserva.objects.filter(usuario=user).select_related('paquete').order_by('-fecha_registro', '-id')
        reservas_recientes = list(reservas_qs[:3])
        stats_turista = {
            'total_reservas': reservas_qs.count(),
            'reservas_confirmadas': reservas_qs.filter(estado_reserva__in=['confirmada', 'CONFIRMADA', 'completada']).count(),
            'reservas_pendientes': reservas_qs.filter(estado_reserva__in=['pendiente', 'PENDIENTE']).count(),
            'saldo_favor': getattr(user, 'saldo_favor', 0),
        }

    return render(request, 'usuario/perfil/perfil.html', {
        'user': user,
        'reservas_recientes': reservas_recientes,
        'stats_turista': stats_turista,
        'stats_admin': stats_admin,
    })
 
 
@login_required
def configuracion_usuario_view(request):
    """
    Vista integral y funcional para la Configuración de Cuenta, Seguridad y Preferencias del Usuario.
    Procesa:
    1. Cambio de contraseña con validación de seguridad y actualización de hash de sesión.
    2. Preferencias de notificaciones por email y sonidos del sistema.
    3. Preferencias de interfaz (idioma, tema visual, formato de fecha).
    4. Privacidad y visibilidad del perfil.
    5. Actualización de datos de contacto directo.
    6. Exportación de datos de usuario en formato JSON (Habeas Data).
    7. Cierre de otras sesiones activas para seguridad.
    """
    user = request.user

    # Descarga de datos personales (Habeas Data)
    if request.GET.get('exportar') == 'json' or request.POST.get('accion') == 'exportar_datos':
        import json
        from django.http import HttpResponse
        from App.models import Reserva, Pago, PQRS

        total_reservas = Reserva.objects.filter(usuario=user).count()
        total_pagos = Pago.objects.filter(reserva__usuario=user).count()
        total_pqrs = PQRS.objects.filter(usuario=user).count()

        datos_exportacion = {
            'sistema': 'Monagua Turismo Ecoturístico',
            'fecha_exportacion': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            'usuario': {
                'id': user.id,
                'username': user.username,
                'nombres': user.first_name,
                'apellidos': user.last_name,
                'email': user.email,
                'tipo_documento': user.get_tipo_documento_display() if hasattr(user, 'get_tipo_documento_display') else user.tipo_documento,
                'numero_documento': user.numero_documento,
                'telefono': user.telefono,
                'residencia': user.residencia,
                'rol': user.get_rol_display() if hasattr(user, 'get_rol_display') else str(user.rol),
                'fecha_registro': user.date_joined.strftime('%Y-%m-%d %H:%M:%S') if user.date_joined else None,
                'ultimo_acceso': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
            },
            'resumen_actividad': {
                'total_reservas': total_reservas,
                'total_pagos': total_pagos,
                'total_pqrs': total_pqrs,
            }
        }

        response = HttpResponse(
            json.dumps(datos_exportacion, indent=4, ensure_ascii=False),
            content_type='application/json; charset=utf-8'
        )
        response['Content-Disposition'] = f'attachment; filename="datos_cuenta_monagua_{user.username}.json"'
        return response

    if request.method == 'POST':
        accion = request.POST.get('accion')

        # 1. Cambio de Contraseña Seguro con validación en servidor
        if accion == 'cambiar_clave':
            form_clave = CambiarClaveSeguraForm(user=user, data=request.POST)
            if form_clave.is_valid():
                user.set_password(form_clave.cleaned_data['new_password'])
                user.save()
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, '¡Tu contraseña ha sido actualizada con éxito!')
            else:
                errores_txt = [str(err[0]) for err in form_clave.errors.values()]
                messages.error(request, f"Error al actualizar la contraseña: {' '.join(errores_txt)}")
            return redirect('configuracion_usuario')

        # 2. Preferencias de Notificaciones y Sistema
        elif accion == 'guardar_preferencias':
            notif_reservas = bool(request.POST.get('notif_reservas'))
            notif_pagos = bool(request.POST.get('notif_pagos'))
            notif_promos = bool(request.POST.get('notif_promos'))
            notif_sonido = bool(request.POST.get('notif_sonido'))
            autenticacion_dos_pasos = bool(request.POST.get('autenticacion_dos_pasos'))
            visibilidad_perfil = request.POST.get('visibilidad_perfil', 'publico')
            tema_visual = request.POST.get('tema_visual', 'claro')
            idioma_pref = request.POST.get('idioma_pref', 'es')

            request.session['pref_notif_reservas'] = notif_reservas
            request.session['pref_notif_pagos'] = notif_pagos
            request.session['pref_notif_promos'] = notif_promos
            request.session['pref_notif_sonido'] = notif_sonido
            request.session['pref_2fa'] = autenticacion_dos_pasos
            request.session['pref_visibilidad'] = visibilidad_perfil
            request.session['pref_tema_visual'] = tema_visual
            request.session['pref_idioma'] = idioma_pref

            messages.success(request, 'Preferencias del sistema y notificaciones actualizadas correctamente.')
            return redirect('configuracion_usuario')

        # 3. Actualizar Contacto Rápido
        elif accion == 'actualizar_contacto':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            telefono = request.POST.get('telefono', '').strip()
            residencia = request.POST.get('residencia', '').strip()

            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if telefono:
                user.telefono = telefono
            if residencia:
                user.residencia = residencia

            user.save()
            messages.success(request, 'Información de contacto y datos personales actualizados.')
            return redirect('configuracion_usuario')

        # 4. Cerrar Otras Sesiones
        elif accion == 'cerrar_otras_sesiones':
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            messages.success(request, 'Se han revocado las credenciales en otros dispositivos.')
            return redirect('configuracion_usuario')

    # Preferencias actuales de la sesión (o defaults)
    preferencias = {
        'notif_reservas': request.session.get('pref_notif_reservas', True),
        'notif_pagos': request.session.get('pref_notif_pagos', True),
        'notif_promos': request.session.get('pref_notif_promos', True),
        'notif_sonido': request.session.get('pref_notif_sonido', True),
        'autenticacion_dos_pasos': request.session.get('pref_2fa', False),
        'visibilidad_perfil': request.session.get('pref_visibilidad', 'publico'),
        'tema_visual': request.session.get('pref_tema_visual', 'claro'),
        'idioma_pref': request.session.get('pref_idioma', 'es'),
    }

    # Cálculo del Nivel de Seguridad de la Cuenta
    score_seguridad = 25  # Base por cuenta creada
    if user.email:
        score_seguridad += 25
    if user.telefono:
        score_seguridad += 25
    if getattr(user, 'numero_documento', None):
        score_seguridad += 25

    # Datos de sesión
    ip_cliente = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1'))
    if ',' in ip_cliente:
        ip_cliente = ip_cliente.split(',')[0].strip()

    contexto = {
        'user': user,
        'preferencias': preferencias,
        'score_seguridad': score_seguridad,
        'ip_cliente': ip_cliente,
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Navegador Web'),
    }

    return render(request, 'usuario/perfil/configuracion.html', contexto)


# ==============================================================================
# GESTIÓN DE USUARIOS (ADMINISTRACIÓN)
# ==============================================================================

def _construir_expediente_usuario(u):
    """
    Construye el expediente integral de actividad de un usuario para consulta administrativa:
    - Paquetes comprados / reservas realizadas y métricas financieras.
    - Comprobantes de pago, PQRS, calificaciones y planes guía.
    - Bitácora cronológica unificada de todas las acciones del usuario.
    """
    reservas_list = sorted(
        list(u.reservas.all()),
        key=lambda r: r.fecha_registro or timezone.now(),
        reverse=True,
    )
    u.reservas_list = reservas_list
    u.total_reservas_count = len(reservas_list)
    u.paquetes_comprados_count = sum(1 for r in reservas_list if r.estado_reserva == 'confirmada')
    u.reservas_pendientes_count = sum(1 for r in reservas_list if r.estado_reserva == 'pendiente')
    u.reservas_canceladas_count = sum(1 for r in reservas_list if r.estado_reserva == 'cancelada')

    pagos_list = []
    calificaciones_list = []
    modificaciones_list = []
    total_invertido = Decimal('0.00')

    for r in reservas_list:
        pago_obj = getattr(r, 'pago', None)
        if pago_obj:
            pagos_list.append(pago_obj)
            if pago_obj.estado_transaccion == 'aprobado':
                total_invertido += (pago_obj.monto or r.monto_total or Decimal('0.00'))
        elif r.estado_reserva == 'confirmada':
            total_invertido += (r.monto_total or Decimal('0.00'))

        for cal in r.calificaciones.all():
            calificaciones_list.append(cal)
        for mod in r.modificaciones_personas.all():
            modificaciones_list.append(mod)

    pagos_list.sort(key=lambda p: p.fecha_envio or timezone.now(), reverse=True)
    calificaciones_list.sort(key=lambda c: c.fecha_calificacion or timezone.now(), reverse=True)

    pqrs_list = sorted(
        list(u.pqrs.all()),
        key=lambda pq: pq.fecha or timezone.now(),
        reverse=True,
    )
    planes_guia_list = sorted(
        list(u.planes_guia.all()),
        key=lambda pg: pg.fecha_creacion or timezone.now(),
        reverse=True,
    )
    notas_credito_list = sorted(
        list(u.notas_credito.all()),
        key=lambda nc: nc.fecha_emision or timezone.now(),
        reverse=True,
    )
    reembolsos_list = sorted(
        list(u.reembolsos.all()),
        key=lambda rb: rb.fecha_solicitud or timezone.now(),
        reverse=True,
    )

    u.pagos_list = pagos_list
    u.calificaciones_list = calificaciones_list
    u.pqrs_list = pqrs_list
    u.planes_guia_list = planes_guia_list
    u.notas_credito_list = notas_credito_list
    u.reembolsos_list = reembolsos_list
    u.total_invertido = total_invertido

    # ── Construcción de la Bitácora Unificada del Usuario ──
    eventos = []
    claves_registradas = set()

    accion_meta = {
        'INSERT': ('Creación / Registro', 'success', 'bi-plus-circle-fill'),
        'UPDATE': ('Actualización / Cambio', 'primary', 'bi-pencil-square'),
        'DELETE': ('Eliminación', 'danger', 'bi-trash3-fill'),
        'LOGIN': ('Inicio de Sesión', 'info', 'bi-box-arrow-in-right'),
        'LOGOUT': ('Cierre de Sesión', 'secondary', 'bi-box-arrow-right'),
        'ACCESO': ('Acceso / Consulta', 'info', 'bi-eye-fill'),
        'RESPUESTA': ('Respuesta / Seguimiento', 'primary', 'bi-reply-fill'),
        'NOTIFICACION': ('Notificación', 'warning', 'bi-bell-fill'),
    }

    # 1. Registros explícitos en tabla Bitacora (hechos por el usuario o sobre sus reservas/pagos/pqrs)
    bitacoras_db = Bitacora.objects.filter(
        Q(usuario=u) |
        Q(reserva__usuario=u) |
        Q(pago__reserva__usuario=u) |
        Q(pqrs__usuario=u)
    ).select_related('usuario', 'reserva', 'pago', 'pqrs').distinct().order_by('-fecha_registro')[:60]

    for b in bitacoras_db:
        label, color, icon = accion_meta.get(b.accion, (b.get_accion_display(), 'secondary', 'bi-activity'))
        autor_txt = ""
        if b.usuario and b.usuario_id != u.id:
            autor_txt = f" (Gestionado por Admin: @{b.usuario.username})"
        eventos.append({
            'id': f"BIT-{b.id}",
            'accion_codigo': b.accion,
            'accion_label': label,
            'modulo': b.modulo or 'General',
            'descripcion': f"{b.descripcion or 'Acción registrada en el sistema.'}{autor_txt}",
            'fecha': b.fecha_registro,
            'ip_origen': b.ip_origen,
            'badge_color': color,
            'icono': icon,
            'registro_id': b.registro_id,
        })
        if b.modulo and b.registro_id:
            claves_registradas.add((b.modulo.lower(), b.registro_id, b.accion))

    # 2. Eventos históricos de Reservas / Paquetes comprados
    for r in reservas_list:
        nombre_paq = r.paquete.nombre if r.paquete else 'Paquete turístico'
        if ('reservas', r.id, 'INSERT') not in claves_registradas:
            eventos.append({
                'id': f"RES-{r.id}",
                'accion_codigo': 'INSERT',
                'accion_label': 'Reserva de Paquete',
                'modulo': 'Reservas',
                'descripcion': (
                    f"Reservó el paquete '{nombre_paq}' (Reserva #{r.id}) para "
                    f"{r.numero_adultos} adulto(s) y {r.numero_menores} menor(es) por COP ${r.monto_total:,.0f}. "
                    f"Estado actual: {r.get_estado_reserva_display()}."
                ),
                'fecha': r.fecha_registro,
                'ip_origen': None,
                'badge_color': 'success',
                'icono': 'bi-bag-check-fill',
                'registro_id': r.id,
            })
        if r.estado_reserva == 'cancelada' or r.motivo_cancelacion:
            if ('cancelaciones', r.id, 'UPDATE') not in claves_registradas:
                eventos.append({
                    'id': f"CAN-{r.id}",
                    'accion_codigo': 'UPDATE',
                    'accion_label': 'Cancelación de Reserva',
                    'modulo': 'Reservas',
                    'descripcion': (
                        f"Solicitud de cancelación en Reserva #{r.id} ('{nombre_paq}'). "
                        f"Motivo: {r.motivo_cancelacion or 'No especificado'}."
                    ),
                    'fecha': r.fecha_reembolso or r.fecha_registro,
                    'ip_origen': None,
                    'badge_color': 'danger',
                    'icono': 'bi-x-octagon-fill',
                    'registro_id': r.id,
                })

    # 3. Modificaciones de cantidad de personas
    for mod in modificaciones_list:
        eventos.append({
            'id': f"MOD-{mod.id}",
            'accion_codigo': 'UPDATE',
            'accion_label': 'Modificación de Pasajeros',
            'modulo': 'Reservas',
            'descripcion': (
                f"Cambio de pasajeros en Reserva #{mod.reserva_id}: "
                f"de {mod.adultos_anteriores} ad. / {mod.menores_anteriores} men. "
                f"a {mod.adultos_nuevos} ad. / {mod.menores_nuevos} men. "
                f"(Monto: COP ${mod.monto_anterior:,.0f} → COP ${mod.monto_nuevo:,.0f})."
            ),
            'fecha': mod.fecha_modificacion,
            'ip_origen': None,
            'badge_color': 'primary',
            'icono': 'bi-people-fill',
            'registro_id': mod.reserva_id,
        })

    # 4. Eventos de Comprobantes de Pago enviados
    for p in pagos_list:
        nombre_paq = p.reserva.paquete.nombre if (p.reserva and p.reserva.paquete) else 'Reserva'
        if ('comprobantes de pago', p.id, 'INSERT') not in claves_registradas:
            eventos.append({
                'id': f"PAG-{p.id}",
                'accion_codigo': 'INSERT',
                'accion_label': 'Envío de Comprobante',
                'modulo': 'Comprobantes de Pago',
                'descripcion': (
                    f"Envió comprobante de pago #{p.id} para '{nombre_paq}' (Reserva #{p.reserva_id}) "
                    f"por COP ${p.monto:,.0f} vía {p.banco_origen} (Ref: {p.referencia}). "
                    f"Estado: {p.get_estado_transaccion_display()}."
                ),
                'fecha': p.fecha_envio,
                'ip_origen': None,
                'badge_color': 'success' if p.estado_transaccion == 'aprobado' else ('danger' if p.estado_transaccion == 'rechazado' else 'warning'),
                'icono': 'bi-receipt-cutoff',
                'registro_id': p.id,
            })

    # 5. Notas de Crédito / Reembolsos
    for nc in notas_credito_list:
        eventos.append({
            'id': f"NC-{nc.id}",
            'accion_codigo': 'INSERT',
            'accion_label': 'Nota de Crédito',
            'modulo': 'Pagos / Créditos',
            'descripcion': (
                f"Generación de Nota de Crédito {nc.codigo} en Reserva #{nc.reserva_id} "
                f"({nc.cupos_liberados} cupos liberados). Monto acreditado/devuelto: COP ${nc.monto_devuelto:,.0f}."
            ),
            'fecha': nc.fecha_emision,
            'ip_origen': None,
            'badge_color': 'info',
            'icono': 'bi-wallet2',
            'registro_id': nc.id,
        })

    # 6. Solicitudes PQRS radicadas
    for pq in pqrs_list:
        if ('pqrs', pq.id, 'INSERT') not in claves_registradas:
            eventos.append({
                'id': f"PQRS-{pq.id}",
                'accion_codigo': 'INSERT',
                'accion_label': f"PQRS ({pq.get_tipo_display()})",
                'modulo': 'PQRS',
                'descripcion': f"Radicó {pq.radicado or f'PQRS #{pq.id}'}: '{pq.asunto}' — Estado: {pq.get_estado_display()}.",
                'fecha': pq.fecha,
                'ip_origen': None,
                'badge_color': 'warning',
                'icono': 'bi-chat-left-text-fill',
                'registro_id': pq.id,
            })

    # 7. Calificaciones / Reseñas publicadas
    for cal in calificaciones_list:
        paq_txt = cal.reserva.paquete.nombre if (cal.reserva and cal.reserva.paquete) else 'Experiencia Monagua'
        eventos.append({
            'id': f"CAL-{cal.id}",
            'accion_codigo': 'INSERT',
            'accion_label': 'Calificación / Reseña',
            'modulo': 'Calificaciones',
            'descripcion': f"Calificó '{paq_txt}' con {cal.puntaje_estrellas} estrella(s): \"{cal.titulo}\".",
            'fecha': cal.fecha_calificacion,
            'ip_origen': None,
            'badge_color': 'warning',
            'icono': 'bi-star-fill',
            'registro_id': cal.id,
        })

    # 8. Último inicio de sesión y fecha de registro de la cuenta
    if u.last_login:
        eventos.append({
            'id': f"LOGIN-{u.id}",
            'accion_codigo': 'LOGIN',
            'accion_label': 'Último Inicio de Sesión',
            'modulo': 'Autenticación',
            'descripcion': f"Inicio de sesión autenticado en la plataforma con la cuenta @{u.username}.",
            'fecha': u.last_login,
            'ip_origen': None,
            'badge_color': 'info',
            'icono': 'bi-box-arrow-in-right',
            'registro_id': u.id,
        })

    if u.date_joined:
        eventos.append({
            'id': f"JOIN-{u.id}",
            'accion_codigo': 'INSERT',
            'accion_label': 'Alta / Creación de Cuenta',
            'modulo': 'Usuarios',
            'descripcion': f"Registro inicial de la cuenta @{u.username} con rol '{u.get_rol_display()}'.",
            'fecha': u.date_joined,
            'ip_origen': None,
            'badge_color': 'secondary',
            'icono': 'bi-person-check-fill',
            'registro_id': u.id,
        })

    eventos.sort(key=lambda e: e['fecha'] or timezone.now(), reverse=True)
    u.bitacora_list = eventos
    u.total_acciones_bitacora = len(eventos)


@user_passes_test(es_administrador)
def gestion_usuarios_admin(request):
    """Directorio, expediente de paquetes comprados, bitácora y gestión de cuentas de usuario en el panel de administración."""
    filtro = request.GET.get('filtro', '').strip()
    query = request.GET.get('q', '').strip()

    usuarios_qs = Usuario.objects.all().prefetch_related(
        'reservas__paquete',
        'reservas__pago',
        'reservas__notas_credito',
        'reservas__reembolsos',
        'reservas__modificaciones_personas',
        'reservas__calificaciones',
        'pqrs',
        'planes_guia__paquete',
        'notas_credito',
        'reembolsos',
    ).order_by('-id')

    rol_mapping = {
        'ADMIN': Usuario.Roles.ADMIN,
        '1': Usuario.Roles.ADMIN,
        'CLIENTE': Usuario.Roles.CLIENTE,
        '2': Usuario.Roles.CLIENTE,
        'GUIA': Usuario.Roles.GUIA,
        '3': Usuario.Roles.GUIA,
    }

    if filtro:
        filtro_norm = filtro.upper()
        if filtro_norm in rol_mapping:
            usuarios_qs = usuarios_qs.filter(rol=rol_mapping[filtro_norm])
        elif filtro_norm in ['ACTIVO', 'ACTIVOS']:
            usuarios_qs = usuarios_qs.filter(is_active=True)
        elif filtro_norm in ['INACTIVO', 'INACTIVOS']:
            usuarios_qs = usuarios_qs.filter(is_active=False)

    if query:
        usuarios_qs = usuarios_qs.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(numero_documento__icontains=query) |
            Q(telefono__icontains=query)
        )

    usuarios = list(usuarios_qs)
    for u in usuarios:
        _construir_expediente_usuario(u)

    total_usuarios = Usuario.objects.count()
    total_admins = Usuario.objects.filter(rol=Usuario.Roles.ADMIN).count()
    total_guias = Usuario.objects.filter(rol=Usuario.Roles.GUIA).count()
    total_clientes = Usuario.objects.filter(rol=Usuario.Roles.CLIENTE).count()

    contexto = {
        'usuarios': usuarios,
        'filtro_actual': filtro,
        'total_usuarios': total_usuarios,
        'total_admins': total_admins,
        'total_guias': total_guias,
        'total_clientes': total_clientes,
    }
    return render(request, 'admin/usuario/gestion_usuarios.html', contexto)


@user_passes_test(es_administrador)
def usuarios_guardar(request):
    """Crea o actualiza la información básica de un usuario (sin alteración de rol)."""
    if request.method == 'POST':
        user_id = request.POST.get('id')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        telefono = request.POST.get('telefono', '').strip()
        tipo_documento = request.POST.get('tipo_documento', 'CC').strip()
        numero_documento = request.POST.get('numero_documento', '').strip()
        residencia = request.POST.get('residencia', '').strip()
        password = request.POST.get('password', '').strip()
        imagen_perfil = request.FILES.get('imagen_perfil')

        if imagen_perfil:
            valido, err = validar_archivo_subido(imagen_perfil, validar_foto_perfil)
            if not valido:
                messages.error(request, err)
                return redirect('gestion_usuarios')

        if user_id:
            user_obj = get_object_or_404(Usuario, pk=user_id)

            if email and Usuario.objects.filter(email=email).exclude(pk=user_obj.pk).exists():
                messages.error(request, f"El correo '{email}' ya se encuentra registrado por otro usuario.")
                return redirect('gestion_usuarios')

            if numero_documento and Usuario.objects.filter(numero_documento=numero_documento).exclude(pk=user_obj.pk).exists():
                messages.error(request, f"El número de documento '{numero_documento}' ya pertenece a otro usuario.")
                return redirect('gestion_usuarios')

            user_obj.first_name = first_name
            user_obj.last_name = last_name
            if email:
                user_obj.email = email
            user_obj.telefono = telefono
            user_obj.tipo_documento = tipo_documento
            user_obj.numero_documento = numero_documento
            user_obj.residencia = residencia

            # NOTA: El rol del usuario NO se modifica en este módulo.

            if password:
                user_obj.set_password(password)
            if imagen_perfil:
                user_obj.imagen_perfil = imagen_perfil

            user_obj.save()

            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"Se ha actualizado la información del usuario '{user_obj.username}'.",
                tipo="Usuario",
                prioridad="media"
            )
            messages.success(request, f"Usuario '{user_obj.username}' actualizado correctamente.")
        else:
            username = request.POST.get('username', '').strip()
            if not username:
                username = email.split('@')[0] if email else f"user_{numero_documento}"

            if Usuario.objects.filter(username=username).exists():
                messages.error(request, f"El nombre de usuario '{username}' ya está en uso.")
                return redirect('gestion_usuarios')

            if email and Usuario.objects.filter(email=email).exists():
                messages.error(request, f"El correo '{email}' ya se encuentra registrado.")
                return redirect('gestion_usuarios')

            if numero_documento and Usuario.objects.filter(numero_documento=numero_documento).exists():
                messages.error(request, f"El número de documento '{numero_documento}' ya se encuentra registrado.")
                return redirect('gestion_usuarios')

            # Para nuevos registros: Administrador o Cliente (por defecto Cliente)
            rol_input = request.POST.get('rol', '').strip()
            rol = Usuario.Roles.ADMIN if str(rol_input).upper() in ['ADMIN', '1'] else Usuario.Roles.CLIENTE

            user_obj = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password or 'Monagua2026*',
                first_name=first_name,
                last_name=last_name,
                rol=rol,
                telefono=telefono,
                tipo_documento=tipo_documento,
                numero_documento=numero_documento,
                residencia=residencia,
                is_staff=(rol == Usuario.Roles.ADMIN)
            )
            if imagen_perfil:
                user_obj.imagen_perfil = imagen_perfil
                user_obj.save()

            crear_notificacion_sistema(
                usuario=request.user,
                mensaje=f"Se ha creado un nuevo usuario '{user_obj.username}' con rol '{user_obj.get_rol_display()}'.",
                tipo="Usuario",
                prioridad="media"
            )
            messages.success(request, f"Usuario '{user_obj.username}' creado exitosamente.")

    return redirect('gestion_usuarios')


@user_passes_test(es_administrador)
def usuarios_toggle_estado(request, id):
    """Activa o desactiva la cuenta de un usuario."""
    if request.method == 'POST':
        user_obj = get_object_or_404(Usuario, pk=id)
        if user_obj.id == request.user.id:
            messages.error(request, "No puedes desactivar tu propia cuenta de administrador.")
            return redirect('gestion_usuarios')

        user_obj.is_active = not user_obj.is_active
        user_obj.save()

        estado_txt = "activada" if user_obj.is_active else "desactivada"
        crear_notificacion_sistema(
            usuario=request.user,
            mensaje=f"La cuenta de '{user_obj.username}' ha sido {estado_txt}.",
            tipo="Usuario",
            prioridad="media"
        )
        messages.success(request, f"La cuenta de '{user_obj.username}' ha sido {estado_txt}.")

    return redirect('gestion_usuarios')