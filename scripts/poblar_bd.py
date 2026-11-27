r"""
Script de poblado inicial de base de datos para Monagua (Turismo en Mongua, Boyacá).

Estructura modular con datos reales y consistentes para todos los módulos vigentes:
- Exactamente 5 usuarios (1 Administrador, 1 Guía Turístico, 3 Turistas/Clientes).
- Categorías, Actividades, Temporadas, Paquetes Turísticos, Tarifas, Promociones y Planes Guía.
- Reservas y Comprobantes de Pago en múltiples estados (confirmada/aprobado, pendiente/en revisión,
  pendiente/rechazado, pendiente/sin pago y cancelada) vinculados a los usuarios existentes.
- Blogs referentes a Monagua y Mongua con imágenes reales del proyecto.
- Calificaciones / Reseñas reales sobre las reservas de usuarios existentes.
- PQRS y Seguimientos realizados con usuarios existentes.
- Bitácora de auditoría y Notificaciones del sistema.

Uso:
    & ".\.venv\Scripts\python.exe" scripts\poblar_bd.py
"""

import os
import sys
import shutil
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path

import django
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Configuración del entorno Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from App.models import (
    Actividades,
    Bitacora,
    Blog,
    Calificacion,
    Categoria,
    ModificacionReserva,
    NotaCredito,
    Notificacion,
    Pago,
    Paquete,
    PaqueteActividad,
    PaquetePromocion,
    PlanGuia,
    PQRS,
    Promocion,
    Reembolso,
    Reserva,
    Seguimiento,
    Tarifa,
    Temporada,
    Usuario,
)


# ==============================================================================
# UTILIDADES DE RECURSOS VISUALES
# ==============================================================================

def copiar_imagen_a_media(nombre_archivo_static: str, subcarpeta_media: str) -> str:
    """
    Copia una imagen existente desde static/img/ hacia media/<subcarpeta_media>/
    y retorna la ruta relativa para almacenarla en un ImageField de Django.
    """
    destino_dir = Path(settings.MEDIA_ROOT) / subcarpeta_media
    destino_dir.mkdir(parents=True, exist_ok=True)

    origen = Path(settings.BASE_DIR) / 'static' / 'img' / nombre_archivo_static
    destino = destino_dir / nombre_archivo_static

    if origen.exists():
        if not destino.exists():
            shutil.copy2(origen, destino)
        return f"{subcarpeta_media}/{nombre_archivo_static}"

    # Fallback a Fondo.webp si el archivo solicitado no existe
    fallback = Path(settings.BASE_DIR) / 'static' / 'img' / 'Fondo.webp'
    if fallback.exists():
        destino_fb = destino_dir / 'Fondo.webp'
        if not destino_fb.exists():
            shutil.copy2(fallback, destino_fb)
        return f"{subcarpeta_media}/Fondo.webp"

    return ""


# ==============================================================================
# 1. LIMPIEZA CONTROLADA DE LA BASE DE DATOS
# ==============================================================================

def limpiar_base_datos():
    """Elimina los registros existentes respetando el orden de dependencias FK/PROTECT."""
    print("1. Limpiando registros existentes en la base de datos...")
    NotaCredito.objects.all().delete()
    Reembolso.objects.all().delete()
    ModificacionReserva.objects.all().delete()
    Bitacora.objects.all().delete()
    Calificacion.objects.all().delete()
    Notificacion.objects.all().delete()
    Seguimiento.objects.all().delete()
    PQRS.objects.all().delete()
    Pago.objects.all().delete()
    Reserva.objects.all().delete()
    PlanGuia.objects.all().delete()
    PaquetePromocion.objects.all().delete()
    Promocion.objects.all().delete()
    Blog.objects.all().delete()
    Tarifa.objects.all().delete()
    Temporada.objects.all().delete()
    PaqueteActividad.objects.all().delete()
    Paquete.objects.all().delete()
    Actividades.objects.all().delete()
    Categoria.objects.all().delete()
    Usuario.objects.all().delete()


# ==============================================================================
# 2. CREACIÓN DE USUARIOS (EXACTAMENTE 5 USUARIOS)
# ==============================================================================

def crear_usuarios():
    """Crea exactamente 5 usuarios reales: 1 Admin, 1 Guía Turístico y 3 Turistas."""
    print("2. Creando 5 usuarios base (1 Admin, 1 Guía, 3 Turistas)...")
    ahora = timezone.now()

    admin_user = Usuario.objects.create_superuser(
        username='admin',
        password='admin1234',
        email='admin@gmail.com',
        first_name='Administrador',
        last_name='Monagua',
        rol=Usuario.Roles.ADMIN,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='0000000001',
        telefono='3000000000',
        residencia='Mongua, Boyacá',
        pais='COL',
        last_login=ahora - timedelta(hours=1),
    )

    guia_user = Usuario.objects.create_user(
        username='guia',
        password='guia1234',
        email='camilo.mendoza@gmail.com',
        first_name='Camilo',
        last_name='Mendoza',
        rol=Usuario.Roles.GUIA,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='1052380002',
        telefono='3114502002',
        residencia='Mongua, Boyacá',
        pais='COL',
        numero_tarjeta_profesional='RNT-BOY-4821',
        experiencia_anos=7,
        experiencia_fecha=date.today() - timedelta(days=365 * 7),
        descripcion_experiencia=(
            'Guía profesional certificado en alta montaña, ecosistemas de páramo '
            'y patrimonio histórico muisca en la provincia de Sugamuxi, Boyacá.'
        ),
        entidad_salud='Nueva EPS',
        last_login=ahora - timedelta(hours=5),
    )

    turista_1 = Usuario.objects.create_user(
        username='turista',
        password='turista1234',
        email='turista@gmail.com',
        first_name='Juan Carlos',
        last_name='Pérez Morales',
        rol=Usuario.Roles.CLIENTE,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='1052380003',
        telefono='3125603003',
        residencia='Bogotá D.C.',
        pais='COL',
        last_login=ahora - timedelta(hours=2),
    )

    turista_2 = Usuario.objects.create_user(
        username='laura_gomez',
        password='turista1234',
        email='laura.gomez@monagua.com',
        first_name='Laura Sofía',
        last_name='Gómez Castillo',
        rol=Usuario.Roles.CLIENTE,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='1052380004',
        telefono='+573156704004',
        residencia='Tunja, Boyacá',
        pais='COL',
        last_login=ahora - timedelta(days=1),
    )

    turista_3 = Usuario.objects.create_user(
        username='andres_rojas',
        password='turista1234',
        email='andres.rojas@monagua.com',
        first_name='Andrés Felipe',
        last_name='Rojas Vargas',
        rol=Usuario.Roles.CLIENTE,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='1052380005',
        telefono='3187805005',
        residencia='Sogamoso, Boyacá',
        pais='COL',
        last_login=ahora - timedelta(days=2),
    )

    return {
        'admin': admin_user,
        'guia': guia_user,
        'clientes': [turista_1, turista_2, turista_3],
    }


