"""
Configuration module for AuroHear backend.
Handles environment variables, database configuration, and app settings.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Config:
    """Base configuration class"""
    
    # Database configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
    
    # Handle database URL configuration - prioritize PostgreSQL for production
    if not DATABASE_URL or '://' not in DATABASE_URL:
        logger.warning(f"DATABASE_URL is invalid or not set: '{DATABASE_URL}'. Using SQLite fallback.")
        DATABASE_URL = 'sqlite:///users.db'
    else:
        # Fix: SQLAlchemy 1.4+ requires postgresql://, not postgres://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        logger.info(f"Using database URL: {DATABASE_URL[:30]}...")
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Supabase configuration
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    
    # Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Audio processing configuration
    SAMPLE_RATE = 44100
    AUDIO_DURATION = 0.35
    REFERENCE_DB = 50


class DevelopmentConfig(Config):
    """Development configuration - can use SQLite for local testing"""
    DEBUG = True
    # Use environment DATABASE_URL or fallback to SQLite
    pass


class ProductionConfig(Config):
    """Production configuration - uses PostgreSQL/Supabase"""
    DEBUG = False
    # Use environment DATABASE_URL (should be PostgreSQL)
    pass


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}