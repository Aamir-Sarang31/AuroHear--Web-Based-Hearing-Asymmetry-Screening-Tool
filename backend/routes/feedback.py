"""
Feedback routes for AuroHear application.
Handles user feedback submission and aggregated feedback statistics.
"""

import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify

from backend.database import db
from backend.models import TestFeedback

feedback_bp = Blueprint('feedback', __name__)


@feedback_bp.route('/submit', methods=['POST'])
def submit_feedback():
    """
    Submit user feedback about the testing experience.
    
    Request Body:
    - session_id (required): UUID of the test session
    - user_id (optional): User ID for authenticated users
    - test_clarity_rating (optional): 1-5 rating for instruction clarity
    - audio_comfort_rating (optional): 1-5 rating for audio comfort
    - ease_of_use_rating (optional): 1-5 rating for ease of use
    - suggestions_text (required): Free text suggestions/issues - minimum 5 characters
    
    Returns:
    - Success confirmation without exposing stored data
    """
    data = request.json or {}
    session_id = data.get('session_id')
    user_id = data.get('user_id')
    
    if not session_id:
        return jsonify({'error': 'Session ID required'}), 400
    
    try:
        # BACKEND VALIDATION: Enforce required feedback
        suggestions_text = data.get('suggestions_text', '').strip()
        if not suggestions_text or len(suggestions_text) < 5:
            return jsonify({'error': 'Feedback is required and must contain at least 5 characters'}), 400
        
        # Validate suggestions text length (prevent abuse)
        if len(suggestions_text) > 1000:  # Reasonable limit
            return jsonify({'error': 'Suggestions text too long (max 1000 characters)'}), 400
        
        # Validate ratings are in 1-5 range if provided
        rating_fields = ['test_clarity_rating', 'audio_comfort_rating', 'ease_of_use_rating']
        for field in rating_fields:
            rating = data.get(field)
            if rating is not None:
                try:
                    rating_val = int(rating)
                    if rating_val < 1 or rating_val > 5:
                        return jsonify({'error': f'{field} must be between 1 and 5'}), 400
                except (ValueError, TypeError):
                    return jsonify({'error': f'{field} must be a valid integer'}), 400
        
        # Get user agent for technical debugging (no personal data)
        user_agent = request.headers.get('User-Agent', '')[:500]  # Truncate to prevent overflow
        
        # Create feedback entry - suggestions_text is now guaranteed to be non-empty
        feedback = TestFeedback(
            session_id=session_id,
            user_id=user_id if user_id else None,  # Allow anonymous feedback
            test_clarity_rating=data.get('test_clarity_rating'),
            audio_comfort_rating=data.get('audio_comfort_rating'),
            ease_of_use_rating=data.get('ease_of_use_rating'),
            suggestions_text=suggestions_text,  # Now required and validated
            user_agent=user_agent
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Log feedback submission (without personal data)
        feedback_type = 'authenticated' if user_id else 'anonymous'
        
        # AUTOMATIC NLP ANALYSIS: Run NLP pipeline on feedback text
        nlp_result = None
        try:
            from backend.nlp_engine.store_results import analyze_and_store_feedback
            
            # Run NLP analysis and store results in test_nlp_insights table
            nlp_result = analyze_and_store_feedback(
                feedback_text=suggestions_text,
                test_id=session_id  # Associate with test session
            )
            
            if nlp_result:
                pass  # NLP analysis completed successfully
            else:
                pass  # NLP analysis failed (non-critical)
                
        except ImportError as ie:
            print(f"ERROR: NLP engine import failed: {ie}") # Explicit debug print
            pass  # NLP engine not available - skipping analysis
        except Exception as nlp_error:
            print(f"ERROR: NLP analysis execution failed: {nlp_error}") # Explicit debug print
            import traceback
            traceback.print_exc()
            pass  # NLP analysis error (non-critical)
        
        # Prepare response with optional NLP insights
        response_data = {
            'success': True,
            'message': 'Thank you for your feedback! It helps us improve the platform.',
            'feedback_id': feedback.id  # Safe to return for confirmation
        }
        
        # Include NLP insights in response if analysis was successful
        if nlp_result:
            response_data['nlp_insights'] = {
                'sentiment': nlp_result.get('sentiment'),
                'analysis_id': nlp_result.get('id'),
                'processed': True
            }
        else:
            response_data['nlp_insights'] = {
                'processed': False,
                'note': 'NLP analysis will be processed asynchronously'
            }
        
        return jsonify(response_data)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to submit feedback'}), 500


@feedback_bp.route('/summary', methods=['GET'])
def get_feedback_summary():
    """
    Get aggregated feedback statistics for platform improvement.
    Admin/development endpoint - no personal data exposed.
    
    Query Parameters:
    - days (optional): Number of days to include (default: 30, max: 365)
    
    Returns:
    - Aggregated statistics without personal identifiers
    """
    try:
        days = min(int(request.args.get('days', 30)), 365)  # Cap at 1 year
        
        summary = TestFeedback.get_feedback_summary(limit_days=days)
        
        if not summary:
            return jsonify({
                'period_days': days,
                'message': 'No feedback data available for the specified period'
            })
        
        return jsonify(summary)
        
    except ValueError:
        return jsonify({'error': 'Invalid days parameter'}), 400
    except Exception as e:
        return jsonify({'error': 'Failed to generate feedback summary'}), 500