# ==============================================================================
# 3. CATÁLOGO TURÍSTICO: CATEGORÍAS, ACTIVIDADES, TEMPORADAS, PAQUETES Y TARIFAS
# ==============================================================================

def crear_catalogo_turistico(guia_user):
    """Crea categorías, actividades, temporadas, paquetes turísticos, tarifas, promociones y planes guía."""
    print("3. Creando categorías, actividades, temporadas, paquetes y tarifas...")

    categorias_data = [
        ("Páramo y Naturaleza", "Recorridos guiados por ecosistemas de alta montaña, lagunas sagradas y frailejones en Mongua."),
        ("Senderismo y Aventura", "Rutas de caminata ecológica, miradores de cumbre y travesías por la cordillera oriental."),
        ("Patrimonio e Historia", "Sitios culturales, arquitectura colonial, plaza central, iglesia y memoria viva del municipio."),
        ("Arqueología Muisca", "Espacios vinculados con el legado indígena muisca, pictogramas y piedras ceremoniales."),
        ("Gastronomía y Cultura", "Sabores tradicionales boyacenses, amasijos en horno de leña y talleres con artesanos locales."),
        ("Familia y Recreación", "Experiencias seguras y tranquilas diseñadas para familias, grupos escolares y viajeros relajados."),
    ]
    categorias = {
        nombre: Categoria.objects.create(nombre=nombre, descripcion=desc, estado=True)
        for nombre, desc in categorias_data
    }

    actividades_data = [
        ("Senderismo al Páramo de Ocetá", "Caminata interpretativa entre frailejones gigantes, musgos y cañones rocosos de alta montaña.", "Botas impermeables, chaqueta térmica, hidratación", "Llevar ropa en capas y respetar estrictamente los senderos demarcados.", True),
        ("Contemplación en la Laguna Negra", "Recorrido paisajístico hacia la mítica Laguna Negra para observación natural y relatos locales.", "Ropa abrigada, cámara fotográfica, termo con agua", "Conservar el silencio para avistar aves andinas y preservar la serenidad del lugar.", True),
        ("Recorrido por la Iglesia y Plaza de Mongua", "Visita guiada por la arquitectura patrimonial, el templo parroquial y la historia del casco urbano.", "Calzado cómodo, bloqueador solar", "Respetar los horarios litúrgicos y apoyar el comercio local.", True),
        ("Miradores y Panoramas Andinos", "Ascenso a puntos estratégicos con vista panorámica al valle de Sugamuxi y la cordillera.", "Gafas de sol, cortavientos, cámara", "Ideal al amanecer o atardecer para capturar la neblina de montaña.", True),
        ("Ruta Arqueológica Piedras de Santo Domingo", "Interpretación de arte rupestre y vestigios ceremoniales de la cultura muisca.", "Calzado con buen agarre, gorra, agua", "No tocar ni alterar las pictografías ancestrales.", True),
        ("Degustación Gastronómica Boyacense", "Experiencia culinaria con cocido boyacense, envueltos, amasijos y bebidas calientes tradicionales.", "Disposición para disfrutar sabores locales", "Informar previamente si algún integrante tiene restricciones alimentarias.", True),
        ("Ascenso al Morro de Uche", "Travesía de exigencia media-alta hacia uno de los picos panorámicos más emblemáticos de Mongua.", "Botas de montaña, bastones de trekking, hidratación", "Recomendado únicamente para personas con buena condición física.", False),
        ("Avistamiento en Laguna de la Estrella", "Exploración ecológica de humedales de altura, flora endémica y fauna silvestre.", "Binoculares, impermeable, protector solar", "Evitar el uso de parlantes para no perturbar la fauna nativa.", True),
        ("Visita al Museo y Talleres Artesanales", "Encuentro con tejedores de lana virgen y exposición histórica de la comunidad monguana.", "Ropa cómoda", "Puedes adquirir artesanías directamente de las familias productoras.", True),
    ]
    actividades = {
        nombre: Actividades.objects.create(
            nombre=nombre,
            descripcion=desc,
            equipo_requerimiento=eq,
            recomendaciones=rec,
            estado=True,
            apto_menores=apto,
        )
        for nombre, desc, eq, rec, apto in actividades_data
    }

    hoy = date.today()
    temporadas_data = [
        ("Temporada Vigente de Páramo", "Tarifas activas para recorridos de montaña, naturaleza y patrimonio en Mongua.", hoy - timedelta(days=45), hoy + timedelta(days=120)),
        ("Temporada Vacacional y Festivos", "Periodo de alta demanda para puentes festivos, viajes familiares y expediciones.", hoy + timedelta(days=121), hoy + timedelta(days=270)),
        ("Temporada Cierre de Año", "Planificación anticipada para temporada decembrina y encuentros familiares en Boyacá.", hoy + timedelta(days=271), hoy + timedelta(days=365)),
    ]
    temporadas = [
        Temporada.objects.create(
            nombre=nombre,
            descripcion=desc,
            fecha_inicio=f_ini,
            fecha_fin=f_fin,
            estado=True,
        )
        for nombre, desc, f_ini, f_fin in temporadas_data
    ]

    paquetes_data = [
        {
            "nombre": "Páramo de Ocetá y Miradores de Mongua",
            "descripcion": "Explora uno de los páramos más hermosos del mundo con guías certificados de Monagua. Caminarás entre bosques de frailejones, formaciones rocosas milenarias y miradores inolvidables.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Parque Principal de Mongua",
            "hora_encuentro": time(6, 30),
            "imagen": "paramo.webp",
            "categoria": "Páramo y Naturaleza",
            "precio_adulto": Decimal("52000"),
            "precio_menor": Decimal("35000"),
            "actividades": [
                ("Senderismo al Páramo de Ocetá", "Alta"),
                ("Miradores y Panoramas Andinos", "Media"),
                ("Contemplación en la Laguna Negra", "Baja"),
            ],
        },
        {
            "nombre": "Laguna Negra y Leyendas Muiscas",
            "descripcion": "Sumérgete en la mística de la Laguna Negra, rodeada de historias ancestrales, paisajes de neblina y senderos ecológicos llenos de biodiversidad andina.",
            "dias_duracion": 1,
            "noches_duracion": 0,
            "punto_encuentro": "Plaza Central de Mongua",
            "hora_encuentro": time(7, 0),
            "imagen": "lagunanegra.webp",
            "categoria": "Arqueología Muisca",
            "precio_adulto": Decimal("32000"),
            "precio_menor": Decimal("20000"),
            "actividades": [
                ("Contemplación en la Laguna Negra", "Media"),
                ("Miradores y Panoramas Andinos", "Baja"),
            ],
        },
        {
            "nombre": "Piedras de Santo Domingo y Memoria Ancestral",
            "descripcion": "Un viaje en el tiempo hacia los vestigios arqueológicos y pictografías muiscas de Mongua, acompañado de relato histórico y visita al museo comunitario.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Casa de la Cultura de Mongua",
            "hora_encuentro": time(8, 0),
            "imagen": "pictografias.webp",
            "categoria": "Arqueología Muisca",
            "precio_adulto": Decimal("42000"),
            "precio_menor": Decimal("28000"),
            "actividades": [
                ("Ruta Arqueológica Piedras de Santo Domingo", "Media"),
                ("Visita al Museo y Talleres Artesanales", "Baja"),
            ],
        },
        {
            "nombre": "Mongua en Familia: Iglesia, Plaza y Sabor Local",
            "descripcion": "Plan diseñado para todas las edades que combina arquitectura colonial, recorrido por el centro histórico, talleres artesanales y almuerzo típico boyacense.",
            "dias_duracion": 1,
            "noches_duracion": 0,
            "punto_encuentro": "Atrio de la Iglesia de Mongua",
            "hora_encuentro": time(9, 0),
            "imagen": "iglesia.webp",
            "categoria": "Familia y Recreación",
            "precio_adulto": Decimal("18000"),
            "precio_menor": Decimal("10000"),
            "actividades": [
                ("Recorrido por la Iglesia y Plaza de Mongua", "Baja"),
                ("Degustación Gastronómica Boyacense", "Baja"),
                ("Visita al Museo y Talleres Artesanales", "Baja"),
            ],
        },
        {
            "nombre": "Sabores de Boyacá y Artesanías de Mongua",
            "descripcion": "Descubre los secretos de la cocina tradicional en horno de leña, amasijos locales y el arte del tejido en lana virgen directamente con las familias monguanas.",
            "dias_duracion": 1,
            "noches_duracion": 0,
            "punto_encuentro": "Plaza de Mercado de Mongua",
            "hora_encuentro": time(10, 0),
            "imagen": "artesanias.webp",
            "categoria": "Gastronomía y Cultura",
            "precio_adulto": Decimal("24000"),
            "precio_menor": Decimal("14000"),
            "actividades": [
                ("Degustación Gastronómica Boyacense", "Baja"),
                ("Visita al Museo y Talleres Artesanales", "Baja"),
            ],
        },
        {
            "nombre": "Expedición Morro de Uche al Amanecer",
            "descripcion": "Aventura de montaña para contemplar el amanecer sobre la cordillera oriental, ideal para amantes del trekking exigente y la fotografía de paisaje.",
            "dias_duracion": 1,
            "noches_duracion": 0,
            "punto_encuentro": "Mirador de la Cumbre, Mongua",
            "hora_encuentro": time(5, 30),
            "imagen": "miradorcumbre.webp",
            "categoria": "Senderismo y Aventura",
            "precio_adulto": Decimal("45000"),
            "precio_menor": Decimal("30000"),
            "actividades": [
                ("Ascenso al Morro de Uche", "Alta"),
                ("Miradores y Panoramas Andinos", "Media"),
            ],
        },
        {
            "nombre": "Laguna de la Estrella y Ecoaventura",
            "descripcion": "Ruta de ecoturismo responsable enfocada en la observación de flora endémica, fuentes hídricas de páramo y senderismo sostenible.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Centro de Interpretación Ambiental de Mongua",
            "hora_encuentro": time(7, 30),
            "imagen": "img_rio.webp",
            "categoria": "Senderismo y Aventura",
            "precio_adulto": Decimal("48000"),
            "precio_menor": Decimal("32000"),
            "actividades": [
                ("Avistamiento en Laguna de la Estrella", "Media"),
                ("Senderismo al Páramo de Ocetá", "Alta"),
            ],
        },
        {
            "nombre": "Mongua Patrimonial: Museo, Iglesia y Comunidad",
            "descripcion": "Inmersión cultural completa para conocer la historia viva del municipio, su patrimonio arquitectónico y el valor comunitario de su gente.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Parque Principal de Mongua",
            "hora_encuentro": time(9, 30),
            "imagen": "museo.webp",
            "categoria": "Patrimonio e Historia",
            "precio_adulto": Decimal("36000"),
            "precio_menor": Decimal("22000"),
            "actividades": [
                ("Recorrido por la Iglesia y Plaza de Mongua", "Baja"),
                ("Visita al Museo y Talleres Artesanales", "Baja"),
                ("Degustación Gastronómica Boyacense", "Baja"),
            ],
        },
    ]

    paquetes = []
    for data in paquetes_data:
        ruta_img = copiar_imagen_a_media(data['imagen'], 'destinos')
        paquete = Paquete.objects.create(
            nombre=data['nombre'],
            descripcion=data['descripcion'],
            dias_duracion=data['dias_duracion'],
            noches_duracion=data['noches_duracion'],
            punto_encuentro=data['punto_encuentro'],
            hora_encuentro=data['hora_encuentro'],
            categoria=categorias[data['categoria']],
            imagen=ruta_img,
            estado=True,
        )
        for act_nombre, dificultad in data['actividades']:
            PaqueteActividad.objects.create(
                paquete=paquete,
                actividad=actividades[act_nombre],
                dificultad_nivel=dificultad,
            )

        # Crear tarifa para cada temporada (con ligero ajuste en temporada alta)
        for idx_temp, temp in enumerate(temporadas):
            factor = Decimal('1.00') if idx_temp == 0 else (Decimal('1.10') if idx_temp == 1 else Decimal('1.15'))
            Tarifa.objects.create(
                paquete=paquete,
                temporada=temp,
                precio_adulto=(data['precio_adulto'] * factor).quantize(Decimal('1')),
                precio_menor=(data['precio_menor'] * factor).quantize(Decimal('1')),
                estado=True,
            )

        paquetes.append(paquete)

    # Promociones vigentes asociadas a paquetes reales
    promo_paramo = Promocion.objects.create(
        nombre="Aventura Páramo de Ocetá -15%",
        descripcion="Descuento especial para expediciones reservadas con anticipación en los ecosistemas de alta montaña de Mongua.",
        porcentaje_descuento=15,
        fecha_inicio=hoy - timedelta(days=10),
        fecha_fin=hoy + timedelta(days=60),
        codigo_promocion="MONAGUA15",
        codigo_cupon="PARAMO15",
        condiciones="Válido para reservas confirmadas en temporada vigente. No acumulable con otros cupones.",
        activa=True,
    )
    promo_familia = Promocion.objects.create(
        nombre="Escapada Familiar Boyacense -10%",
        descripcion="Beneficio exclusivo para grupos familiares que deseen conocer el patrimonio y la gastronomía de Mongua.",
        porcentaje_descuento=10,
        fecha_inicio=hoy - timedelta(days=5),
        fecha_fin=hoy + timedelta(days=90),
        codigo_promocion="FAMILIA10",
        codigo_cupon="MONGUAFAM",
        condiciones="Aplica en paquetes culturales y familiares con al menos 2 viajeros.",
        activa=True,
    )

    PaquetePromocion.objects.create(paquete=paquetes[0], promocion=promo_paramo)
    PaquetePromocion.objects.create(paquete=paquetes[3], promocion=promo_familia)

    # Asignar planes de guía al guía existente
    for paq in paquetes[:4]:
        PlanGuia.objects.create(
            usuario=guia_user,
            paquete=paq,
            idioma_servicio="Español / Inglés",
            fecha_inicio_plan=hoy,
            fecha_fin_plan=hoy + timedelta(days=180),
            estado=True,
        )

    return paquetes


