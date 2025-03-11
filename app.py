import os
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text, or_
from flask_login import LoginManager
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from dotenv import load_dotenv
import logging
import atexit
import secrets
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('uptime-monitor')

# Load environment variables
load_dotenv()

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
    enabled=os.environ.get('ENABLE_RATE_LIMITING', 'True').lower() == 'true'
)

# Criar o scheduler como variável global, mas inicializar apenas uma vez
scheduler = None

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI', 'sqlite:///uptime.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Otimizações de performance para SQLite
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        # Usar parameters mais simples que funcionem bem
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {
                'timeout': 30,
                'check_same_thread': False
            }
        }
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    
    # Configure LoginManager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Aplicar otimizações SQLite com pragmas mais simples
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        with app.app_context():
            db.session.execute(text("PRAGMA journal_mode=WAL"))
            db.session.execute(text("PRAGMA synchronous=NORMAL"))
            db.session.execute(text("PRAGMA temp_store=memory"))
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()
    
    # Register Blueprints
    with app.app_context():
        from routes import main, auth, api, probes, jobs
        
        app.register_blueprint(main.main_blueprint)
        app.register_blueprint(auth.auth_blueprint)
        app.register_blueprint(api.api_blueprint)
        app.register_blueprint(probes.probes_blueprint)
        app.register_blueprint(jobs.jobs_blueprint)

        @login_manager.user_loader
        def load_user(user_id):
            from models import User
            return User.query.get(int(user_id))
    
    # Initialize database if it doesn't exist
    with app.app_context():
        # Adicionar as colunas faltantes na tabela users
        try:
            db.session.execute(text("""
                ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0;
            """))
            db.session.commit()
            app.logger.info('Added failed_login_attempts column to users table')
        except Exception as e:
            db.session.rollback()
            app.logger.info(f'Column might already exist: {str(e)}')
        
        try:
            db.session.execute(text("""
                ALTER TABLE users ADD COLUMN last_failed_login TIMESTAMP;
            """))
            db.session.commit()
            app.logger.info('Added last_failed_login column to users table')
        except Exception as e:
            db.session.rollback()
            app.logger.info(f'Column might already exist: {str(e)}')
        
        try:
            db.session.execute(text("""
                ALTER TABLE users ADD COLUMN locked_until TIMESTAMP;
            """))
            db.session.commit()
            app.logger.info('Added locked_until column to users table')
        except Exception as e:
            db.session.rollback()
            app.logger.info(f'Column might already exist: {str(e)}')
        
        # Create tables if they don't exist
        db.create_all()
        
        # Create admin user if not exists - remove this part since we're using init_db.py
        # from models import User
        # if not User.query.filter(db.or_(User.username == 'admin', User.email == 'admin@example.com')).first():
        #     admin_user = User(username='admin', email='admin@example.com', is_admin=True)
        #     admin_user.set_password('admin')
        #     db.session.add(admin_user)
        #     db.session.commit()
        #     app.logger.info('Admin user created with username: admin and password: admin')
    
    # Error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    # Inicializa o scheduler uma única vez na aplicação principal
    global scheduler
    if scheduler is None or not scheduler.running:
        scheduler = BackgroundScheduler()
        start_scheduler(app)
        # Garantir que o scheduler seja encerrado adequadamente
        atexit.register(lambda: shutdown_scheduler())
            
    return app

def shutdown_scheduler():
    """Shut down the scheduler safely"""
    global scheduler
    if scheduler and scheduler.running:
        try:
            logger.info("Shutting down scheduler...")
            scheduler.shutdown(wait=False)
            logger.info("Scheduler shutdown complete.")
        except:
            pass

def start_scheduler(app):
    """Start the scheduler for periodic tasks"""
    global scheduler
    if not scheduler or not scheduler.running:
        return
    
    # Criar uma função wrapper que executa dentro do contexto da aplicação
    # e com menos frequência (para reduzir o impacto no sistema)
    def cleanup_logs_job():
        try:
            with app.app_context():
                from utils.log_cleaner import cleanup_old_logs
                cleanup_old_logs()
        except Exception as e:
            logger.error(f"Error in cleanup_logs_job: {str(e)}")
    
    # Agendar para executar uma vez por dia, mas não imediatamente
    # para evitar sobrecarga no início da aplicação
    scheduler.add_job(
        cleanup_logs_job, 
        'interval', 
        hours=24, 
        id='cleanup_logs',
        replace_existing=True,
        max_instances=1,  # Limitar a uma instância para evitar execuções paralelas
        coalesce=True     # Combinar execuções perdidas
    )
    
    # Start the scheduler
    try:
        scheduler.start()
        logger.info("Log cleanup scheduler started. Logs older than 24 hours will be automatically removed once a day.")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

if __name__ == '__main__':
    app = create_app()
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
