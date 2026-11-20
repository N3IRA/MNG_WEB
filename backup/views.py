import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods


def es_administrador(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'rol', None) == 1)


def obtener_motor():
    engine = settings.DATABASES['default']['ENGINE']
    if 'postgresql' in engine:
        return 'postgresql'
    if 'sqlite' in engine:
        return 'sqlite'
    if 'mysql' in engine:
        return 'mysql'
    return 'desconocido'


def probar_conexion():
    motor = obtener_motor()
    db = settings.DATABASES['default']

    if motor == 'sqlite':
        return os.path.exists(str(db['NAME']))

    if motor == 'postgresql':
        try:
            import psycopg2
            conn = psycopg2.connect(
                dbname=db['NAME'], user=db['USER'], password=db['PASSWORD'],
                host=db['HOST'] or 'localhost', port=db['PORT'] or '5432',
                connect_timeout=5,
            )
            conn.close()
            return True
        except Exception:
            return False

    if motor == 'mysql':
        try:
            from django.db import connections
            connections['default'].cursor().execute('SELECT 1')
            return True
        except Exception:
            return False

    return False


def ejecutable_postgres(nombre):
    encontrado = shutil.which(nombre)
    if encontrado:
        return encontrado
    posibles = (
        r'C:\Program Files\PostgreSQL\18\bin',
        r'C:\Program Files\PostgreSQL\17\bin',
        r'C:\Program Files\PostgreSQL\16\bin',
        r'C:\Program Files\PostgreSQL\15\bin',
        r'C:\Program Files\PostgreSQL\14\bin',
        r'C:\Program Files\PostgreSQL\13\bin',
    )
    for directorio in posibles:
        ruta = os.path.join(directorio, f'{nombre}.exe')
        if os.path.exists(ruta):
            return ruta
    return None


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['GET', 'POST'])
def backup(request):
    motor = obtener_motor()
    conectado = probar_conexion()

    if request.method == 'POST':
        if request.POST.get('accion') != 'backup_completo':
            return JsonResponse({'error': 'Acción no válida'}, status=400)
        if not conectado:
            return JsonResponse({'error': 'No se puede conectar a la base de datos activa.'}, status=400)
        try:
            if motor == 'postgresql':
                return descargar_backup_postgresql()
            if motor == 'sqlite':
                return descargar_backup_sqlite()
            return JsonResponse({'error': f'Respaldo automático no soportado para el motor: {motor}'}, status=400)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

    return render(request, 'backup/menu.html', {
        'titulo': 'Respaldo y Restauración de Base de Datos',
        'db_conectada': conectado,
        'motor_db': motor,
        'nombre_db': settings.DATABASES['default']['NAME'],
    })


@login_required(login_url='login')
@user_passes_test(es_administrador, login_url='login')
@require_http_methods(['POST'])
def restaurar_datos(request):
    if 'archivo' not in request.FILES:
        return JsonResponse({'error': 'No se proporcionó ningún archivo'}, status=400)

    archivo = request.FILES['archivo']
    if not archivo.name.lower().endswith('.sql'):
        return JsonResponse({'error': 'El archivo debe tener extensión .sql'}, status=400)
    if archivo.size > 100 * 1024 * 1024:
        return JsonResponse({'error': 'El archivo supera el límite de 100 MB'}, status=400)

    contenido = archivo.read()
    try:
        contenido_sql = contenido.decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            contenido_sql = contenido.decode('cp1252')
        except UnicodeDecodeError:
            return JsonResponse({'error': 'El archivo SQL no tiene una codificación válida'}, status=400)

    try:
        motor = obtener_motor()
        if motor == 'postgresql':
            restaurar_postgresql(contenido_sql)
        elif motor == 'sqlite':
            restaurar_sqlite(contenido_sql)
        else:
            return JsonResponse({'error': f'Restauración no soportada para el motor: {motor}'}, status=400)
        return JsonResponse({'exito': True, 'mensaje': 'Base de datos restaurada correctamente.'})
    except Exception as exc:
        return JsonResponse({'error': f'Error al restaurar: {exc}'}, status=400)


