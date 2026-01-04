"""
User model for AuroHear backend.
"""

from backend.database import db


class User(db.Model):
    """
    User model for storing user profiles and authentication data.
    Supports both authenticated users (via Supabase) and guest sessions.
    """
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    age_group = db.Column(db.String(50))
    gender = db.Column(db.String(50))
    
    # Link to Supabase Auth User ID (UUID string)
    supabase_id = db.Column(db.String(36), unique=True, nullable=True) 
    
    # Authentication type: 'authenticated' or 'guest'
    auth_type = db.Column(db.String(20), default='guest', nullable=False)
    
    # Timestamps for tracking
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    # Aggregated test results
    left_avg = db.Column(db.Float, nullable=True)
    right_avg = db.Column(db.Float, nullable=True)
    dissimilarity = db.Column(db.Float, nullable=True)
    test_state = db.Column(db.Text, nullable=True)
    
    def to_dict(self):
        """Convert user to dictionary for JSON responses"""
        return {
            'id': self.id,
            'name': self.name,
            'surname': self.surname,
            'age_group': self.age_group,
            'gender': self.gender,
            'auth_type': self.auth_type,
            'supabase_id': self.supabase_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }