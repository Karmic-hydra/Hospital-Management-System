from flask import Flask
from extensions import db, login_manager
import os

# Main application factory
# This part is tricky - creates and configures the Flask app!
def create_app():
    # Initialize Flask application
    flaskApp = Flask(__name__)
    
    secretKey = os.environ.get('SECRET_KEY')
    if secretKey is None:
        secretKey = 'your-secret-key-here-change-in-production'  # Fallback
    
    flaskApp.config['SECRET_KEY'] = secretKey
    flaskApp.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
    flaskApp.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disable tracking to save memory
    
    # Initialize extensions with app
    db.init_app(flaskApp)
    login_manager.init_app(flaskApp)
    
    # Configure login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Create database tables and setup
    # Debugging is important here !!!!
    with flaskApp.app_context():
        # Import models here to avoid circular imports - this is important!
        import models
        db.create_all()  # Create all tables
        
        # Create admin user if not exists
        from utils import create_admin
        create_admin()  # Setup default data
    
    # Register blueprints - using dict for cleaner organization
    # More human approach than multiple register calls
    blueprintConfig = {}
    
    # Import all blueprints
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.doctor import doctor_bp
    from routes.patient import patient_bp
    from routes.api import api_bp
    
    # Store blueprints with their prefixes
    blueprintConfig['auth'] = {'blueprint': auth_bp, 'prefix': None}
    blueprintConfig['admin'] = {'blueprint': admin_bp, 'prefix': '/admin'}
    blueprintConfig['doctor'] = {'blueprint': doctor_bp, 'prefix': '/doctor'}
    blueprintConfig['patient'] = {'blueprint': patient_bp, 'prefix': '/patient'}
    blueprintConfig['api'] = {'blueprint': api_bp, 'prefix': '/api'}
    
    # Register each blueprint with its prefix
    for bpName, bpConfig in blueprintConfig.items():
        currentBlueprint = bpConfig['blueprint']
        urlPrefix = bpConfig['prefix']
        
        if urlPrefix is not None:
            flaskApp.register_blueprint(currentBlueprint, url_prefix=urlPrefix)
        else:
            flaskApp.register_blueprint(currentBlueprint)
    
    return flaskApp

# Run the application
if __name__ == '__main__':
    # Create app instance
    hospitalApp = create_app()
    
    # Run in debug mode for development
    hospitalApp.run(debug=True)