def descargar_backup_postgresql():
    pg_dump = ejecutable_postgres('pg_dump')
    if not pg_dump:
        raise Exception('No se encontró pg_dump. Instala PostgreSQL o agrega su carpeta bin al PATH.')

    db = settings.DATABASES['default']
    cmd = [
        pg_dump,
        '--host', db['HOST'] or 'localhost',
        '--port', str(db['PORT'] or '5432'),
        '--username', db['USER'],
        '--dbname', db['NAME'],
        '--format=plain',
        '--clean',
        '--if-exists',
        '--no-owner',
        '--no-acl',
        '--encoding=UTF8',
    ]
    env = os.environ.copy()
    env['PGPASSWORD'] = db['PASSWORD'] or ''
    resultado = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=120)
    if resultado.returncode != 0:
        raise Exception(resultado.stderr.strip() or 'PostgreSQL no pudo crear el respaldo')

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(resultado.stdout, content_type='application/sql; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="backup_postgresql_{fecha}.sql"'
    return response


def descargar_backup_sqlite():
    db = settings.DATABASES['default']
    ruta = str(db['NAME'])
    connection.close()

    con = sqlite3.connect(ruta)
    try:
        lineas = [
            '-- Respaldo SQLite generado por Monagua',
            f'-- Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '-- Motor: SQLite',
        ]
        lineas.extend(con.iterdump())
        contenido = '\n'.join(lineas)
    finally:
        con.close()

    fecha = datetime.now().strftime('%Y%m%d_%H%M%S')
    response = HttpResponse(contenido, content_type='application/sql; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="backup_sqlite_{fecha}.sql"'
    return response


def restaurar_postgresql(contenido_sql):
    psql = ejecutable_postgres('psql')
    if not psql:
        raise Exception('No se encontró psql. Instala PostgreSQL o agrega su carpeta bin al PATH.')

    if not contenido_sql.strip():
        raise Exception('El archivo SQL está vacío')

    db = settings.DATABASES['default']
    cmd = [
        psql,
        '--host', db['HOST'] or 'localhost',
        '--port', str(db['PORT'] or '5432'),
        '--username', db['USER'],
        '--dbname', db['NAME'],
        '--set=ON_ERROR_STOP=1',
        '--no-psqlrc',
    ]
    env = os.environ.copy()
    env['PGPASSWORD'] = db['PASSWORD'] or ''

    connection.close()
    proceso = subprocess.run(
        cmd,
        input=contenido_sql,
        capture_output=True,
        text=True,
        encoding='utf-8',
        env=env,
        timeout=180,
    )
    connection.close()

    if proceso.returncode != 0:
        detalle = proceso.stderr.strip() or proceso.stdout.strip()
        raise Exception(detalle or 'psql rechazó el archivo SQL')


def restaurar_sqlite(contenido_sql):
    if not contenido_sql.strip() or not any(
        linea.strip() and not linea.lstrip().startswith('--')
        for linea in contenido_sql.splitlines()
    ):
        raise Exception('El archivo está vacío o no contiene instrucciones SQL')

    db = settings.DATABASES['default']
    ruta_original = str(db['NAME'])
    connection.close()

    directorio = os.path.dirname(ruta_original)
    descriptor, ruta_temporal = tempfile.mkstemp(suffix='.sqlite3', dir=directorio)
    os.close(descriptor)
    os.unlink(ruta_temporal)

    try:
        con = sqlite3.connect(ruta_temporal)
        con.executescript(contenido_sql)
        integridad = con.execute('PRAGMA integrity_check').fetchone()
        if not integridad or integridad[0] != 'ok':
            raise Exception(f'La copia restaurada no pasó la integridad: {integridad}')
        con.commit()
        con.close()

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        copia_seguridad = f'{ruta_original}.pre_restore_{timestamp}.bak'
        if os.path.exists(ruta_original):
            shutil.copy2(ruta_original, copia_seguridad)

        os.replace(ruta_temporal, ruta_original)
        connection.close()
    except Exception:
        if os.path.exists(ruta_temporal):
            os.remove(ruta_temporal)
        raise
