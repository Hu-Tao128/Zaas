from flask import Flask
from flask_migrate import Migrate
from app.extensions import db, login_manager, init_supabase
from app.auth import auth_bp
from app.auth.firebase_service import init_firebase_app
from app.catalogo import catalogo_bp
from app.contratos import contratos_bp
from app.pagos import pagos_bp
from app.comunicacion import comunicacion_bp
from app.supabase_api import supabase_bp


def create_app(config_class=None):
    app = Flask(__name__)
    if config_class is None:
        from config import Config
        config_class = Config
    app.config.from_object(config_class)

    # Extensiones
    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Debes iniciar sesión para acceder a esta página.'

    # Inicializar Supabase
    init_supabase(app)

    # Inicializar Firebase Auth
    init_firebase_app(app.config.get('FIREBASE_KEY_PATH', ''))

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(catalogo_bp)
    app.register_blueprint(contratos_bp)
    app.register_blueprint(pagos_bp)
    app.register_blueprint(comunicacion_bp)
    app.register_blueprint(supabase_bp)

    # Contexto para login_manager
    from app.auth.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    with app.app_context():
        db.create_all()

    return app
