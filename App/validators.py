"""
Módulo de validadores de seguridad para subida de archivos e imágenes en Monagua.
Aplica directrices de OWASP para prevenir:
- Web shells y ejecución remota de código (RCE)
- Inyecciones de scripts (XSS vía SVG o políglotas)
- Ataques de Path Traversal
- Bombas de descompresión (Decompression Bombs / DoS)
- Manipulación de extensiones y dobles extensiones (.php.png, etc.)
- Carga de archivos no autorizados
"""

import os
import re
from PIL import Image
from django.core.exceptions import ValidationError

# Límite máximo de píxeles para prevenir Decompression Bombs en Pillow (50 MP)
Image.MAX_IMAGE_PIXELS = 50_000_000

# Extensiones ejecutables y peligrosas prohibidas en cualquier parte del nombre del archivo
EXTENSIONES_PELIGROSAS = (
    '.php', '.phtml', '.php3', '.php4', '.php5', '.phps',
    '.exe', '.sh', '.bat', '.py', '.pl', '.jsp', '.asp',
    '.aspx', '.cgi', '.cmd', '.vbs', '.js', '.jar', '.svg',
    '.html', '.htm', '.shtml', '.htaccess'
)

# Formatos de imagen estrictamente permitidos
EXTENSIONES_IMAGENES_PERMITIDAS = ('.jpg', '.jpeg', '.png', '.webp', '.gif')
FORMATOS_PILLOW_PERMITIDOS = ('JPEG', 'PNG', 'WEBP', 'GIF')

# Firmas de código malicioso en cabeceras o primeros bytes
PATRONES_MALICIOSOS = (
    b'<?php', b'<?=', b'<script', b'eval(', b'base64_decode',
    b'system(', b'shell_exec(', b'passthru(', b'exec(',
    b'<html', b'<!doctype', b'onload=', b'onerror='
)


def validar_imagen_segura(archivo, max_mb=5, permitir_pdf=False, ancho_max=6000, alto_max=6000):
    """
    Valida rigurosamente que el archivo subido sea una imagen legítima (o PDF si permitir_pdf=True).
    Verifica tamaño, extensiones, nombres sospechosos, magic bytes y estructura interna con Pillow.
    """
    if not archivo:
        return archivo

    # 1. Validación de tamaño
    if hasattr(archivo, 'size'):
        if archivo.size <= 0:
            raise ValidationError("El archivo subido está vacío.")
        if archivo.size > max_mb * 1024 * 1024:
            raise ValidationError(f"El archivo es demasiado grande ({archivo.size / (1024*1024):.1f} MB). El tamaño máximo permitido es de {max_mb} MB.")

    nombre = getattr(archivo, 'name', '') or ''
    nombre_lower = nombre.lower().strip()

    # 2. Protección contra Path Traversal
    if '..' in nombre_lower or '/' in nombre_lower or '\\' in nombre_lower:
        raise ValidationError("El nombre del archivo contiene caracteres o rutas no permitidas.")

    # 3. Protección contra dobles extensiones maliciosas (ej: foto.php.png)
    for ext_peligrosa in EXTENSIONES_PELIGROSAS:
        if ext_peligrosa in nombre_lower:
            raise ValidationError(
                f"Archivo sospechoso detectado con extensión no permitida ({ext_peligrosa}). Solo se admiten imágenes limpias o PDF."
            )

    # 4. Validación de extensión permitida
    _, ext = os.path.splitext(nombre_lower)
    extensiones_validas = EXTENSIONES_IMAGENES_PERMITIDAS + (('.pdf',) if permitir_pdf else ())
    
    if ext not in extensiones_validas:
        formatos_str = ', '.join([e.replace('.', '').upper() for e in extensiones_validas])
        raise ValidationError(
            f"Extensión no permitida ('{ext}'). Solo se admiten archivos de tipo: {formatos_str}."
        )

    # 5. Inspección de código malicioso en los primeros bytes
    pos_original = archivo.tell() if hasattr(archivo, 'tell') else 0
    if hasattr(archivo, 'seek'):
        archivo.seek(0)
    
    primeros_bytes = archivo.read(4096) if hasattr(archivo, 'read') else b''
    
    if hasattr(archivo, 'seek'):
        archivo.seek(pos_original)

    primeros_bytes_lower = primeros_bytes.lower()
    for patron in PATRONES_MALICIOSOS:
        if patron in primeros_bytes_lower:
            raise ValidationError(
                "El archivo adjunto contiene código ejecutable no permitido por seguridad."
            )

    # 6. Verificación profunda según el tipo de archivo
    if ext == '.pdf' and permitir_pdf:
        if not primeros_bytes.startswith(b'%PDF-'):
            raise ValidationError("El archivo PDF del comprobante está dañado o no es un PDF válido.")
    else:
        # Validación con Pillow para imágenes
        try:
            if hasattr(archivo, 'seek'):
                archivo.seek(0)

            # verify() comprueba la integridad de la cabecera y estructura interna
            with Image.open(archivo) as img:
                img.verify()

            # Reabrimos para inspeccionar formato real y dimensiones
            if hasattr(archivo, 'seek'):
                archivo.seek(0)

            with Image.open(archivo) as img:
                formato = (img.format or '').upper()
                if formato not in FORMATOS_PILLOW_PERMITIDOS:
                    raise ValidationError(
                        f"El formato interno de la imagen ('{formato}') no es compatible o seguro. Solo se admiten: JPEG, PNG, WebP o GIF."
                    )

                ancho, alto = img.size
                if ancho > ancho_max or alto > alto_max:
                    raise ValidationError(
                        f"Las dimensiones de la imagen ({ancho}x{alto} px) exceden el límite máximo permitido de {ancho_max}x{alto_max} px."
                    )

        except ValidationError:
            raise
        except Exception:
            raise ValidationError(
                "El archivo subido no es una imagen válida o se encuentra dañado. Asegúrate de que sea un archivo JPG, PNG o WebP real."
            )
        finally:
            if hasattr(archivo, 'seek'):
                archivo.seek(pos_original)

    return archivo


def validar_foto_perfil(archivo):
    """Validador específico para fotos de perfil (máx 5 MB, sin PDF)."""
    return validar_imagen_segura(archivo, max_mb=5, permitir_pdf=False, ancho_max=5000, alto_max=5000)


def validar_imagen_paquete(archivo):
    """Validador para imágenes de paquetes turísticos y destinos (máx 8 MB, sin PDF)."""
    return validar_imagen_segura(archivo, max_mb=8, permitir_pdf=False, ancho_max=6000, alto_max=6000)


def validar_imagen_blog(archivo):
    """Validador para imágenes de artículos de blog (máx 8 MB, sin PDF)."""
    return validar_imagen_segura(archivo, max_mb=8, permitir_pdf=False, ancho_max=6000, alto_max=6000)


def validar_comprobante_pago(archivo):
    """Validador para comprobantes de pago de reservas y reembolsos (máx 10 MB, permite PDF)."""
    return validar_imagen_segura(archivo, max_mb=10, permitir_pdf=True, ancho_max=6000, alto_max=6000)


def validar_archivo_subido(archivo, validator_func=validar_imagen_segura, **kwargs):
    """
    Función auxiliar para vistas tradicionales (FBVs).
    Retorna (True, None) si el archivo es válido, o (False, error_str) si falla la validación.
    """
    if not archivo:
        return True, None
    try:
        validator_func(archivo, **kwargs)
        return True, None
    except ValidationError as e:
        mensaje = e.messages[0] if hasattr(e, 'messages') and e.messages else str(e)
        return False, mensaje
