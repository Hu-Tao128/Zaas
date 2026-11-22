from flask import Flask
from flask_migrate import Migrate
from flask_cors import CORS
from app.extensions import db, login_manager, init_supabase
from app.auth import auth_bp
from app.auth.firebase_service import init_firebase_app
from app.catalogo import catalogo_bp
from app.contratos import contratos_bp
from app.contratos.api import contratos_api_bp
from app.pagos import pagos_bp
from app.pagos.api import pagos_api_bp
from app.comunicacion import comunicacion_bp
from app.comunicacion.api import comunicacion_api
from app.routes import iot_bp
from app.supabase_api import supabase_bp


def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        from config import Config
        config_class = Config
    app.config.from_object(config_class)

    # Orígenes permitidos por CORS. Se configuran por entorno (CORS_ORIGINS)
    # para poder desplegar en Coolify sin tocar el código.
    origenes_cors = app.config.get('CORS_ORIGINS') or ['http://localhost:3000']
    CORS(
        app,
        resources={r"/*": {"origins": origenes_cors}},
        supports_credentials=True
    )

    # Extensiones
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'

    # Inicializar Supabase
    init_supabase(app)

    # Inicializar Firebase Auth (archivo en disco o JSON por variable de entorno)
    init_firebase_app(
        app.config.get('FIREBASE_KEY_PATH', ''),
        app.config.get('FIREBASE_CREDENTIALS_JSON'),
    )

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogo_bp)
    app.register_blueprint(contratos_bp)
    app.register_blueprint(contratos_api_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(pagos_api_bp)
    # Alias para compatibilidad con la convención /api/<modulo>.
    app.register_blueprint(pagos_api_bp, url_prefix='/api/pagos', name='pagos_api_alt')
    app.register_blueprint(comunicacion_bp)
    app.register_blueprint(comunicacion_api)
    app.register_blueprint(iot_bp)
    app.register_blueprint(supabase_bp)

    # Contexto para login_manager
    from app.auth.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    with app.app_context():
        from app import models  # noqa: F401  # Registra los modelos IoT/ECBD.
        db.create_all()
        # Garantiza que existan las plantillas base de cada tipo de contrato.
        from app.contratos.plantillas import ensure_plantillas
        ensure_plantillas()

    return app
