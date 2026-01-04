"""
NLP routes for AuroHear application.
Handles NLP insights retrieval and reliability metrics.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

nlp_bp = Blueprint('nlp', __name__)


@nlp_bp.route('/insights/<session_id>', methods=['GET'])
def get_nlp_insights(session_id):
    """
    Get NLP insights for a specific test session.
    
    Path Parameters:
    - session_id: UUID of the test session
    
    Returns:
    - NLP analysis results for the session
    """
    try:
        # Validate session_id format
        try:
            uuid.UUID(session_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid session ID format'}), 400
        
        # Import NLP module
        try:
            from backend.nlp_engine.store_results import get_test_insights
        except ImportError:
            return jsonify({'error': 'NLP engine not available'}), 503
        
        # Retrieve insights
        insights = get_test_insights(session_id)
        
        if not insights:
            return jsonify({
                'session_id': session_id,
                'insights': [],
                'message': 'No NLP insights found for this session'
            })
        
        # Return insights with metadata
        return jsonify({
            'session_id': session_id,
            'insights': insights,
            'count': len(insights),
            'latest_analysis': insights[0].get('created_at') if insights else None
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve NLP insights'}), 500


@nlp_bp.route('/reliability', methods=['GET'])
def get_nlp_reliability():
    """
    Get platform reliability metrics based on NLP analysis.
    
    Query Parameters:
    - days (optional): Number of days to analyze (default: 7, max: 30)
    
    Returns:
    - Reliability metrics and sentiment analysis summary
    """
    try:
        days = min(int(request.args.get('days', 7)), 30)  # Cap at 30 days
        
        # Import NLP module
        try:
            from backend.nlp_engine.store_results import NLPResultsStorage
        except ImportError:
            return jsonify({'error': 'NLP engine not available'}), 503
        
        storage = NLPResultsStorage()
        
        # Get reliability metrics
        reliability = storage.get_reliability_metrics(limit_days=days)
        
        # Get sentiment summary
        sentiment_summary = storage.get_sentiment_summary(limit_days=days)
        
        return jsonify({
            'period_days': days,
            'reliability': reliability,
            'sentiment_summary': sentiment_summary,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to retrieve reliability metrics'}), 500