# ==============================================================================
# 4. RESERVAS Y COMPROBANTES DE PAGO (CON USUARIOS EXISTENTES)
# ==============================================================================

def crear_reservas_y_pagos(clientes, paquetes, admin_user):
    """
    Crea reservas y pagos realistas distribuidos entre los 3 turistas existentes,
    cubriendo los distintos estados del flujo de negocio de Monagua.
    """
    print("4. Creando reservas y comprobantes de pago con usuarios existentes...")
    hoy = date.today()
    ahora = timezone.now()
    img_comprobante = copiar_imagen_a_media('Fondo.webp', 'comprobantes')

    escenarios = [
        # 1. Confirmada + Pago Aprobado (turista 1)
        {
            "usuario": clientes[0],
            "paquete": paquetes[0],
            "fecha_inicio": hoy + timedelta(days=12),
            "adultos": 2,
            "menores": 1,
            "estado_pago": "aprobado",
            "banco": "Bancolombia",
            "metodo": "Transferencia Bancaria",
            "ref": "CUS-20261101-8841",
            "nota_admin": "Transferencia verificada en cuenta Bancolombia Monagua.",
        },
        # 2. Confirmada + Pago Aprobado (turista 2)
        {
            "usuario": clientes[1],
            "paquete": paquetes[1],
            "fecha_inicio": hoy + timedelta(days=18),
            "adultos": 2,
            "menores": 0,
            "estado_pago": "aprobado",
            "banco": "Nequi",
            "metodo": "Billetera Digital",
            "ref": "NEQ-20261105-4412",
            "nota_admin": "Pago aprobado correctamente vía Nequi.",
        },
        # 3. Confirmada + Pago Aprobado (turista 3)
        {
            "usuario": clientes[2],
            "paquete": paquetes[3],
            "fecha_inicio": hoy + timedelta(days=22),
            "adultos": 2,
            "menores": 2,
            "estado_pago": "aprobado",
            "banco": "Daviplata",
            "metodo": "Billetera Digital",
            "ref": "DAV-20261108-7731",
            "nota_admin": "Comprobante claro y valor exacto confirmado.",
        },
        # 4. Pendiente + Comprobante en Revisión (turista 1) -> Ideal para probar aprobación Admin
        {
            "usuario": clientes[0],
            "paquete": paquetes[2],
            "fecha_inicio": hoy + timedelta(days=28),
            "adultos": 2,
            "menores": 0,
            "estado_pago": "pendiente",
            "banco": "Nequi",
            "metodo": "Billetera Digital",
            "ref": "NEQ-20261124-9015",
            "nota_admin": "",
        },
        # 5. Pendiente + Comprobante Rechazado (turista 2) -> Ideal para probar corrección / Pagos Rechazados
        {
            "usuario": clientes[1],
            "paquete": paquetes[4],
            "fecha_inicio": hoy + timedelta(days=34),
            "adultos": 3,
            "menores": 0,
            "estado_pago": "rechazado",
            "banco": "Davivienda",
            "metodo": "Transferencia Bancaria",
            "ref": "DAVI-20261120-1120",
            "nota_admin": "La captura adjunta se encuentra borrosa y no permite verificar el número de aprobación.",
        },
        # 6. Pendiente sin Pago enviado (turista 3) -> Ideal para probar Enviar Comprobante y Modificar Personas
        {
            "usuario": clientes[2],
            "paquete": paquetes[6],
            "fecha_inicio": hoy + timedelta(days=40),
            "adultos": 2,
            "menores": 1,
            "estado_pago": None,
            "banco": "",
            "metodo": "",
            "ref": "",
            "nota_admin": "",
        },
        # 7. Cancelada con Reembolso COMPLETADO (turista 1 - Política favorable 90% / 10% penalidad)
        {
            "usuario": clientes[0],
            "paquete": paquetes[5],
            "fecha_inicio": hoy + timedelta(days=45),
            "adultos": 2,
            "menores": 0,
            "estado_pago": "aprobado",
            "banco": "Bancolombia",
            "metodo": "Transferencia Bancaria",
            "ref": "BAN-20261102-3310",
            "nota_admin": "Pago aprobado antes de la solicitud de cancelación.",
            "cancelada": True,
            "motivo_cancelacion": "Cambio de fechas laborales en la semana del viaje.",
            "reembolso": {
                "porcentaje_penalidad": Decimal("0.10"),
                "estado": "completado",
                "banco_emisor": "Bancolombia Monagua",
                "banco_destino": "Nequi",
                "referencia": "REEM-20261118-9921",
                "notas_admin": "Reembolso del 90% transferido exitosamente según política favorable (>15 días).",
                "dias_atras": 2,
            },
        },
        # 8. Cancelada con Reembolso PENDIENTE de desembolso (turista 2 - Política parcial 50% / 50% penalidad)
        {
            "usuario": clientes[1],
            "paquete": paquetes[7],
            "fecha_inicio": hoy + timedelta(days=8),
            "adultos": 2,
            "menores": 1,
            "estado_pago": "aprobado",
            "banco": "Nequi",
            "metodo": "Billetera Digital",
            "ref": "NEQ-20261110-5582",
            "nota_admin": "Pago aprobado vía Nequi.",
            "cancelada": True,
            "motivo_cancelacion": "Imprevisto familiar de último momento impide asistir en la fecha reservada.",
            "reembolso": {
                "porcentaje_penalidad": Decimal("0.50"),
                "estado": "pendiente",
                "banco_emisor": "Bancolombia Monagua",
                "banco_destino": "Nequi",
                "referencia": "",
                "notas_admin": "Cancelación aprobada con política parcial (50%). Pendiente subir soporte de transferencia.",
                "dias_atras": None,
            },
        },
        # 9. Cancelada con Reembolso COMPLETADO (turista 3 - Política favorable 90% / 10% penalidad)
        {
            "usuario": clientes[2],
            "paquete": paquetes[2],
            "fecha_inicio": hoy + timedelta(days=30),
            "adultos": 1,
            "menores": 1,
            "estado_pago": "aprobado",
            "banco": "Daviplata",
            "metodo": "Billetera Digital",
            "ref": "DAV-20261112-6640",
            "nota_admin": "Pago confirmado vía Daviplata.",
            "cancelada": True,
            "motivo_cancelacion": "Reprogramación de vacaciones familiares.",
            "reembolso": {
                "porcentaje_penalidad": Decimal("0.10"),
                "estado": "completado",
                "banco_emisor": "Bancolombia Monagua",
                "banco_destino": "Daviplata",
                "referencia": "REEM-20261120-4105",
                "notas_admin": "Devolución realizada al número Daviplata registrado por el turista.",
                "dias_atras": 1,
            },
        },
    ]

    img_comprobante_reembolso = copiar_imagen_a_media('Fondo.webp', 'comprobantes_reembolsos')
    reservas_creadas = []
    pagos_creados = []
    reembolsos_creados = []

    for idx, esc in enumerate(escenarios):
        reserva = Reserva.objects.create(
            paquete=esc['paquete'],
            usuario=esc['usuario'],
            fecha_inicio=esc['fecha_inicio'],
            numero_adultos=esc['adultos'],
            numero_menores=esc['menores'],
            estado_reserva='pendiente',
            motivo_cancelacion=esc.get('motivo_cancelacion', ''),
        )

        pago = None
        if esc.get('estado_pago'):
            pago = Pago.objects.create(
                reserva=reserva,
                referencia=esc['ref'],
                banco_origen=esc['banco'],
                metodo_pago=esc['metodo'],
                monto=reserva.monto_total,
                imagen_comprobante=img_comprobante,
                descripcion=f"Pago realizado por {esc['usuario'].nombre_completo} para {esc['paquete'].nombre}.",
                estado_transaccion=esc['estado_pago'],
                nota_admin=esc['nota_admin'],
                fecha_pago=ahora - timedelta(days=len(escenarios) - idx + 2),
                fecha_revision=(ahora - timedelta(days=len(escenarios) - idx + 1)) if esc['estado_pago'] in ('aprobado', 'rechazado') else None,
            )
            pagos_creados.append(pago)
            reserva.refresh_from_db()

        if esc.get('cancelada'):
            reem_cfg = esc.get('reembolso')
            reserva.estado_reserva = 'cancelada'
            reserva.estado_cancelacion = 'aprobada'

            if reem_cfg and pago:
                pct_pen = reem_cfg['porcentaje_penalidad']
                penalidad = (reserva.monto_total * pct_pen).quantize(Decimal('1'))
                monto_devolver = (reserva.monto_total - penalidad).quantize(Decimal('1'))
                es_completado = reem_cfg['estado'] == 'completado'
                fecha_desembolso = (ahora - timedelta(days=reem_cfg['dias_atras'])) if es_completado else None

                reserva.penalidad = penalidad
                reserva.monto_reembolsable = monto_devolver
                reserva.estado_reembolso = 'pagado' if es_completado else 'pendiente'
                reserva.banco_reembolso = reem_cfg['banco_destino']
                reserva.referencia_reembolso = reem_cfg['referencia']
                reserva.fecha_reembolso = fecha_desembolso
                reserva.motivo_resolucion_cancelacion = reem_cfg['notas_admin']
                reserva.save()

                reembolso = Reembolso.objects.create(
                    reserva=reserva,
                    usuario=reserva.usuario,
                    pago_asociado=pago,
                    monto_total_reserva=reserva.monto_total,
                    penalidad_aplicada=penalidad,
                    monto_reembolsado=monto_devolver,
                    estado=reem_cfg['estado'],
                    motivo=reserva.motivo_cancelacion,
                    imagen_comprobante=img_comprobante_reembolso if es_completado else None,
                    banco_emisor=reem_cfg['banco_emisor'],
                    banco_destino=reem_cfg['banco_destino'],
                    cuenta_o_telefono=reserva.usuario.telefono or '',
                    referencia_transferencia=reem_cfg['referencia'],
                    notas_admin=reem_cfg['notas_admin'],
                    gestionado_por=admin_user,
                    fecha_reembolso=fecha_desembolso,
                )
                reembolsos_creados.append(reembolso)
            else:
                reserva.motivo_resolucion_cancelacion = 'Cancelación aprobada sin penalidad (solicitud realizada con anticipación).'
                reserva.save()

        reservas_creadas.append(reserva)

    return reservas_creadas, pagos_creados, reembolsos_creados


# ==============================================================================
# 5. BLOGS REFERENTES A MONAGUA Y MONGUA
# ==============================================================================

def crear_blogs_monagua(admin_user):
    """Crea artículos de blog originales sobre Monagua y el turismo sostenible en Mongua, Boyacá."""
    print("5. Creando artículos de blog referentes a Monagua...")

    articulos = [
        {
            "titulo": "Descubre Monagua: Turismo Sostenible en el Corazón de Mongua, Boyacá",
            "imagen": "paramo.webp",
            "info": "Identidad Monagua · Ecoturismo Comunitario",
            "contenido": (
                "Monagua nace con el propósito de conectar a viajeros responsables con la riqueza natural, "
                "cultural e histórica de Mongua, un tesoro escondido en la provincia de Sugamuxi en Boyacá. "
                "A más de 2.975 metros sobre el nivel del mar, nuestro territorio ofrece paisajes de páramo, "
                "lagunas sagradas, arquitectura tradicional y la calidez de una comunidad orgullosa de sus raíces.\n\n"
                "A través de nuestra plataforma digital, los turistas pueden explorar paquetes certificados, "
                "reservar sus fechas con total transparencia, contar con guías locales expertos y contribuir "
                "directamente al desarrollo económico sostenible de las familias monguanas."
            ),
        },
        {
            "titulo": "Guía Completa para Explorar el Páramo de Ocetá con Monagua",
            "imagen": "paramo_oseta.webp",
            "info": "Alta Montaña · Recomendaciones de Viaje",
            "contenido": (
                "Considerado uno de los ecosistemas de páramo mejor conservados de Colombia, el Páramo de Ocetá "
                "es una parada obligatoria para quienes buscan senderismo auténtico y contacto puro con la naturaleza. "
                "Durante los recorridos organizados por Monagua, podrás admirar frailejones centenarios, "
                "cañones rocosos, nacimientos de agua cristalina y formaciones geológicas únicas.\n\n"
                "Recomendaciones clave de nuestros guías: vestir en tres capas (térmica, abrigo e impermeable), "
                "usar botas con buen agarre, llevar protector solar e hidratación suficiente, y nunca salir de los "
                "senderos autorizados para proteger la flora endémica."
            ),
        },
        {
            "titulo": "Laguna Negra de Mongua: Leyendas Muiscas y Paisajes de Neblina",
            "imagen": "lagunanegra.webp",
            "info": "Naturaleza y Mística · Patrimonio Natural",
            "contenido": (
                "Rodeada de montañas silenciosas y neblina andina, la Laguna Negra es uno de los escenarios más "
                "emblemáticos de Mongua. Para los antiguos muiscas, los cuerpos de agua de altura representaban "
                "lugares sagrados de conexión espiritual y agradecimiento a la tierra.\n\n"
                "En las caminatas guiadas de Monagua hacia la Laguna Negra, combinamos la interpretación ecológica "
                "con los relatos transmitidos por generaciones de habitantes locales, logrando una experiencia "
                "profunda de contemplación, fotografía y respeto ambiental."
            ),
        },
        {
            "titulo": "Piedras de Santo Domingo: Arte Rupestre y Memoria Muisca en Mongua",
            "imagen": "pictografias.webp",
            "info": "Arqueología · Historia Ancestral",
            "contenido": (
                "Las Piedras de Santo Domingo conservan valiosas pictografías y trazos indígenas que narran la "
                "presencia milenaria del pueblo muisca en el territorio boyacense. Cada símbolo grabado en roca "
                "refleja su cosmovisión, su relación con los astros y su vínculo con el entorno montañoso.\n\n"
                "Con los tours patrimoniales de Monagua, los visitantes descubren el significado histórico de estos "
                "vestigios y comprenden la importancia de proteger el patrimonio arqueológico de Boyacá."
            ),
        },
        {
            "titulo": "Gastronomía Boyacense y Artesanías Locales: Experiencias Auténticas con Monagua",
            "imagen": "artesanias.webp",
            "info": "Cultura Viva · Sabores y Oficios",
            "contenido": (
                "Viajar a Mongua con Monagua también es un deleite para el paladar y los sentidos. Tras una jornada "
                "de caminata por el páramo, nada se compara con compartir un cocido boyacense tradicional, "
                "envueltos de mazorca, arepas asadas en laja, queso campesino y agua de panela caliente.\n\n"
                "Además, promovemos encuentros directos con artesanos tejedores de ruanas y cobijas en lana virgen, "
                "permitiendo que cada visitante conozca el oficio tradicional y apoye el comercio justo local."
            ),
        },
        {
            "titulo": "Patrimonio Arquitectónico de Mongua: Iglesia, Plaza y Vida Comunitaria",
            "imagen": "iglesia.webp",
            "info": "Turismo Cultural · Recorrido Urbano",
            "contenido": (
                "El casco urbano de Mongua conserva el encanto tranquilo de los pueblos tradicionales de Boyacá. "
                "Su parque principal, la fachada histórica de su iglesia y las calles empedradas invitan a caminar "
                "sin afán, conversar con su gente y disfrutar de la calma andina.\n\n"
                "Monagua integra este recorrido cultural en sus planes familiares para ofrecer una experiencia "
                "completa que une aventura, historia y descanso en un solo destino."
            ),
        },
    ]

    blogs_creados = []
    for art in articulos:
        ruta_img = copiar_imagen_a_media(art['imagen'], 'blog')
        blog = Blog.objects.create(
            usuario=admin_user,
            titulo=art['titulo'],
            contenido=art['contenido'],
            informacion_adicional=art['info'],
            imagen_destacada=ruta_img,
            estado=True,
        )
        blogs_creados.append(blog)

    return blogs_creados


# ==============================================================================
# 6. CALIFICACIONES / RESEÑAS (VINCULADAS A RESERVAS DE USUARIOS EXISTENTES)
# ==============================================================================

def crear_calificaciones(reservas):
    """Crea reseñas reales vinculadas a las reservas de los usuarios existentes."""
    print("6. Creando calificaciones y reseñas de usuarios existentes...")

    reservas_confirmadas = [r for r in reservas if r.estado_reserva == 'confirmada']
    resenas_data = [
        (
            "Una experiencia inolvidable en el Páramo de Ocetá",
            5,
            "El guía Camilo fue extraordinario, nos explicó cada detalle de los frailejones y cuidó mucho al grupo. La organización de Monagua desde la reserva hasta la factura fue impecable.",
            "¡Muchas gracias Juan Carlos! Nos alegra enormemente saber que disfrutaste el Páramo de Ocetá junto a tu familia. ¡Mongua siempre será tu casa!",
        ),
        (
            "La Laguna Negra es mágica y el servicio excelente",
            5,
            "Paisajes espectaculares y muy buena puntualidad en el punto de encuentro. El proceso de envío del comprobante y confirmación por correo fue muy rápido.",
            "¡Gracias Laura Sofía por confiar en Monagua! Esperamos verte pronto en una nueva expedición.",
        ),
        (
            "Plan familiar perfecto y comida deliciosa",
            4,
            "Fuimos con niños y todos la pasaron increíble en la plaza, el museo y la degustación boyacense. Muy recomendado para desconectarse un fin de semana.",
            "¡Gracias Andrés Felipe por tu calificación! Seguimos trabajando para ofrecer los mejores planes familiares en Mongua.",
        ),
    ]

    calificaciones_creadas = []
    for reserva, (titulo, estrellas, comentario, respuesta_admin) in zip(reservas_confirmadas, resenas_data):
        cal = Calificacion.objects.create(
            reserva=reserva,
            tipo='experiencia',
            titulo=titulo,
            puntaje_estrellas=estrellas,
            comentario=comentario,
            visible=True,
            admin_respuesta=respuesta_admin,
        )
        calificaciones_creadas.append(cal)

    return calificaciones_creadas


