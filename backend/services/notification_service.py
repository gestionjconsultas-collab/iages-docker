"""
Servicio centralizado para gestión de notificaciones push del navegador
"""
from models import NotificationPreferences, db
from flask import current_app


class NotificationService:
    
    @staticmethod
    def get_user_preferences(user_id):
        """Obtener preferencias de notificación del usuario"""
        prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()
        
        if not prefs:
            # Crear preferencias por defecto
            prefs = NotificationPreferences(user_id=user_id)
            db.session.add(prefs)
            db.session.commit()
        
        return prefs.to_dict()
    
    @staticmethod
    def update_preferences(user_id, preferences):
        """Actualizar preferencias de usuario"""
        prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()
        
        if not prefs:
            prefs = NotificationPreferences(user_id=user_id)
            db.session.add(prefs)
        
        # Actualizar campos permitidos
        allowed_fields = [
            'enabled', 'sound_enabled',
            'documentos_procesados', 'errores_procesamiento',
            'vencimientos', 'tareas_asignadas',
            'respuestas_soporte', 'mantenimiento'
        ]
        
        for key, value in preferences.items():
            if key in allowed_fields and hasattr(prefs, key):
                setattr(prefs, key, value)
        
        db.session.commit()
        return True
    
    @staticmethod
    def should_notify(user_id, notification_type):
        """
        Verificar si se debe notificar al usuario
        
        Args:
            user_id: ID del usuario
            notification_type: Tipo de notificación
                - 'documento_procesado'
                - 'error_procesamiento'
                - 'vencimiento'
                - 'tarea_asignada'
                - 'respuesta_soporte'
                - 'mantenimiento'
        
        Returns:
            bool: True si se debe notificar, False en caso contrario
        """
        prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()
        
        if not prefs or not prefs.enabled:
            return False
        
        # Mapeo de tipos de notificación a campos del modelo
        type_map = {
            'documento_procesado': 'documentos_procesados',
            'error_procesamiento': 'errores_procesamiento',
            'vencimiento': 'vencimientos',
            'tarea_asignada': 'tareas_asignadas',
            'respuesta_soporte': 'respuestas_soporte',
            'mantenimiento': 'mantenimiento'
        }
        
        pref_field = type_map.get(notification_type)
        if pref_field:
            return getattr(prefs, pref_field, False)
        
        return False
    
    @staticmethod
    def get_sound_enabled(user_id):
        """Verificar si el usuario tiene sonido activado"""
        prefs = NotificationPreferences.query.filter_by(user_id=user_id).first()
        return prefs.sound_enabled if prefs else True
