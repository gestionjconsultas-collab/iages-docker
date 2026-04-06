# backend/cocoindex/template_matcher.py
"""
Template Matcher con Embeddings
Identifica automáticamente el tipo de documento usando similarity search
"""

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Optional
import json

class TemplateMatcher:
    """
    Identifica plantillas de documentos usando embeddings
    
    Uso:
        matcher = TemplateMatcher()
        result = matcher.find_best_template(texto_pdf)
        
        if result['confidence'] > 0.8:
            # Usar plantilla conocida
            template = result['template']
        else:
            # Fallback a extracción genérica
            pass
    """
    
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        """
        Inicializa el matcher con modelo de embeddings
        
        Args:
            model_name: Nombre del modelo de sentence-transformers
                       'all-MiniLM-L6-v2' es ligero y rápido (384 dim)
        """
        print(f"🔧 Inicializando TemplateMatcher con modelo '{model_name}'...")
        self.model = SentenceTransformer(model_name)
        self.templates_cache = None
        self.embeddings_cache = None
        print("✅ TemplateMatcher listo")
    
    def load_templates(self) -> List[Dict]:
        """
        Carga plantillas desde la base de datos
        
        Returns:
            List de plantillas con sus embeddings
        """
        try:
            from models import db
            from sqlalchemy import text
            
            # Query para obtener plantillas activas
            query = text("""
            SELECT id, codigo, nombre, descripcion, campos, embedding
            FROM document_templates
            WHERE is_active = TRUE
            ORDER BY usage_count DESC
            """)
            
            result = db.session.execute(query)
            templates = []
            
            for row in result:
                # Convertir embedding de JSONB a numpy array
                embedding_data = row[5]  # JSONB
                embedding = None
                
                if embedding_data:
                    # Si es una lista JSON, convertir a numpy array
                    if isinstance(embedding_data, list):
                        embedding = np.array(embedding_data, dtype=np.float32)
                    elif isinstance(embedding_data, str):
                        import json
                        embedding = np.array(json.loads(embedding_data), dtype=np.float32)
                
                template = {
                    'id': row[0],
                    'codigo': row[1],
                    'nombre': row[2],
                    'descripcion': row[3],
                    'campos': row[4],  # Ya es dict (JSONB)
                    'embedding': embedding
                }
                templates.append(template)
            
            print(f"✅ Cargadas {len(templates)} plantillas desde BD")
            return templates
            
        except Exception as e:
            print(f"⚠️ Error cargando plantillas desde BD: {e}")
            import traceback
            traceback.print_exc()
            # Fallback a plantillas hardcoded
            return self._get_hardcoded_templates()
    
    def _get_hardcoded_templates(self) -> List[Dict]:
        """Plantillas hardcoded como fallback"""
        return [
            {
                'id': None,
                'codigo': 'embargo',
                'nombre': 'Embargo',
                'descripcion': 'Embargo de cuenta bancaria',
                'campos': {
                    'numero_referencia': 'Referencia del embargo',
                    'importe_embargado': 'Importe embargado',
                    'numero_cuenta': 'IBAN',
                    'nif_deudor': 'NIF del deudor'
                },
                'embedding': None
            },
            {
                'id': None,
                'codigo': 'pago_cuenta',
                'nombre': 'Pago a Cuenta',
                'descripcion': 'Carta de pago a cuenta',
                'campos': {
                    'importe_pagar': 'Importe a pagar',
                    'periodo': 'Periodo fiscal'
                },
                'embedding': None
            }
        ]
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Genera embedding de un texto
        
        Args:
            text: Texto del documento
        
        Returns:
            numpy array con el embedding (384 dim)
        """
        # Usar solo primeras 500 palabras para velocidad
        words = text.split()[:500]
        text_sample = ' '.join(words)
        
        # Generar embedding
        embedding = self.model.encode(text_sample, convert_to_numpy=True)
        return embedding
    
    def find_best_template(
        self, 
        text: str, 
        min_confidence: float = 0.75
    ) -> Dict:
        """
        Encuentra la mejor plantilla para un documento
        
        Args:
            text: Texto extraído del PDF
            min_confidence: Umbral mínimo de confianza (0-1)
        
        Returns:
            {
                'template': Dict con la plantilla (o None),
                'confidence': float (0-1),
                'method': 'embedding' | 'none'
            }
        """
        # Cargar plantillas si no están en caché
        if self.templates_cache is None:
            self.templates_cache = self.load_templates()
        
        if not self.templates_cache:
            return {
                'template': None,
                'confidence': 0.0,
                'method': 'none'
            }
        
        # Generar embeddings de plantillas si no existen
        self._ensure_template_embeddings()
        
        # Generar embedding del documento
        doc_embedding = self.generate_embedding(text)
        
        # Calcular similitud con cada plantilla
        best_template = None
        best_score = 0.0
        
        for template in self.templates_cache:
            if template['embedding'] is None:
                continue
            
            # Similitud coseno
            similarity = self._cosine_similarity(
                doc_embedding, 
                template['embedding']
            )
            
            if similarity > best_score:
                best_score = similarity
                best_template = template
        
        # Determinar si cumple el umbral
        if best_score >= min_confidence:
            print(f"✅ Template detectado: '{best_template['nombre']}' (confianza: {best_score:.2%})")
            return {
                'template': best_template,
                'confidence': float(best_score),
                'method': 'embedding'
            }
        else:
            print(f"⚠️ No se encontró template con confianza suficiente (mejor: {best_score:.2%})")
            return {
                'template': None,
                'confidence': float(best_score),
                'method': 'none'
            }
    
    def _ensure_template_embeddings(self):
        """Genera embeddings para plantillas que no los tienen"""
        for template in self.templates_cache:
            if template['embedding'] is None:
                # Generar embedding basado en nombre + descripción
                text = f"{template['nombre']} {template['descripcion']}"
                template['embedding'] = self.generate_embedding(text)
                print(f"🔧 Embedding generado para '{template['nombre']}'")
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calcula similitud coseno entre dos vectores
        
        Returns:
            float entre 0 y 1 (1 = idénticos)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        
        # Normalizar a rango [0, 1]
        # Cosine similarity está en [-1, 1], pero para textos similares suele ser [0, 1]
        return max(0.0, min(1.0, similarity))
    
    def update_template_embedding(self, template_id: int, embedding: np.ndarray):
        """
        Actualiza el embedding de una plantilla en la BD
        
        Args:
            template_id: ID de la plantilla
            embedding: Nuevo embedding (numpy array)
        """
        try:
            from models import db
            from sqlalchemy import text
            import json
            
            # Convertir numpy array a lista para JSONB
            embedding_list = embedding.tolist()
            
            # Convertir a JSON string para PostgreSQL JSONB
            embedding_json = json.dumps(embedding_list)
            
            # Usar CAST() en lugar de :: para evitar conflicto con parámetros
            query = text("""
            UPDATE document_templates
            SET embedding = CAST(:embedding AS jsonb), updated_at = CURRENT_TIMESTAMP
            WHERE id = :template_id
            """)
            
            db.session.execute(query, {'embedding': embedding_json, 'template_id': template_id})
            db.session.commit()
            
            print(f"✅ Embedding actualizado para template #{template_id}")
            
        except Exception as e:
            print(f"❌ Error actualizando embedding: {e}")
            import traceback
            traceback.print_exc()
    
    def clear_cache(self):
        """Limpia el caché de plantillas (útil después de agregar nuevas)"""
        self.templates_cache = None
        self.embeddings_cache = None
        print("🔄 Caché de plantillas limpiado")


# Instancia global (singleton)
_matcher_instance = None

def get_template_matcher() -> TemplateMatcher:
    """
    Obtiene instancia singleton del TemplateMatcher
    
    Returns:
        TemplateMatcher instance
    """
    global _matcher_instance
    
    if _matcher_instance is None:
        _matcher_instance = TemplateMatcher()
    
    return _matcher_instance
