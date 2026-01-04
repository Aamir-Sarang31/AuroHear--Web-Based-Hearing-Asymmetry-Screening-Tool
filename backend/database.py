"""
Database initialization and management for AuroHear backend.
"""

import logging
from flask_sqlalchemy import SQLAlchemy

logger = logging.getLogger(__name__)

# Initialize SQLAlchemy
db = SQLAlchemy()


def init_db(app):
    """Initialize database with Flask app"""
    try:
        db.init_app(app)
        logger.info("Database initialized successfully")
        return db
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_tables(app):
    """Create all database tables"""
    with app.app_context():
        try:
            # Import models to ensure they're registered
            from backend.models import User, TestFeedback, TestNLPInsights, ScreeningSessions
            
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            
            # For development/testing, try creating a local SQLite database as fallback
            if 'postgresql' in str(e).lower() or 'postgres' in str(e).lower():
                logger.warning("PostgreSQL connection failed. This might be expected in development.")
                logger.info("For production, ensure DATABASE_URL points to a valid PostgreSQL database.")
                
                # Only fallback to SQLite if explicitly in development mode
                if app.config.get('DEBUG', False):
                    logger.info("Debug mode detected - attempting SQLite fallback")
                    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
                    try:
                        # Re-initialize with SQLite
                        db.init_app(app)
                        db.create_all()
                        logger.info("SQLite database created successfully as development fallback")
                    except Exception as sqlite_error:
                        logger.error(f"SQLite fallback also failed: {sqlite_error}")
                        raise
                else:
                    logger.error("Production mode - PostgreSQL connection required")
                    raise
            else:
                raise


# Supabase client initialization
supabase = None

def init_supabase():
    """Initialize Supabase client"""
    global supabase
    
    from backend.config import Config
    
    try:
        if Config.SUPABASE_URL and Config.SUPABASE_KEY:
            from supabase import create_client
            supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            logger.info("Supabase client initialized")
        else:
            logger.info("SUPABASE_URL or SUPABASE_KEY not set; Supabase client disabled")
    except Exception as e:
        logger.warning(f"Supabase initialization failed (non-fatal): {e}")
    
    return supabase