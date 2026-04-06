# backend/config_swagger.py
"""
Configuración de documentación API con Swagger
"""

from flask_restx import Api, Resource, fields
from flask import Blueprint


def init_swagger(app):
    """
    Inicializa Swagger UI para documentación de API
    
    Documentación disponible en: /api/docs
    
    Args:
        app: Instancia de Flask
    
    Returns:
        Api instance
    """
    # Crear blueprint para API
    api_bp = Blueprint('api_docs', __name__, url_prefix='/api')
    
    # Configurar API
    api = Api(
        api_bp,
        version='1.0',
        title='IAGES API',
        description='API de gestión documental para gestorías',
        doc='/docs',  # Swagger UI en /api/docs
        prefix='/v1',
        
        # Configuración de seguridad
        authorizations={
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'JWT Token. Formato: Bearer <token>'
            }
        },
        security='Bearer'
    )
    
    # Registrar blueprint
    app.register_blueprint(api_bp)
    
    # ==========================================
    # NAMESPACES (GRUPOS DE ENDPOINTS)
    # ==========================================
    
    auth_ns = api.namespace('auth', description='Autenticación y autorización')
    docs_ns = api.namespace('documentos', description='Gestión de documentos')
    empresas_ns = api.namespace('empresas', description='Gestión de empresas')
    saltra_ns = api.namespace('saltra', description='Integración con Saltra')
    audit_ns = api.namespace('auditoria', description='Logs de auditoría')
    
    # ==========================================
    # MODELOS DE DATOS
    # ==========================================
    
    # Modelo de Login
    login_model = api.model('Login', {
        'email': fields.String(required=True, description='Email del usuario'),
        'password': fields.String(required=True, description='Contraseña'),
    })
    
    # Modelo de Usuario
    user_model = api.model('User', {
        'id': fields.Integer(description='ID del usuario'),
        'nombre': fields.String(description='Nombre completo'),
        'email': fields.String(description='Email'),
        'gestoria_id': fields.Integer(description='ID de la gestoría'),
        'departamento': fields.String(description='Departamento'),
        'is_admin': fields.Boolean(description='Es administrador'),
    })
    
    # Modelo de Documento
    documento_model = api.model('Documento', {
        'id': fields.Integer(description='ID del documento'),
        'nombre_archivo': fields.String(description='Nombre del archivo'),
        'categoria': fields.String(description='Categoría del documento'),
        'empresa_id': fields.Integer(description='ID de la empresa'),
        'fecha_subida': fields.DateTime(description='Fecha de subida'),
        'procesado': fields.Boolean(description='Está procesado'),
    })
    
    # Modelo de Empresa
    empresa_model = api.model('Empresa', {
        'id': fields.Integer(description='ID de la empresa'),
        'nombre': fields.String(required=True, description='Nombre de la empresa'),
        'nif': fields.String(required=True, description='NIF/CIF'),
        'email': fields.String(description='Email de contacto'),
        'telefono': fields.String(description='Teléfono'),
    })
    
    # Modelo de Notificación Saltra
    notificacion_model = api.model('NotificacionSaltra', {
        'id': fields.Integer(description='ID de la notificación'),
        'sent_reference': fields.String(description='Referencia de envío'),
        'identifier': fields.String(description='Identificador'),
        'state': fields.String(description='Estado (ACEPTADA, PENDIENTE, etc)'),
        'fecha_recepcion': fields.DateTime(description='Fecha de recepción'),
    })
    
    # ==========================================
    # EJEMPLOS DE ENDPOINTS DOCUMENTADOS
    # ==========================================
    
    @auth_ns.route('/login')
    class Login(Resource):
        @auth_ns.doc('login')
        @auth_ns.expect(login_model)
        @auth_ns.marshal_with(user_model)
        def post(self):
            '''Iniciar sesión'''
            pass
    
    @docs_ns.route('/')
    class DocumentoList(Resource):
        @docs_ns.doc('list_documentos')
        @docs_ns.marshal_list_with(documento_model)
        @docs_ns.param('page', 'Número de página', type=int, default=1)
        @docs_ns.param('per_page', 'Documentos por página', type=int, default=50)
        @docs_ns.param('categoria', 'Filtrar por categoría', type=str)
        def get(self):
            '''Listar documentos'''
            pass
    
    @empresas_ns.route('/')
    class EmpresaList(Resource):
        @empresas_ns.doc('list_empresas')
        @empresas_ns.marshal_list_with(empresa_model)
        def get(self):
            '''Listar empresas'''
            pass
        
        @empresas_ns.doc('create_empresa')
        @empresas_ns.expect(empresa_model)
        @empresas_ns.marshal_with(empresa_model, code=201)
        def post(self):
            '''Crear nueva empresa'''
            pass
    
    @saltra_ns.route('/notificaciones')
    class SaltraNotificaciones(Resource):
        @saltra_ns.doc('list_notificaciones')
        @saltra_ns.marshal_list_with(notificacion_model)
        @saltra_ns.param('page', 'Número de página', type=int, default=1)
        @saltra_ns.param('estado', 'Filtrar por estado', type=str)
        def get(self):
            '''Listar notificaciones de Saltra'''
            pass
    
    app.logger.info("✅ Swagger UI inicializado en /api/docs")
    
    return api


# ==========================================
# INSTRUCCIONES DE USO
# ==========================================

"""
Para usar Swagger en tu aplicación:

1. Instalar dependencias:
   pip install flask-restx

2. En app.py, importar y inicializar:
   from config_swagger import init_swagger
   
   api = init_swagger(app)

3. Acceder a la documentación:
   http://localhost:5000/api/docs

4. Para documentar un endpoint existente:
   
   from flask_restx import Resource, fields
   from config_swagger import api
   
   # Definir namespace
   docs_ns = api.namespace('documentos', description='Documentos')
   
   # Definir modelo
   doc_model = api.model('Documento', {
       'id': fields.Integer(),
       'nombre': fields.String(required=True)
   })
   
   # Documentar endpoint
   @docs_ns.route('/<int:id>')
   class DocumentoResource(Resource):
       @docs_ns.marshal_with(doc_model)
       def get(self, id):
           '''Obtener documento por ID'''
           # tu código aquí
           pass

5. Autenticación en Swagger:
   - Click en "Authorize" en la UI
   - Ingresar: Bearer <tu_token_jwt>
   - Ahora puedes probar endpoints protegidos
"""
