from django.urls import path
from autenticacion.views.login import views as login_views
from autenticacion.views.registro import views as registro_views
from autenticacion.views.recuperar_apodo import views as apodo_views
from autenticacion.views.recuperar_clave import views as clave_views
from autenticacion.views.ajax import views as ajax_views
from autenticacion.views.htmx import views as htmx_views
from autenticacion.views.geografia import views as geo_views

urlpatterns = [
    # Inicio y Cierre de Sesión
    path('login/', login_views.login_vista, name='login'),
    path('logout/', login_views.logout_vista, name='logout'),

    # Registro de Usuarios y Validación OTP
    path('registro/', registro_views.registro_vista, name='registro'),
    path('registro/verificar-otp/', registro_views.verificar_otp_registro_vista, name='verificar_otp_registro'),
    path('registro/reenviar-otp/', registro_views.reenviar_otp_registro_vista, name='reenviar_otp_registro'),

    # Recuperación de Nombre de Usuario / Apodo
    path('recuperar-apodo/', apodo_views.recuperar_apodo_vista, name='recuperar_apodo'),

    # Recuperación de Contraseña con OTP y Enlace
    path('recuperar-clave/', clave_views.recuperar_clave_vista, name='recuperar_clave'),
    path('recuperar-clave/verificar-otp/', clave_views.verificar_otp_recuperar_vista, name='verificar_otp_clave'),
    path('recuperar-clave/enviado/', clave_views.restablecer_clave_enviado_vista, name='clave_enviada'),
    path('recuperar-clave/confirmar/<uidb64>/<token>/', clave_views.restablecer_clave_confirmar_vista, name='confirmar_clave'),
    path('recuperar-clave/guardada/', clave_views.restablecer_clave_guardar_vista, name='clave_guardada'),

    # Verificación Reactiva en Tiempo Real con HTMX (Reemplazo Seguro de AJAX)
    path('htmx/verificar-apodo/', htmx_views.verificar_apodo_htmx, name='verificar_apodo_htmx'),
    path('htmx/verificar-email/', htmx_views.verificar_email_htmx, name='verificar_email_htmx'),
    path('htmx/verificar-documento/', htmx_views.verificar_documento_htmx, name='verificar_documento_htmx'),
    path('htmx/verificar-telefono/', htmx_views.verificar_telefono_htmx, name='verificar_telefono_htmx'),

    # Verificación en Tiempo Real (Compatibilidad AJAX heredada)
    path('ajax/verificar-campo/', ajax_views.verificar_campo_ajax, name='verificar_campo_ajax'),
    path('verificar-campo/', ajax_views.verificar_campo_ajax, name='verificar_campo_directo'),

    # APIs Geográficas Locales (dr5hn)
    path('api/paises/', geo_views.api_paises, name='api_paises'),
    path('api/departamentos/<str:pais_id>/', geo_views.api_departamentos, name='api_departamentos'),
    path('api/ciudades/<int:departamento_id>/', geo_views.api_ciudades, name='api_ciudades'),
]
