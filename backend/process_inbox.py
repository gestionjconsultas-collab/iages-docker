import sys
import os
import json

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models_dehu import NotificacionDehu
from models import Empresa
import importlib
import logging

logging.getLogger("iages").setLevel(logging.CRITICAL)
logging.getLogger("celery_worker").setLevel(logging.CRITICAL)
logging.getLogger("async_runner").setLevel(logging.CRITICAL)

try:
    from tasks import trigger_dehu_processing
except ImportError:
    trigger_dehu_processing = None

results = {
    "assigned": [],
    "celery_queued": [],
    "errors": []
}

with app.app_context():
    inbox_notifs = NotificacionDehu.query.filter(
        NotificacionDehu.file_path.ilike('%__INBOX_NO_CLASIFICADOS%')
    ).all()
    
    no_empresa_notifs = NotificacionDehu.query.filter(
        NotificacionDehu.empresa_id.is_(None),
        NotificacionDehu.nif_titular.isnot(None),
        NotificacionDehu.nif_titular != ''
    ).all()
    
    # Merge unique
    all_to_process = {n.id: n for n in inbox_notifs + no_empresa_notifs}.values()
    
    for n in all_to_process:
        # 1. Intentar asignar empresa si no la tiene
        if not n.empresa_id and n.nif_titular:
            emp = Empresa.query.filter_by(nif=n.nif_titular.strip()).first()
            if emp:
                n.empresa_id = emp.id
                results["assigned"].append({"id": n.id, "ref": n.referencia, "empresa_id": emp.id, "empresa_nombre": emp.nombre})
            else:
                results["errors"].append({"id": n.id, "error": f"No empresa para NIF {n.nif_titular}"})
        
        # 2. Enviar a procesar si tiene ruta e ID de empresa validos (como las que acabamos de agrupar en INBOX)
        if getattr(n, 'empresa_id', None) and n.file_path and os.path.exists(n.file_path):
            if trigger_dehu_processing:
                try:
                    task = trigger_dehu_processing.delay(n.empresa_id, n.file_path, str(n.id), False)
                    results["celery_queued"].append({"id": n.id, "ref": n.referencia, "task_id": str(task.id)})
                except Exception as e:
                    results["errors"].append({"id": n.id, "error": f"Celery error: {str(e)}"})
            else:
                 results["errors"].append({"id": n.id, "error": "No trigger_dehu_processing available"})
                
    db.session.commit()

with open("process_inbox_report.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4)
    
os._exit(0)
