"""
AuroHear - Professional Hearing Asymmetry Screening Platform
Main Flask application entry point.
"""

import os
import logging
from flask import Flask

from backend.config import config
from backend.database import init_db, init_supabase, create_tables
from backend.models import User, TestFeedback, TestNLPInsights, ScreeningSessions
from backend.utils.helpers import run_migrations, create_db_command

logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """Application factory pattern for Flask app creation"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'production')  # Default to production
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize database
    db = init_db(app)
    
    # Initialize Supabase
    init_supabase()
    
    # Register blueprints
    from backend.routes.main import main_bp
    from backend.routes.auth import auth_bp
    from backend.routes.test import test_bp
    from backend.routes.feedback import feedback_bp
    from backend.routes.nlp import nlp_bp
    from backend.routes.user import user_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(test_bp, url_prefix='/test')
    app.register_blueprint(feedback_bp, url_prefix='/feedback')
    app.register_blueprint(nlp_bp, url_prefix='/nlp')
    app.register_blueprint(user_bp, url_prefix='/user')
    
    # Legacy routes for compatibility
    from backend.routes.auth import register
    from backend.routes.test import start_test as legacy_start_test, submit_response as legacy_submit_response, next_test as legacy_next_test, generate_tone as legacy_generate_tone
    from backend.routes.feedback import submit_feedback as legacy_submit_feedback
    from backend.routes.test import save_results as legacy_save_results
    
    # Register legacy routes at root level for backward compatibility
    app.add_url_rule('/register', 'register', register, methods=['POST'])
    app.add_url_rule('/start_test', 'start_test', legacy_start_test, methods=['POST'])
    app.add_url_rule('/submit_response', 'submit_response', legacy_submit_response, methods=['POST'])
    app.add_url_rule('/next_test', 'next_test', legacy_next_test, methods=['GET'])
    app.add_url_rule('/tone', 'tone', legacy_generate_tone, methods=['GET'])
    app.add_url_rule('/submit_feedback', 'submit_feedback', legacy_submit_feedback, methods=['POST'])
    app.add_url_rule('/save_results', 'save_results', legacy_save_results, methods=['POST'])
    
    # Create tables and run migrations
    with app.app_context():
        try:
            create_tables(app)
            run_migrations()
        except Exception as e:
            logger.error(f"Database setup failed: {e}")
            # Continue anyway for development
    
    # Add CLI commands
    app.cli.add_command(app.cli.command("create-db")(create_db_command))
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)