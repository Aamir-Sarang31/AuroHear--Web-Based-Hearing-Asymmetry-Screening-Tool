"""
Helper utilities for AuroHear application.
Contains database migration and other utility functions.
"""

import logging
from flask import current_app
from backend.database import db
from backend.models import User, TestFeedback, ScreeningSessions, TestNLPInsights

logger = logging.getLogger(__name__)


def run_migrations():
    """Database migration for both SQLite and PostgreSQL"""
    try:
        inspector = db.inspect(db.engine)
        
        # Check if user table exists, if not create all tables
        if not inspector.has_table('user'):
            logger.info("Creating all database tables")
            db.create_all()
            return
        
        columns = [c['name'] for c in inspector.get_columns('user')]
        is_postgres = 'postgresql' in str(db.engine.url)
        
        # Add supabase_id column if missing
        if 'supabase_id' not in columns:
            logger.info("Migrating: Adding supabase_id column to User table")
            with db.engine.connect() as conn:
                if is_postgres:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN supabase_id VARCHAR(36) UNIQUE'))
                else:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN supabase_id TEXT UNIQUE"))
                conn.commit()
        
        # Add auth_type column if missing
        if 'auth_type' not in columns:
            logger.info("Migrating: Adding auth_type column to User table")
            with db.engine.connect() as conn:
                if is_postgres:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN auth_type VARCHAR(20) DEFAULT \'guest\''))
                else:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN auth_type TEXT DEFAULT 'guest'"))
                conn.commit()
        
        # Add timestamp columns if missing
        if 'created_at' not in columns:
            logger.info("Migrating: Adding timestamp columns to User table")
            with db.engine.connect() as conn:
                if is_postgres:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP'))
                else:
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                    conn.execute(db.text("ALTER TABLE user ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()
                
        # Create new tables if they don't exist
        if not inspector.has_table('screening_sessions'):
            logger.info("Creating screening_sessions table")
            ScreeningSessions.__table__.create(db.engine)
        
        if not inspector.has_table('test_feedback'):
            logger.info("Creating test_feedback table")
            TestFeedback.__table__.create(db.engine)
            
        if not inspector.has_table('test_nlp_insights'):
            logger.info("Creating test_nlp_insights table")
            TestNLPInsights.__table__.create(db.engine)
            
        logger.info("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        # If migration fails, try to create all tables
        try:
            logger.info("Migration failed, attempting to create all tables")
            db.create_all()
        except Exception as create_error:
            logger.error(f"Table creation also failed: {create_error}")
            raise


def create_db_command():
    """CLI command to create database tables"""
    with current_app.app_context():
        db.create_all()
    print("Database tables created successfully.")


def validate_user_access(user_id, require_authenticated=False):
    """
    Validate user access and return user object.
    
    Args:
        user_id: User ID to validate
        require_authenticated: Whether to require authenticated user
    
    Returns:
        User object if valid, None otherwise
    
    Raises:
        ValueError: If user not found or access denied
    """
    if not user_id:
        raise ValueError("User ID required")
    
    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")
    
    if require_authenticated and user.auth_type != 'authenticated':
        raise ValueError("Access restricted to authenticated users")
    
    return user


def format_session_data(session_results):
    """
    Format screening session results for API response.
    
    Args:
        session_results: List of ScreeningSessions objects
    
    Returns:
        dict: Formatted session data
    """
    if not session_results:
        return None
    
    # Group by session_id
    sessions_dict = {}
    for result in session_results:
        session_id = result.session_id
        if session_id not in sessions_dict:
            sessions_dict[session_id] = {
                'session_id': session_id,
                'timestamp': result.timestamp,
                'results': []
            }
        sessions_dict[session_id]['results'].append(result)
    
    # Convert to list and sort by timestamp
    sessions_list = list(sessions_dict.values())
    sessions_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return sessions_list


def calculate_test_completeness(thresholds):
    """
    Calculate test completeness metrics.
    
    Args:
        thresholds: Dict with 'left' and 'right' ear data
    
    Returns:
        dict: Completeness metrics
    """
    expected_frequencies = [250, 500, 1000, 2000, 4000, 5000]
    
    left_count = len([f for f in expected_frequencies if f in thresholds.get('left', {})])
    right_count = len([f for f in expected_frequencies if f in thresholds.get('right', {})])
    total_expected = len(expected_frequencies) * 2
    total_recorded = left_count + right_count
    
    return {
        'left': left_count,
        'right': right_count,
        'total_expected': total_expected,
        'total_recorded': total_recorded,
        'is_complete': total_recorded >= total_expected,
        'completion_percentage': (total_recorded / total_expected) * 100 if total_expected > 0 else 0
    }


def sanitize_user_input(text, max_length=1000):
    """
    Sanitize user input text.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length
    
    Returns:
        str: Sanitized text
    
    Raises:
        ValueError: If text is invalid
    """
    if not text or not isinstance(text, str):
        raise ValueError("Text input required")
    
    text = text.strip()
    
    if len(text) < 5:
        raise ValueError("Text must be at least 5 characters")
    
    if len(text) > max_length:
        raise ValueError(f"Text too long (max {max_length} characters)")
    
    return text


def log_user_action(user_id, action, details=None):
    """
    Log user actions for debugging and analytics.
    
    Args:
        user_id: User ID
        action: Action description
        details: Optional additional details
    """
    user_type = "unknown"
    try:
        user = User.query.get(user_id)
        if user:
            user_type = user.auth_type
    except:
        pass
    
    log_message = f"User action: user_id={user_id}, type={user_type}, action={action}"
    if details:
        log_message += f", details={details}"
    
    logger.info(log_message)