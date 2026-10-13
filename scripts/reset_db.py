import os
import sys

# --- CONFIGURACIÓN ---
# ¡ATENCIÓN APRENDIZ! Verifica que el nombre de tu entorno virtual sea exactamente este.
# Si le pusiste otro nombre (ej. 'env', 'entorno'), cámbialo en la variable de abajo.
VENV_DIR = 'venv'

# Raíz del proyecto (carpeta padre de /scripts), así el script funciona
# sin importar desde dónde se ejecute.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')
ENV_FILE = os.path.join(BASE_DIR, '.env')
archivos_a_borrar = []


def cargar_env(ruta):
    """Lee el archivo .env (clave=valor) sin depender de librerías externas."""
    valores = {}
    if not os.path.exists(ruta):
        return valores
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith('#') or '=' not in linea:
                continue
            clave, valor = linea.split('=', 1)
            valores[clave.strip()] = valor.strip().strip('"').strip("'")
    return valores


def resetear_postgres(cfg):
    """Elimina todas las tablas de PostgreSQL recreando el esquema 'public'."""
    try:
        import psycopg2
    except ImportError:
        print("❌ No se encontró 'psycopg2'. Activa el entorno virtual o instala psycopg2-binary.")
        return False

    try:
        conn = psycopg2.connect(
            dbname=cfg['name'], user=cfg['user'], password=cfg['password'],
            host=cfg['host'], port=cfg['port'],
        )
    except psycopg2.OperationalError as e:
        print(f"❌ No se pudo conectar a PostgreSQL: {e}")
        return False

    conn.autocommit = True
    cur = conn.cursor()
    try:
        # Opción 1: recrear el esquema completo (requiere ser dueño del esquema)
        cur.execute("DROP SCHEMA public CASCADE;")
        cur.execute("CREATE SCHEMA public;")
        cur.execute(f'GRANT ALL ON SCHEMA public TO "{cfg["user"]}";')
        cur.execute("GRANT ALL ON SCHEMA public TO public;")
        print(f"Borrado: todas las tablas de PostgreSQL '{cfg['name']}' (esquema public recreado)")
    except psycopg2.Error as e:
        # Opción 2: si no somos dueños del esquema, borrar todo lo que nos pertenece
        print(f"⚠️  No se pudo recrear el esquema ({e.pgerror or e}). Intentando DROP OWNED...")
        try:
            cur.execute("DROP OWNED BY CURRENT_USER CASCADE;")
            print(f"Borrado: todos los objetos de '{cfg['user']}' en '{cfg['name']}'")
        except psycopg2.Error as e2:
            print(f"❌ Error al limpiar PostgreSQL: {e2}")
            return False
    finally:
        cur.close()
        conn.close()
    return True


print("\n=== HERRAMIENTA DE RESETEO DE MIGRACIONES Y BASE DE DATOS ===")
print(f"Nota: Se ignorará la carpeta del entorno virtual: '{VENV_DIR}'")

# 1. Buscar archivos de migración recursivamente
for root, dirs, files in os.walk(BASE_DIR):
    # Ignorar carpetas comunes de entornos virtuales y control de versiones
    for venv in ['.venv', 'venv', VENV_DIR, '.git', '__pycache__']:
        if venv in dirs:
            dirs.remove(venv)

    # Buscar solo dentro de carpetas llamadas 'migrations'
    if os.path.basename(root) == 'migrations':
        for file in files:
            # Seleccionar archivos de migración (excluyendo __init__.py)
            if file != '__init__.py' and file.endswith('.py'):
                archivos_a_borrar.append(os.path.join(root, file))

# 2. Verificar qué bases de datos existen
db_existe = os.path.exists(DB_FILE)

env = cargar_env(ENV_FILE)
pg_cfg = None
motor = env.get('DB_ENGINE', 'django.db.backends.postgresql')
if env.get('DB_NAME') and 'postgresql' in motor:
    pg_cfg = {
        'name': env['DB_NAME'],
        'user': env.get('DB_USER', 'postgres'),
        'password': env.get('DB_PASSWORD', ''),
        'host': env.get('DB_HOST', 'localhost'),
        'port': env.get('DB_PORT', '5432'),
    }

# 3. Mostrar resumen al usuario
print(f"\nSe encontraron {len(archivos_a_borrar)} archivos de migración:")
for archivo in archivos_a_borrar:
    print(f" - {os.path.relpath(archivo, BASE_DIR)}")

if db_existe:
    print(f"\nTambién se encontró la base de datos SQLite: {os.path.basename(DB_FILE)}")
else:
    print("\nNo se encontró la base de datos SQLite (ya fue borrada o no existe).")

if pg_cfg:
    print(f"Base de datos PostgreSQL configurada en .env: "
          f"'{pg_cfg['name']}' en {pg_cfg['host']}:{pg_cfg['port']} (usuario '{pg_cfg['user']}')")
    print("   -> Se ELIMINARÁN TODAS sus tablas y datos.")
else:
    print("No hay base de datos PostgreSQL configurada en .env.")

if len(archivos_a_borrar) == 0 and not db_existe and not pg_cfg:
    print("\nNo hay nada que borrar. ¡El proyecto ya está limpio!")
    sys.exit()

# 4. Pedir confirmación por seguridad
respuesta = input(
    "\n¿Estás seguro de que deseas ELIMINAR estos archivos/datos? Esta acción NO se puede deshacer. (s/n): ")

if respuesta.lower() == 's':
    # Borrar migraciones
    for archivo in archivos_a_borrar:
        os.remove(archivo)
        print(f"Borrado: {os.path.relpath(archivo, BASE_DIR)}")

    # Borrar base de datos SQLite
    if db_existe:
        os.remove(DB_FILE)
        print(f"Borrado: {os.path.basename(DB_FILE)}")

    # Resetear PostgreSQL
    pg_ok = True
    if pg_cfg:
        print("\nTip: detén 'runserver' antes, para evitar bloqueos en la base de datos.")
        pg_ok = resetear_postgres(pg_cfg)

    if pg_ok:
        print("\n✅ ¡Limpieza completada exitosamente!")
        print("Siguiente paso: python manage.py makemigrations && python manage.py migrate")
    else:
        print("\n⚠️  Limpieza parcial: revisa el error de PostgreSQL arriba.")
else:
    print("\n🚫 Operación cancelada. No se borró ningún archivo.")
