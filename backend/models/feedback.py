"""
Feedback model for AuroHear backend.
"""

from datetime import datetime, timedelta
from backend.database import db


class TestFeedback(db.Model):
    """
    Stores user feedback about the testing experience.
    Separate from audiometric data for privacy and analytics.
    Supports both authenticated and anonymous feedback.
    """
    __tablename__ = 'test_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, index=True)  # Links to test session
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable for guest feedback
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    
    # Rating fields (1-5 scale)
    test_clarity_rating = db.Column(db.Integer, nullable=True)  # How clear were the instructions?
    audio_comfort_rating = db.Column(db.Integer, nullable=True)  # Was the audio comfortable?
    ease_of_use_rating = db.Column(db.Integer, nullable=True)  # How easy was the test to use?
    
    # Required text feedback (for NLP analysis)
    suggestions_text = db.Column(db.Text, nullable=False)  # "Any suggestions or issues you faced?" - Required for NLP
    
    # Metadata
    user_agent = db.Column(db.String(500), nullable=True)  # Browser info for technical issues
    
    # Relationship to user (optional)
    user = db.relationship('User', backref=db.backref('feedback_entries', lazy=True))
    
    def to_dict(self):
        """Convert feedback to dictionary for JSON responses"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'test_clarity_rating': self.test_clarity_rating,
            'audio_comfort_rating': self.audio_comfort_rating,
            'ease_of_use_rating': self.ease_of_use_rating,
            'suggestions_text': self.suggestions_text
        }
    
    @classmethod
    def get_feedback_summary(cls, limit_days=30):
        """Get aggregated feedback statistics for platform improvement"""
        cutoff_date = datetime.now() - timedelta(days=limit_days)
        
        feedback_entries = cls.query.filter(cls.timestamp >= cutoff_date).all()
        
        if not feedback_entries:
            return None
        
        # Calculate averages for each rating category
        clarity_ratings = [f.test_clarity_rating for f in feedback_entries if f.test_clarity_rating]
        comfort_ratings = [f.audio_comfort_rating for f in feedback_entries if f.audio_comfort_rating]
        ease_ratings = [f.ease_of_use_rating for f in feedback_entries if f.ease_of_use_rating]
        
        return {
            'period_days': limit_days,
            'total_feedback_count': len(feedback_entries),
            'average_ratings': {
                'test_clarity': sum(clarity_ratings) / len(clarity_ratings) if clarity_ratings else None,
                'audio_comfort': sum(comfort_ratings) / len(comfort_ratings) if comfort_ratings else None,
                'ease_of_use': sum(ease_ratings) / len(ease_ratings) if ease_ratings else None
            },
            'response_counts': {
                'test_clarity': len(clarity_ratings),
                'audio_comfort': len(comfort_ratings),
                'ease_of_use': len(ease_ratings),
                'with_suggestions': len([f for f in feedback_entries if f.suggestions_text])
            }
        }