# ==============================================================================
# 7. PQRS Y SEGUIMIENTOS (CON USUARIOS EXISTENTES)
# ==============================================================================

def crear_pqrs_y_seguimientos(clientes, admin_user):
    """Crea solicitudes PQRS reales vinculadas a los usuarios turistas existentes."""
    print("7. Creando solicitudes PQRS y seguimientos con usuarios existentes...")

    pqrs_data = [
        {
            "usuario": clientes[0],
            "tipo": "peticion",
            "asunto": "Consulta sobre equipo térmico para el Páramo de Ocetá",
            "descripcion": "Hola equipo Monagua, tengo una reserva confirmada para el Páramo de Ocetá con un menor de edad. ¿Recomiendan llevar bastones de trekking o los guías facilitan el apoyo en la ruta?",
            "estado": "cerrado",
            "respuesta": "Hola Juan Carlos. Te confirmamos que la ruta familiar cuenta con acompañamiento constante de nuestro guía certificado. Recomendamos botas impermeables, chaqueta térmica y guantes; si deseas bastones, podemos prestarte un par en el punto de encuentro sin costo adicional.",
        },
        {
            "usuario": clientes[1],
            "tipo": "sugerencia",
            "asunto": "Agregar opción de transporte desde Sogamoso o Tunja",
            "descripcion": "Me encantó el tour a la Laguna Negra. Como sugerencia, sería genial ofrecer un servicio adicional de traslado grupal desde Tunja o Sogamoso hasta el parque principal de Mongua.",
            "estado": "en_proceso",
            "respuesta": "Muchas gracias Laura Sofía por tu valiosa sugerencia. Actualmente estamos estructurando alianzas con transportadores locales certificados para habilitar esta opción en los próximos meses.",
        },
        {
            "usuario": clientes[2],
            "tipo": "reclamo",
            "asunto": "Demora en actualización del estado de un comprobante",
            "descripcion": "Realicé una consulta previa sobre un pago y me gustaría confirmar el horario habitual de validación de comprobantes los fines de semana.",
            "estado": "cerrado",
            "respuesta": "Hola Andrés Felipe, lamentamos la espera. Nuestro equipo valida comprobantes todos los días entre las 7:00 a.m. y las 8:00 p.m., y te enviamos confirmación automática al correo apenas se aprueba el pago.",
        },
        {
            "usuario": clientes[0],
            "tipo": "peticion",
            "asunto": "Disponibilidad para grupo empresarial en temporada vacacional",
            "descripcion": "Quisiera cotizar una salida ecológica para 8 personas en el paquete de Piedras de Santo Domingo y saber si aplica descuento grupal.",
            "estado": "abierto",
            "respuesta": None,
        },
    ]

    pqrs_creadas = []
    for item in pqrs_data:
        u = item['usuario']
        pqr = PQRS.objects.create(
            usuario=u,
            nombre_completo=u.nombre_completo,
            correo=u.email,
            tipo=item['tipo'],
            asunto=item['asunto'],
            descripcion=item['descripcion'],
            estado=item['estado'],
        )
        if item['respuesta']:
            Seguimiento.objects.create(
                pqrs=pqr,
                usuario=admin_user,
                respuesta=item['respuesta'],
            )
        pqrs_creadas.append(pqr)

    return pqrs_creadas


