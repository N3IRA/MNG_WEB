import os
import sys
import random
import shutil
from datetime import date, timedelta, datetime
from decimal import Decimal
from pathlib import Path

import django
from django.conf import settings
from django.db import transaction
from django.utils import timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from App.models import (
    Actividades,
    Aseguradora,
    Bitacora,
    Blog,
    Calificacion,
    Categoria,
    Notificacion,
    Pago,
    Paquete,
    PaqueteActividad,
    PaquetePromocion,
    PlanGuia,
    PolizaViaje,
    PQRS,
    Promocion,
    Reserva,
    Seguimiento,
    Tarifa,
    Temporada,
    Usuario,
)

RECURSOS_VISUALES = {
    'img_Iglesia.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'paramo.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'lagunanegra.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'img_rutas.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'paramo_oseta.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'miradorcumbre.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'artesanias.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'estatua_piedra.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'img_rio.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
    'iglesia.webp': {
        'autor': 'Equipo Monagua',
        'fuente': 'Repositorio local del proyecto',
        'fecha_publicacion': '2025',
        'licencia': 'Uso interno del proyecto académico; no se usó material externo sin revisión.'
    },
}


def generar_documento_unico(prefijo):
    while True:
        doc = f"{prefijo}{random.randint(100000, 999999)}"
        if not Usuario.objects.filter(numero_documento=doc).exists():
            return doc


def generar_email_unico(username):
    email = f"{username}@ejemplo.com"
    if not Usuario.objects.filter(email__iexact=email).exists():
        return email
    while True:
        email = f"{username}_{random.randint(10, 99)}@ejemplo.com"
        if not Usuario.objects.filter(email__iexact=email).exists():
            return email


