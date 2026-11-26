#!/bin/sh
set -e

# ==============================================================================
# Script de Entrada para Contenedor Docker (Django MNG_WEB)
# Espera a que PostgreSQL esté listo, ejecuta migraciones y levanta el servidor
# ==============================================================================

if [ "$DB_ENGINE" = "django.db.backends.postgresql" ] || [ -n "$DB_NAME" ]; then
    echo "==> Verificando conexión a la base de datos PostgreSQL ($DB_HOST:$DB_PORT)..."
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 0.5
    done
    echo "==> Base de datos PostgreSQL conectada y lista."
fi

# Aplicar migraciones pendientes
echo "==> Aplicando migraciones de base de datos..."
python manage.py migrate --noinput

# Recopilar archivos estáticos si no están en modo debug o si se requiere
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ]; then
    echo "==> Recolectando archivos estáticos para producción..."
    python manage.py collectstatic --noinput --clear || true
fi

echo "==> Iniciando proceso: $@"
exec "$@"