# ==============================================================================
# 8. BITÁCORA DE AUDITORÍA Y NOTIFICACIONES
# ==============================================================================

def crear_bitacoras_y_notificaciones(clientes, admin_user, reservas, pagos, reembolsos, pqrs_list):
    """Registra eventos reales en Bitacora y Notificacion vinculados a los usuarios existentes."""
    print("8. Creando registros de bitácora y notificaciones del sistema...")

    for r in reservas:
        Bitacora.objects.create(
            usuario=r.usuario,
            reserva=r,
            accion='INSERT',
            modulo='Reservas',
            registro_id=r.id,
            ip_origen='192.168.1.15',
            descripcion=(
                f"El usuario @{r.usuario.username} registró la reserva #{r.id} "
                f"para el paquete '{r.paquete.nombre}' ({r.numero_adultos} adultos, {r.numero_menores} menores) "
                f"por COP ${r.monto_total:,.0f}."
            ),
        )

    for p in pagos:
        Bitacora.objects.create(
            usuario=p.reserva.usuario,
            reserva=p.reserva,
            pago=p,
            accion='INSERT',
            modulo='Comprobantes de Pago',
            registro_id=p.id,
            ip_origen='192.168.1.18',
            descripcion=(
                f"El usuario @{p.reserva.usuario.username} envió el comprobante #{p.id} "
                f"por COP ${p.monto:,.0f} vía {p.banco_origen} (Ref: {p.referencia})."
            ),
        )
        if p.estado_transaccion in ('aprobado', 'rechazado'):
            Bitacora.objects.create(
                usuario=admin_user,
                reserva=p.reserva,
                pago=p,
                accion='UPDATE',
                modulo='Comprobantes de Pago',
                registro_id=p.id,
                ip_origen='127.0.0.1',
                descripcion=(
                    f"Comprobante #{p.id}: Estado actualizado a '{p.estado_transaccion.capitalize()}'. "
                    f"Nota: {p.nota_admin or 'Sin observaciones'}."
                ),
            )

    for pqr in pqrs_list:
        Bitacora.objects.create(
            usuario=pqr.usuario,
            pqrs=pqr,
            accion='INSERT',
            modulo='PQRS',
            registro_id=pqr.id,
            ip_origen='192.168.1.22',
            descripcion=f"El usuario @{pqr.usuario.username} radicó {pqr.radicado}: '{pqr.asunto}'.",
        )

    for reem in reembolsos:
        Bitacora.objects.create(
            usuario=admin_user,
            reserva=reem.reserva,
            pago=reem.pago_asociado,
            accion='UPDATE' if reem.estado == 'completado' else 'INSERT',
            modulo='Reembolsos',
            registro_id=reem.id,
            ip_origen='127.0.0.1',
            descripcion=(
                f"Reembolso #{reem.id} para reserva #{reem.reserva_id} (@{reem.usuario.username}) "
                f"en estado '{reem.get_estado_display()}' por COP ${reem.monto_reembolsado:,.0f} "
                f"(penalidad COP ${reem.penalidad_aplicada:,.0f})."
            ),
        )
        if reem.estado == 'completado':
            Notificacion.objects.create(
                usuario=reem.usuario,
                reserva=reem.reserva,
                mensaje=(
                    f"¡Tu reembolso de COP ${reem.monto_reembolsado:,.0f} por la reserva #{reem.reserva_id} "
                    f"ha sido transferido exitosamente vía {reem.banco_destino} (Ref: {reem.referencia_transferencia})!"
                ),
                tipo="Reembolso",
                prioridad="alta",
                leido=False,
            )
        elif reem.estado == 'pendiente':
            Notificacion.objects.create(
                usuario=admin_user,
                reserva=reem.reserva,
                mensaje=(
                    f"Reembolso pendiente de desembolso (#{reem.id}) para @{reem.usuario.username} "
                    f"por COP ${reem.monto_reembolsado:,.0f} (Reserva #{reem.reserva_id})."
                ),
                tipo="Reembolso Pendiente",
                prioridad="alta",
                leido=False,
            )

    # Notificaciones relevantes para turistas y administrador
    Notificacion.objects.create(
        usuario=clientes[0],
        reserva=reservas[0],
        mensaje=f"¡Tu pago para '{reservas[0].paquete.nombre}' (Reserva #{reservas[0].id}) fue aprobado! Ya puedes descargar tu factura.",
        tipo="Comprobante de Pago",
        prioridad="alta",
        leido=False,
    )
    Notificacion.objects.create(
        usuario=clientes[1],
        reserva=reservas[4],
        mensaje=f"Tu comprobante para la reserva #{reservas[4].id} fue rechazado. Motivo: La captura se encuentra borrosa.",
        tipo="Comprobante de Pago",
        prioridad="alta",
        leido=False,
    )
    Notificacion.objects.create(
        usuario=admin_user,
        reserva=reservas[3],
        mensaje=f"Nuevo comprobante pendiente de revisión enviado por @{clientes[0].username} para la reserva #{reservas[3].id}.",
        tipo="Nuevo Comprobante de Pago",
        prioridad="alta",
        leido=False,
    )