@transaction.atomic
def poblar_base_datos():
    print("Iniciando el poblado de la base de datos con datos reales de Mongua...")
    print("1. Limpieza de registros existentes...")

    Bitacora.objects.all().delete()
    Calificacion.objects.all().delete()
    Pago.objects.all().delete()
    Notificacion.objects.all().delete()
    PlanGuia.objects.all().delete()
    Aseguradora.objects.all().delete()
    PolizaViaje.objects.all().delete()
    PaquetePromocion.objects.all().delete()
    Promocion.objects.all().delete()
    Seguimiento.objects.all().delete()
    PQRS.objects.all().delete()
    Blog.objects.all().delete()
    Reserva.objects.all().delete()
    Tarifa.objects.all().delete()
    Temporada.objects.all().delete()
    PaqueteActividad.objects.all().delete()
    Paquete.objects.all().delete()
    Actividades.objects.all().delete()
    Categoria.objects.all().delete()
    Usuario.objects.all().delete()

    anio = timezone.localdate().year

    categorias_semilla = [
        ("Páramo y naturaleza", "Recorridos por los ecosistemas de altura, lagunas, páramos y miradores del municipio de Mongua."),
        ("Senderismo y aventura", "Rutas de caminata, observación de paisaje y recorridos de mayor exigencia en la geografía de Mongua."),
        ("Patrimonio e historia", "Sitios con valor cultural, memoria indígena muisca, plaza central, iglesia y relatos del municipio."),
        ("Arqueología y cultura muisca", "Espacios vinculados con las huellas del poblamiento muisca y la escultura rupestre del territorio."),
        ("Gastronomía y cultura", "Sabores tradicionales, productos del campo y experiencias gastronómicas ligadas a la identidad boyacense."),
        ("Familia y recreación", "Planes para grupos, familias y visitantes que buscan un turismo tranquilo y cercano."),
    ]

    actividades_semilla = [
        ("Senderismo al Páramo de Ocetá", "Ruta guiada por paisajes de alta montaña y ecosistemas andinos del municipio.", "Botas de senderismo, mochila, agua, ropa térmica", "Usa varias capas de ropa y lleva protección contra el frío del páramo.", True),
        ("Laguna Negra y contemplación natural", "Recorrido para descubrir el entorno de la Laguna Negra y su valor paisajístico y cultural.", "Ropa cómoda, cámara, agua", "Mantén silencio para disfrutar mejor el paisaje y la calma del lugar.", True),
        ("Visita a la Iglesia de Mongua", "Paseo cultural por la arquitectura y la historia del municipio con sentido de conservación patrimonial.", "Ropa cómoda, cámara fotográfica", "Respeta los horarios de la comunidad y el espacio sagrado.", True),
        ("Ruta de miradores y panoramas", "Caminatas hacia puntos con amplia vista del municipio, los valles y la cordillera.", "Gafas de sol, chaqueta ligera", "La mejor vista suele presentarse al amanecer o al atardecer.", True),
        ("Piedras de Santo Domingo y arte rupestre", "Ruta de interpretación cultural para conocer vestigios arqueológicos y piezas rupestres significativas.", "Calzado adecuado, cuaderno de campo", "Consulta con la guía para entender el contexto histórico del sitio.", True),
        ("Degustación boyacense", "Experiencia para probar productos típicos, sabores locales y preparaciones de la región.", "Ganas de probar sabores locales", "Es ideal combinar la gastronomía con el recorrido por la plaza y la comunidad.", True),
        ("Caminata al Morro de Uche", "Actividad de paisaje y aventura con miradas amplias hacia la geografía del municipio.", "Botas, agua, casco opcional", "Se recomienda hacer la ruta con guía por la variabilidad del terreno.", False),
        ("Laguna de la Estrella y ecosistemas", "Recorrido de observación de flora y fauna en áreas de gran valor ecológico.", "Binoculares, ropa cómoda, bloqueador", "Lleva protección solar y una botella de agua.", True),
        ("Fotografía de paisaje y memoria local", "Ruta enfocada en vistas, texturas, luz y la relación entre paisaje y patrimonio.", "Cámara, trípode opcional, lente amplio", "La mejor luz suele estar al amanecer o en la hora dorada.", True),
        ("Museo y patrimonio del municipio", "Encuentro con la historia de Mongua, la cultura muisca y la memoria local.", "Ropa cómoda, interés por la historia", "Aprovecha la visita para conversar con la comunidad y aprender su contexto.", True),
    ]

    temporadas_semilla = [
        ("Temporada seca y clara de enero a marzo", "Meses con condiciones estables para senderismo, excursiones y recorridos de paisaje en el municipio.", date(anio, 1, 1), date(anio, 3, 31)),
        ("Semana Santa y feriados de abril", "Periodos con alta demanda por viajes familiares y actividades culturales de corto recorrido.", date(anio, 3, 20), date(anio, 4, 30)),
        ("Temporada verde de mayo a julio", "Ritmo de lluvias y paisajes exuberantes, muy apropiado para fotografía y ecoturismo.", date(anio, 5, 1), date(anio, 7, 31)),
        ("Periodo de celebración y viajes del segundo semestre", "Meses con alta afluencia por feriados, descanso y visitas culturales en Boyacá.", date(anio, 9, 1), date(anio, 11, 30)),
        ("Navidad y cierre de año", "Recomendado para turismo familiar, visitas cortas y recorridos patrimoniales.", date(anio, 12, 1), date(anio, 12, 31)),
    ]

    paquetes_semilla = [
        {
            "nombre": "Páramo de Ocetá y miradores de Mongua",
            "descripcion": "Recorrido por paisajes de alta montaña, miradores y rutas de senderismo con guía local, ideal para quienes buscan naturaleza, altura y fotografía.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Parque principal de Mongua",
            "hora_encuentro": "06:30:00",
            "imagen": "paramo.webp",
            "categoria": "Páramo y naturaleza",
            "actividades": ["Senderismo al Páramo de Ocetá", "Ruta de miradores y panoramas", "Laguna Negra y contemplación natural"],
        },
        {
            "nombre": "Laguna Negra y leyendas del municipio",
            "descripcion": "Experiencia de paisaje y cultura en torno a la Laguna Negra, con rutas de contemplación, historia local y espacios de gran valor ecológico.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Terminal de transporte de Mongua",
            "hora_encuentro": "07:00:00",
            "imagen": "lagunanegra.webp",
            "categoria": "Arqueología y cultura muisca",
            "actividades": ["Laguna Negra y contemplación natural", "Fotografía de paisaje y memoria local", "Ruta de miradores y panoramas"],
        },
        {
            "nombre": "Piedras de Santo Domingo y memoria muisca",
            "descripcion": "Ruta cultural y arqueológica para conocer los vestigios indígenas del territorio y su relación con la historia y la identidad de Mongua.",
            "dias_duracion": 3,
            "noches_duracion": 2,
            "punto_encuentro": "Casa de la cultura de Mongua",
            "hora_encuentro": "08:00:00",
            "imagen": "img_rutas.webp",
            "categoria": "Patrimonio e historia",
            "actividades": ["Piedras de Santo Domingo y arte rupestre", "Museo y patrimonio del municipio", "Fotografía de paisaje y memoria local"],
        },
        {
            "nombre": "Mongua en familia: plaza, iglesia y sabor local",
            "descripcion": "Plan pensado para grupos familiares con recorridos tranquilos, patrimonio y degustaciones del municipio.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Plaza principal de Mongua",
            "hora_encuentro": "09:00:00",
            "imagen": "iglesia.webp",
            "categoria": "Familia y recreación",
            "actividades": ["Visita a la Iglesia de Mongua", "Degustación boyacense", "Museo y patrimonio del municipio"],
        },
        {
            "nombre": "Sabores de Boyacá en Mongua",
            "descripcion": "Recorrido gastronómico para reconocer preparación artesanal, productos locales y experiencias cercanas con la comunidad del municipio.",
            "dias_duracion": 1,
            "noches_duracion": 1,
            "punto_encuentro": "Mercado del pueblo",
            "hora_encuentro": "11:00:00",
            "imagen": "artesanias.webp",
            "categoria": "Gastronomía y cultura",
            "actividades": ["Degustación boyacense", "Museo y patrimonio del municipio"],
        },
        {
            "nombre": "Morro de Uche y amanecer boyacense",
            "descripcion": "Experiencia para disfrutar del amanecer, la geografía de altura y la belleza del paisaje andino desde un punto panorámico del municipio.",
            "dias_duracion": 1,
            "noches_duracion": 0,
            "punto_encuentro": "Mirador del pueblo",
            "hora_encuentro": "05:30:00",
            "imagen": "miradorcumbre.webp",
            "categoria": "Páramo y naturaleza",
            "actividades": ["Caminata al Morro de Uche", "Ruta de miradores y panoramas", "Fotografía de paisaje y memoria local"],
        },
        {
            "nombre": "Laguna de la Estrella y rutas de ecoaventura",
            "descripcion": "Ruta de observación ambiental, paisajes húmedos y experiencia cercana con la fauna y flora del entorno de Mongua.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Centro de interpretación local",
            "hora_encuentro": "08:30:00",
            "imagen": "img_rio.webp",
            "categoria": "Senderismo y aventura",
            "actividades": ["Laguna de la Estrella y ecosistemas", "Senderismo al Páramo de Ocetá", "Fotografía de paisaje y memoria local"],
        },
        {
            "nombre": "Mongua patrimonial: iglesia, plaza y comunidad",
            "descripcion": "Ruta de historia y vida local en torno a la arquitectura, la plaza y la identidad del municipio.",
            "dias_duracion": 2,
            "noches_duracion": 1,
            "punto_encuentro": "Parque principal",
            "hora_encuentro": "10:00:00",
            "imagen": "img_Iglesia.webp",
            "categoria": "Patrimonio e historia",
            "actividades": ["Visita a la Iglesia de Mongua", "Museo y patrimonio del municipio", "Degustación boyacense"],
        },
    ]

    print("2. Creando usuarios base...")
    admin_user = Usuario.objects.create_superuser(
        username='admin',
        password='admin1234',
        email='admin@monagua.local',
        first_name='Admin',
        last_name='Monagua',
        rol=Usuario.Roles.ADMIN,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='12345678',
        telefono='+573000000000',
        residencia='Mongua, Boyacá',
        pais='COL'
    )

    turista_user = Usuario.objects.create_user(
        username='turista',
        password='turista1234',
        email='turista@monagua.local',
        first_name='Juan',
        last_name='Turista',
        rol=Usuario.Roles.CLIENTE,
        tipo_documento=Usuario.TipoDocumento.CC,
        numero_documento='87654321',
        telefono='+573100000000',
        residencia='Mongua, Boyacá',
        pais='COL'
    )

    clientes_creados = [turista_user]
    for idx in range(8):
        username = f"cliente_{idx + 1}"
        usuario = Usuario.objects.create_user(
            username=username,
            password='password123',
            first_name=f'Cliente{idx + 1}',
            last_name='Mongua',
            email=generar_email_unico(username),
            rol=Usuario.Roles.CLIENTE,
            tipo_documento=Usuario.TipoDocumento.CC,
            numero_documento=generar_documento_unico(f"100{idx + 1}"),
            telefono=f'+573{random.randint(10000000, 99999999)}',
            residencia='Mongua, Boyacá',
            pais='COL'
        )
        clientes_creados.append(usuario)

    guias_creados = []
    guia_nombres = [
        ('Camilo', 'Mendoza', 'Guía de senderismo y naturaleza'),
        ('Laura', 'Pérez', 'Guía de patrimonio y cultura'),
        ('Nelson', 'Gutiérrez', 'Especialista en rutas de montaña'),
        ('Andrea', 'Sánchez', 'Guía de avistamiento y ecoturismo'),
        ('Diego', 'Gómez', 'Especialista en aventura y actividades de río'),
    ]
    for first, last, bio in guia_nombres:
        usuario = Usuario.objects.create_user(
            username=f"guia_{first.lower()}",
            password='password123',
            first_name=first,
            last_name=last,
            email=generar_email_unico(f"guia_{first.lower()}"),
            rol=Usuario.Roles.GUIA,
            tipo_documento=Usuario.TipoDocumento.CC,
            numero_documento=generar_documento_unico(f"200{random.randint(100, 999)}"),
            telefono=f'+573{random.randint(10000000, 99999999)}',
            residencia='Mongua, Boyacá',
            pais='COL',
            numero_tarjeta_profesional=f'LIC-MG-{random.randint(1000, 9999)}',
            experiencia_anos=random.randint(3, 12),
            descripcion_experiencia=bio,
            entidad_salud='EPS Monagua',
            experiencia_fecha=date.today() - timedelta(days=random.randint(365, 3000))
        )
        guias_creados.append(usuario)

    print("3. Creación de categorías y actividades...")
    categorias_creadas = []
    for nombre, descripcion in categorias_semilla:
        categoria = Categoria.objects.create(nombre=nombre, descripcion=descripcion, estado=True)
        categorias_creadas.append(categoria)

    actividades_creadas = []
    for nombre, descripcion, equipo, recomendaciones, apto_menores in actividades_semilla:
        actividad = Actividades.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            equipo_requerimiento=equipo,
            recomendaciones=recomendaciones,
            estado=True,
            apto_menores=apto_menores,
        )
        actividades_creadas.append(actividad)

    print("4. Creación de temporadas y tarifas...")
    temporadas_creadas = []
    for nombre, descripcion, fecha_ini, fecha_fin in temporadas_semilla:
        temporada = Temporada.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            fecha_inicio=fecha_ini,
            fecha_fin=fecha_fin,
            estado=True,
        )
        temporadas_creadas.append(temporada)

    print("5. Creación de paquetes turísticos...")
    destinos_dir = Path(settings.MEDIA_ROOT) / 'destinos'
    destinos_dir.mkdir(parents=True, exist_ok=True)

    paquetes_creados = []
    for data in paquetes_semilla:
        imagen_origen = Path(settings.BASE_DIR) / 'static' / 'img' / data['imagen']
        imagen_destino = destinos_dir / data['imagen']
        if imagen_origen.exists():
            shutil.copy2(imagen_origen, imagen_destino)

        paquete = Paquete.objects.create(
            nombre=data['nombre'],
            descripcion=data['descripcion'],
            dias_duracion=data['dias_duracion'],
            noches_duracion=data['noches_duracion'],
            punto_encuentro=data['punto_encuentro'],
            hora_encuentro=data['hora_encuentro'],
            categoria=Categoria.objects.get(nombre=data['categoria']),
            imagen=f'destinos/{data["imagen"]}',
            estado=True,
        )

        for nombre_actividad in data['actividades']:
            actividad_obj = Actividades.objects.get(nombre=nombre_actividad)
            PaqueteActividad.objects.create(
                paquete=paquete,
                actividad=actividad_obj,
                dificultad_nivel=random.choice(['Baja', 'Media', 'Alta'])
            )

        paquetes_creados.append(paquete)

    for idx, paquete in enumerate(paquetes_creados):
        for temporada in temporadas_creadas:
            Tarifa.objects.create(
                paquete=paquete,
                temporada=temporada,
                precio_adulto=Decimal(str(180000 + idx * 45000 + random.randint(20000, 80000))),
                precio_menor=Decimal(str(120000 + idx * 30000 + random.randint(15000, 50000))),
                estado=True,
            )

    print("6. Creación de reservas y pagos...")
    reservas_creadas = []
    for idx in range(10):
        paquete = paquetes_creados[idx % len(paquetes_creados)]
        usuario = clientes_creados[idx % len(clientes_creados)]
        fecha_inicio = date.today() + timedelta(days=idx * 7 + 5)

        tipo_reserva = random.choice(['pendiente', 'pendiente', 'cancelada'])
        reserva = Reserva.objects.create(
            paquete=paquete,
            usuario=usuario,
            fecha_inicio=fecha_inicio,
            numero_adultos=random.randint(1, 3),
            numero_menores=random.randint(0, 2),
            estado_reserva='pendiente',
            motivo_cancelacion=''
        )

        # Se genera un pequeño porcentaje de reservas confirmadas, pero solo cuando existe
        # un pago aprobado; esto respeta la lógica del negocio del proyecto.
        estado_pago = 'pendiente'
        if idx % 4 == 0:
            estado_pago = 'aprobado'

        elif idx % 3 == 0:
            reserva.estado_reserva = 'cancelada'
            reserva.motivo_cancelacion = 'El cliente canceló por cambio de fechas.'
            reserva.save()

        pago = Pago.objects.create(
            reserva=reserva,
            referencia=f"REF-{random.randint(100000, 999999)}",
            banco_origen=random.choice(['Bancolombia', 'Davivienda', 'Nequi', 'Banco de Bogotá']),
            metodo_pago=random.choice(['Transferencia', 'PSE', 'Billetera Digital']),
            monto=reserva.monto_total or Decimal('150000'),
            imagen_comprobante='comprobantes/placeholder.jpg',
            estado_transaccion=estado_pago,
            fecha_pago=timezone.now(),
            nota_admin='Pago generado por población inicial de pruebas.'
        )

        if estado_pago == 'aprobado':
            reserva.estado_reserva = 'confirmada'
            reserva.save()

        reservas_creadas.append(reserva)

    print("7. Creación de promociones, blogs, PQRS y bitácoras...")
    for idx in range(4):
        Promocion.objects.create(
            nombre=f"Promoción Mongua {idx + 1}",
            descripcion="Descuento especial para viajeros que exploran la región y sus destinos de alta montaña.",
            porcentaje_descuento=random.choice([10, 15, 20, 25]),
            fecha_inicio=date.today() - timedelta(days=15),
            fecha_fin=date.today() + timedelta(days=60),
            codigo_promocion=f"MONGUA{idx + 1}",
            activa=True,
        )

    for nombre, contenido, info in [
        ("Mongua y la Laguna Negra", "Mongua, ubicado en la provincia de Sugamuxi en Boyacá, destaca por paisajes de alta montaña y por la presencia de la Laguna Negra, un lugar ligado a la historia, la leyenda y la contemplación del territorio. La experiencia del visitante combina naturaleza, geografía y memoria local.", "Paisaje, leyenda y geografía"),
        ("Piedras de Santo Domingo y la memoria muisca", "El municipio guarda vestigios arqueológicos de gran valor, entre ellos las Piedras de Santo Domingo, un punto de interés que permite reconocer la presencia cultural de los muiscas y la importancia del patrimonio en los Andes boyacenses.", "Arqueología e historia"),
        ("El Páramo de Ocetá y el turismo de altura", "La geografía de Mongua, a 2975 metros sobre el nivel del mar, convierte a este municipio en un destino apropiado para el senderismo de altura, la observación del paisaje y la conexión con la naturaleza andina.", "Senderismo y naturaleza"),
        ("Mongua, agricultura, ganadería y tradición", "La economía del municipio se apoya en la agricultura, la ganadería y la minería, actividades que también forman parte del contexto cultural y productivo del territorio. Esto enriquece la experiencia de quienes visitan el pueblo y se acercan a su identidad local.", "Economía y comunidad"),
        ("Patrimonio de Mongua: iglesia, plaza y comunidad", "La historia del municipio se refleja en la plaza, la iglesia y los relatos de la comunidad. Visitar Mongua es también conocer la forma en que la tradición, la fe y la vida cotidiana se entrelazan en el paisaje boyacense.", "Patrimonio y tradición"),
    ]:
        Blog.objects.create(
            usuario=admin_user,
            titulo=nombre,
            contenido=contenido,
            informacion_adicional=info,
            estado=True,
        )

    for idx in range(8):
        pqr = PQRS.objects.create(
            usuario=clientes_creados[idx % len(clientes_creados)],
            tipo=random.choice(['peticion', 'queja', 'reclamo', 'sugerencia']),
            asunto=f"Consulta {idx + 1} sobre paquetes de Mongua",
            descripcion="Necesito información sobre reservas, disponibilidad y actividades de senderismo para visitar el municipio.",
            estado=random.choice(['abierto', 'en_proceso', 'cerrado'])
        )
        if pqr.estado in ['en_proceso', 'cerrado']:
            Seguimiento.objects.create(
                pqrs=pqr,
                usuario=admin_user,
                respuesta='Se atendió la solicitud con información del paquete y de la disponibilidad del servicio.'
            )

    for idx in range(8):
        Bitacora.objects.create(
            usuario=clientes_creados[idx % len(clientes_creados)],
            accion=random.choice(['LOGIN', 'ACCESO', 'RESERVA', 'CONSULTA']),
            modulo=random.choice(['usuarios', 'reservas', 'paquetes', 'pagos']),
            descripcion='Actividad de prueba del sistema con datos representativos de Mongua.'
        )

    print("\n" + "=" * 60)
    print("[OK] Base de datos poblada con datos representativos de Mongua.")
    print(f"- Usuarios: {Usuario.objects.count()}")
    print(f"- Categorías: {Categoria.objects.count()}")
    print(f"- Actividades: {Actividades.objects.count()}")
    print(f"- Paquetes: {Paquete.objects.count()}")
    print(f"- Temporadas: {Temporada.objects.count()}")
    print(f"- Tarifas: {Tarifa.objects.count()}")
    print(f"- Reservas: {Reserva.objects.count()}")
    print(f"- Pagos: {Pago.objects.count()}")
    print(f"- Blogs: {Blog.objects.count()}")
    print(f"- PQRS: {PQRS.objects.count()}")
    print("=" * 60)


if __name__ == '__main__':
    poblar_base_datos()