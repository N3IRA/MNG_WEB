# ==============================================================================
# Dockerfile para MNG_WEB - Monagua Turismo (Django 6.1 + Python 3.13)
# ==============================================================================
FROM python:3.13-slim

# Evitar que Python genere archivos .pyc y habilitar logs en tiempo real sin búfer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Directorio de trabajo de la aplicación
WORKDIR /app

# Instalar dependencias del sistema requeridas para PostgreSQL, Pillow, PDF y utilidades
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    python3-dev \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7 \
    libtiff-dev \
    libxml2-dev \
    libxslt1-dev \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para optimizar la caché de capas de Docker
COPY requirements.txt /app/

# Actualizar gestor de paquetes e instalar librerías de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn==23.0.0

# Copiar el código fuente completo del proyecto
COPY . /app/

# Crear directorios para archivos estáticos y multimedia
RUN mkdir -p /app/staticfiles /app/media

# Copiar script de entrada, normalizar saltos de línea LF (Unix) y otorgar permisos
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN tr -d '\r' < /app/docker-entrypoint.sh > /app/docker-entrypoint.sh.tmp && \
    mv /app/docker-entrypoint.sh.tmp /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

# Exponer el puerto predeterminado de Django
EXPOSE 8000

# Punto de entrada para espera de base de datos y migraciones automáticas
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Comando por defecto para iniciar el servidor
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
