import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from config import Config

# Initialisation des extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
login_manager.login_message_category = 'info'
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Création du dossier d'upload s'il n'existe pas
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Liaison des extensions à l'application
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Enregistrement des blueprints
    from app.routes.main import bp as main_bp
    app.register_blueprint(main_bp)
    
    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from app.routes.admin import bp as admin_bp
    app.register_blueprint(admin_bp)
    
    from app.routes.supervisor import bp as supervisor_bp
    app.register_blueprint(supervisor_bp)

    @app.context_processor
    def inject_user_mode():
        from flask import session
        from flask_login import current_user
        if current_user.is_authenticated and current_user.is_admin():
            mode = session.get('active_mode', 'admin')
            return {
                'can_switch_mode': True,
                'active_mode': mode,
                'is_admin_mode': mode == 'admin',
                'is_supervisor_mode': mode == 'supervisor'
            }
        return {
            'can_switch_mode': False,
            'active_mode': current_user.role if current_user.is_authenticated else None,
            'is_admin_mode': False,
            'is_supervisor_mode': current_user.role == 'supervisor' if current_user.is_authenticated else False
        }

    return app