# ==============================================================================
# EJECUCIÓN PRINCIPAL
# ==============================================================================

@transaction.atomic
def poblar_base_datos():
    print("=" * 68)
    print("  MONAGUA - POBLADO ESTRUCTURADO DE BASE DE DATOS (DATOS REALES)")
    print("=" * 68)

    limpiar_base_datos()
    usuarios_map = crear_usuarios()
    paquetes = crear_catalogo_turistico(usuarios_map['guia'])
    reservas, pagos, reembolsos = crear_reservas_y_pagos(usuarios_map['clientes'], paquetes, usuarios_map['admin'])
    crear_blogs_monagua(usuarios_map['admin'])
    crear_calificaciones(reservas)
    pqrs_list = crear_pqrs_y_seguimientos(usuarios_map['clientes'], usuarios_map['admin'])
    crear_bitacoras_y_notificaciones(usuarios_map['clientes'], usuarios_map['admin'], reservas, pagos, reembolsos, pqrs_list)

    print("\n" + "=" * 68)
    print("  [OK] BASE DE DATOS POBLADA EXITOSAMENTE")
    print("=" * 68)
    print(f"  - Usuarios:        {Usuario.objects.count()} (1 Admin, 1 Guía, 3 Turistas)")
    print(f"  - Categorías:      {Categoria.objects.count()}")
    print(f"  - Actividades:     {Actividades.objects.count()}")
    print(f"  - Temporadas:      {Temporada.objects.count()}")
    print(f"  - Paquetes:        {Paquete.objects.count()}")
    print(f"  - Tarifas:         {Tarifa.objects.count()}")
    print(f"  - Promociones:     {Promocion.objects.count()}")
    print(f"  - Planes Guía:     {PlanGuia.objects.count()}")
    print(f"  - Reservas:        {Reserva.objects.count()}")
    print(f"  - Pagos:           {Pago.objects.count()}")
    print(f"  - Reembolsos:      {Reembolso.objects.count()}")
    print(f"  - Blogs Monagua:   {Blog.objects.count()}")
    print(f"  - Calificaciones:  {Calificacion.objects.count()}")
    print(f"  - PQRS:            {PQRS.objects.count()} (Seguimientos: {Seguimiento.objects.count()})")
    print(f"  - Bitácora:        {Bitacora.objects.count()}")
    print(f"  - Notificaciones:  {Notificacion.objects.count()}")
    print("-" * 68)
    print("  CREDENCIALES DE ACCESO:")
    print("  * Admin:     admin        / admin1234")
    print("  * Guía:      guia         / guia1234")
    print("  * Turista 1: turista      / turista1234")
    print("  * Turista 2: laura_gomez  / turista1234")
    print("  * Turista 3: andres_rojas / turista1234")
    print("=" * 68)


if __name__ == '__main__':
    poblar_base_datos()
