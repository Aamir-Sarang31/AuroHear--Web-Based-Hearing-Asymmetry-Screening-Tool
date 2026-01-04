"""
Screening Sessions model for AuroHear backend.
"""

from backend.database import db


class ScreeningSessions(db.Model):
    """
    Stores individual screening test results for authenticated users only.
    Each row represents one frequency test result.
    Guest sessions are never persisted to maintain privacy.
    
    Table structure matches exact specification:
    - session_id (UUID): Groups related test results
    - user_id (nullable): Links to authenticated user
    - timestamp: When the test was performed
    - ear: 'left' or 'right'
    - frequency_hz: Test frequency (250, 500, 1000, 2000, 4000, 5000)
    - threshold_db: Measured threshold in dB HL
    """
    __tablename__ = 'screening_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, index=True)  # UUID - not unique to allow multiple rows per session
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Nullable as specified
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp(), nullable=False)
    ear = db.Column(db.String(5), nullable=False)  # 'left' or 'right'
    frequency_hz = db.Column(db.Integer, nullable=False)  # Test frequency
    threshold_db = db.Column(db.Float, nullable=False)  # Threshold in dB HL
    
    # Relationship to user
    user = db.relationship('User', backref=db.backref('screening_sessions', lazy=True))
    
    # Composite index for efficient queries
    __table_args__ = (
        db.Index('idx_session_user', 'session_id', 'user_id'),
        db.Index('idx_user_timestamp', 'user_id', 'timestamp'),
    )
    
    def to_dict(self):
        """Convert screening result to dictionary for JSON responses"""
        return {
            'id': self.id,
            'session_id': self.session_id,
            'user_id': self.user_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'ear': self.ear,
            'frequency_hz': self.frequency_hz,
            'threshold_db': self.threshold_db
        }
    
    @classmethod
    def get_sessions_for_user(cls, user_id, limit=50, offset=0):
        """Get all sessions for a user, grouped by session_id"""
        return db.session.query(cls).filter_by(user_id=user_id)\
            .order_by(cls.timestamp.desc())\
            .offset(offset).limit(limit).all()
    
    @classmethod
    def get_session_summary(cls, session_id):
        """Get summary statistics for a specific session"""
        results = cls.query.filter_by(session_id=session_id).all()
        
        if not results:
            return None
        
        # Group by ear
        left_thresholds = [r.threshold_db for r in results if r.ear == 'left']
        right_thresholds = [r.threshold_db for r in results if r.ear == 'right']
        
        summary = {
            'session_id': session_id,
            'timestamp': results[0].timestamp,
            'user_id': results[0].user_id,
            'left_avg': sum(left_thresholds) / len(left_thresholds) if left_thresholds else None,
            'right_avg': sum(right_thresholds) / len(right_thresholds) if right_thresholds else None,
            'frequency_count': len(results),
            'ears_tested': len(set(r.ear for r in results))
        }
        
        # Calculate interaural differences per frequency
        frequencies = set(r.frequency_hz for r in results)
        interaural_differences = {}
        freq_diffs = []
        
        for freq in frequencies:
            left_val = next((r.threshold_db for r in results if r.ear == 'left' and r.frequency_hz == freq), None)
            right_val = next((r.threshold_db for r in results if r.ear == 'right' and r.frequency_hz == freq), None)
            
            if left_val is not None and right_val is not None:
                # Calculate absolute difference (no directional bias)
                abs_diff = abs(left_val - right_val)
                # Calculate signed difference (left - right, for trend analysis)
                signed_diff = left_val - right_val
                
                interaural_differences[freq] = {
                    'left_threshold': left_val,
                    'right_threshold': right_val,
                    'absolute_difference': abs_diff,
                    'signed_difference': signed_diff,  # Positive = left worse, Negative = right worse
                    'frequency_hz': freq
                }
                
                freq_diffs.append(abs_diff)
        
        # Add interaural analysis to summary
        summary['interaural_differences'] = interaural_differences
        summary['dissimilarity'] = max(freq_diffs) if freq_diffs else None
        
        # Calculate additional interaural statistics
        if freq_diffs:
            summary['interaural_stats'] = {
                'max_difference': max(freq_diffs),
                'min_difference': min(freq_diffs),
                'mean_difference': sum(freq_diffs) / len(freq_diffs),
                'frequencies_with_differences': len([d for d in freq_diffs if d > 0]),
                'total_frequencies_compared': len(freq_diffs)
            }
        else:
            summary['interaural_stats'] = None
        
        return summary
    
    @classmethod
    def compute_interaural_differences(cls, thresholds):
        """
        Compute interaural threshold differences from threshold data.
        
        Args:
            thresholds: Dict with 'left' and 'right' keys containing frequency->threshold mappings
            
        Returns:
            Dict containing per-frequency differences and summary statistics
        """
        if not thresholds or 'left' not in thresholds or 'right' not in thresholds:
            return None
        
        left_data = thresholds['left']
        right_data = thresholds['right']
        
        # Find common frequencies
        common_frequencies = set(left_data.keys()) & set(right_data.keys())
        
        if not common_frequencies:
            return None
        
        differences = {}
        abs_diffs = []
        signed_diffs = []
        
        for freq in common_frequencies:
            try:
                freq_int = int(freq)
                left_val = float(left_data[freq])
                right_val = float(right_data[freq])
                
                abs_diff = abs(left_val - right_val)
                signed_diff = left_val - right_val
                
                differences[freq_int] = {
                    'left_threshold': left_val,
                    'right_threshold': right_val,
                    'absolute_difference': abs_diff,
                    'signed_difference': signed_diff,
                    'frequency_hz': freq_int
                }
                
                abs_diffs.append(abs_diff)
                signed_diffs.append(signed_diff)
                
            except (ValueError, TypeError):
                continue
        
        if not abs_diffs:
            return None
        
        return {
            'per_frequency': differences,
            'summary_stats': {
                'max_absolute_difference': max(abs_diffs),
                'min_absolute_difference': min(abs_diffs),
                'mean_absolute_difference': sum(abs_diffs) / len(abs_diffs),
                'max_signed_difference': max(signed_diffs),
                'min_signed_difference': min(signed_diffs),
                'mean_signed_difference': sum(signed_diffs) / len(signed_diffs),
                'frequencies_compared': len(abs_diffs),
                'total_frequencies': len(common_frequencies)
            }
        }