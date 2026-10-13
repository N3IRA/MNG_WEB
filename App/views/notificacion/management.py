"""
Módulo de gestión y tareas de notificaciones (reubicado desde App/management).
"""
from .notificar_vencimiento import notificar_vencimientos, Command

__all__ = ['notificar_vencimientos', 'Command']
