"""
Módulo de servicio y lógica NLP para el asistente virtual Condy.
"""
from .condy_nlp import FAQS, remove_accents, procesar_mensaje

__all__ = ['FAQS', 'remove_accents', 'procesar_mensaje']
