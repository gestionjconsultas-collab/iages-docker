#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from flask import Blueprint, jsonify
from models import ConfiguracionGlobal

logger = logging.getLogger(__name__)

desktop_app_bp = Blueprint('desktop_app', __name__)

@desktop_app_bp.route('/api/version', methods=['GET'])
def get_version():
    """
    Endpoint público para que la aplicación de escritorio (Conecta)
    consulte si hay actualizaciones disponibles.
    """
    try:
        def get_config(key, default):
            record = ConfiguracionGlobal.query.filter_by(clave=key).first()
            return record.valor if record else default

        version_data = {
            "version": get_config('conecta_version', '1.2.0'),
            "url": get_config('conecta_url', 'https://iages.es/updates/conecta-1.2.0-setup.exe'),
            "notes": get_config('conecta_notes', 'Integración del nuevo gestor de actualizaciones y mejoras de rendimiento.'),
            "sha256": get_config('conecta_sha256', ''),
            "mandatory": get_config('conecta_mandatory', 'false').lower() == 'true'
        }
        return jsonify(version_data), 200
        
    except Exception as e:
        logger.error(f"Error sirviendo /api/version: {e}")
        return jsonify({"error": "Error interno del servidor"}), 500
