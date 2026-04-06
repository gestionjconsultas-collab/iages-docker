"""
Utilidad para Sistema Multi-Key de Gemini API
==============================================

Proporciona función centralizada para obtener API key disponible
con fallback automático cuando se agota la cuota.

Uso:
    from gemini_utils import obtener_gemini_con_fallback
    
    response, key_usada = obtener_gemini_con_fallback(
        prompt="Tu pregunta aquí",
        modelo='gemini-2.5-flash',
        historial=[]  # Opcional
    )
"""

import os
import google.generativeai as genai
from typing import Optional, Tuple, List, Dict, Any
from datetime import date, datetime


def registrar_uso_api_key(key_number: int, success: bool = True, tokens: int = 0):
    """
    Registra el uso de una API key en la base de datos con gestoría
    
    Args:
        key_number: Número de la key (1, 2, 3)
        success: Si la llamada fue exitosa
        tokens: Tokens consumidos
    """
    try:
        from utils.quota_utils import track_api_usage
        from tenant_utils import get_current_gestoria_id
        
        key_name = f"GEMINI_API_KEY_{key_number}"
        
        # Obtener gestoria_id del contexto actual
        gestoria_id = get_current_gestoria_id()
        
        # Usar la función de quota_utils que incluye gestoria_id
        track_api_usage(
            key_name=key_name,
            tokens_used=tokens,
            success=success,
            gestoria_id=gestoria_id
        )
        
        print(f"✅ Tracking registrado: {key_name} - Gestoría #{gestoria_id} - Tokens: {tokens}")
        
    except Exception as e:
        print(f"⚠️ Error registrando uso de API key: {e}")
        import traceback
        traceback.print_exc()


def obtener_gemini_con_fallback(
    prompt: str,
    modelo: str = 'gemini-2.5-flash',
    historial: Optional[List[Dict[str, Any]]] = None,
    generation_config: Optional[Dict[str, Any]] = None
) -> Tuple[Any, int]:
    """
    Llama a Gemini API con sistema de fallback multi-key
    
    Args:
        prompt: Texto del prompt
        modelo: Nombre del modelo a usar
        historial: Historial de conversación (opcional)
        generation_config: Configuración de generación (opcional)
        tipo_uso: 'chat' o 'documentos' para seleccionar el pool de keys
    
    Returns:
        Tuple[response, key_usada]: Respuesta de Gemini y número de key usada (1-3)
    
    Raises:
        Exception: Si todas las keys agotaron su cuota o hay otro error
    """
    
    # Obtener keys del entorno según el tipo de uso
    keys_pool = GEMINI_KEYS.get(tipo_uso, GEMINI_KEYS['chat']) # Fallback a 'chat' si tipo_uso no es válido
    
    # Filtrar keys vacías
    gemini_keys = [key for key in keys_pool if key]
    
    if not gemini_keys:
        raise Exception(f'No hay API keys de Gemini configuradas para el tipo de uso "{tipo_uso}"')
    
    response = None
    key_usada = None
    error_final = None
    
    # Intentar con cada key hasta que una funcione
    for i, api_key in enumerate(gemini_keys, 1):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(modelo)
            
            # Configurar parámetros de generación si se proporcionan
            if generation_config:
                model._generation_config = generation_config
            
            # Llamar a Gemini
            if historial:
                # Conversación existente - usar historial
                chat = model.start_chat(history=historial)
                response = chat.send_message(prompt)
            else:
                # Primera pregunta - sin historial
                response = model.generate_content(prompt)
            
            key_usada = i
            
            # Registrar uso exitoso
            try:
                tokens_usados = 0
                if hasattr(response, 'usage_metadata') and hasattr(response.usage_metadata, 'total_token_count'):
                    tokens_usados = response.usage_metadata.total_token_count
                registrar_uso_api_key(i, success=True, tokens=tokens_usados)
            except Exception as e:
                print(f"⚠️ Error registrando tracking: {e}")
            
            # Si llegamos aquí, la llamada fue exitosa
            print(f"✅ Gemini API: Respuesta generada con Key #{i} ({modelo})")
            break
            
        except Exception as e:
            error_msg = str(e)
            
            # Si es error de cuota (429), intentar siguiente key
            if '429' in error_msg or 'quota' in error_msg.lower() or 'ResourceExhausted' in error_msg:
                print(f"⚠️ Gemini API: Key #{i} agotó su cuota, intentando con siguiente key...")
                # Registrar error
                try:
                    registrar_uso_api_key(i, success=False)
                except Exception as track_error:
                    print(f"⚠️ Error registrando tracking: {track_error}")
                error_final = f"Cuota agotada en key #{i}"
                continue
            else:
                # Otro tipo de error, no continuar
                print(f"❌ Gemini API: Error en Key #{i}: {error_msg}")
                error_final = error_msg
                raise e
    
    # Si ninguna key funcionó
    if response is None:
        raise Exception(f'Todas las API keys de Gemini agotaron su cuota. {error_final}')
    
    return response, key_usada


def obtener_api_key_disponible() -> Tuple[str, int]:
    """
    Obtiene la primera API key disponible sin hacer llamada a Gemini
    
    Returns:
        Tuple[api_key, numero]: API key y su número (1-3)
    
    Raises:
        Exception: Si no hay keys configuradas
    """
    gemini_keys = [
        os.getenv('GEMINI_API_KEY'),
        os.getenv('GEMINI_API_KEY_2'),
        os.getenv('GEMINI_API_KEY_3'),
    ]
    
    gemini_keys = [key for key in gemini_keys if key]
    
    if not gemini_keys:
        raise Exception('No hay API keys de Gemini configuradas en .env')
    
    # Retornar primera key disponible
    return gemini_keys[0], 1
