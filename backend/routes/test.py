"""
Test routes for AuroHear application.
Handles audiometric testing, tone generation, and test session management.
"""

import json
from flask import Blueprint, request, jsonify

from backend.database import db
from backend.models import User, ScreeningSessions
from backend.utils.audio import generate_tone_response, validate_audio_parameters
from backend.utils.algorithms import (
    initialize_test_state, process_test_response, 
    finalize_test_results, save_screening_session
)
from backend.utils.helpers import validate_user_access, log_user_action

test_bp = Blueprint('test', __name__)


@test_bp.route('/start', methods=['POST'])
def start_test():
    """Initialize a new hearing test session"""
    data = request.json or {}
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = validate_user_access(user_id)
        
        # Initialize test state
        test_state = initialize_test_state()
        
        user.test_state = json.dumps(test_state)
        db.session.commit()
        
        log_user_action(user_id, "test_started")
        
        return jsonify({
            'freq': test_state['current_test']['frequency'],
            'ear': test_state['current_test']['ear'],
            'level': test_state['current_test']['current_level'],
            'progress': 0,
            'test_number': 1,
            'total_tests': test_state['total_tests']
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to start test: {str(e)}'}), 500


@test_bp.route('/submit-response', methods=['POST'])
def submit_response():
    """Submit a test response and get next test parameters"""
    data = request.json or {}
    user_id = data.get('user_id')
    heard = data.get('heard')
    
    if not user_id or heard is None:
        return jsonify({'error': 'User ID and response required'}), 400
    
    try:
        user = validate_user_access(user_id)
        
        if not user.test_state:
            return jsonify({'error': 'No active test session'}), 404
        
        test_state = json.loads(user.test_state)
        
        # Process response using algorithms
        test_state = process_test_response(test_state, heard)
        
        user.test_state = json.dumps(test_state)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to process response: {str(e)}'}), 500


@test_bp.route('/next', methods=['GET'])
def next_test():
    """Get next test parameters"""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = validate_user_access(user_id)
        
        if not user.test_state:
            return jsonify({'error': 'No active test session'}), 404
        
        test_state = json.loads(user.test_state)
        current_test_index = test_state.get('current_test_index', 0)
        total_tests = test_state.get('total_tests', 0)

        if current_test_index >= total_tests:
            # Test completed - finalize results
            results = finalize_test_results(test_state)
            
            # Update user's latest results
            user.left_avg = results['left_avg']
            user.right_avg = results['right_avg']
            user.dissimilarity = results['dissimilarity']
            user.test_state = None  # Clear test state
            db.session.commit()

            # Save screening session for authenticated users only
            session_id = save_screening_session(
                user_id=user.id,
                thresholds=results['thresholds'],
                left_avg=results['left_avg'],
                right_avg=results['right_avg'],
                dissimilarity=results['dissimilarity']
            )

            log_user_action(user_id, "test_completed", f"session_id={session_id}")

            return jsonify({
                'completed': True,
                'is_valid': results['is_valid'],
                'thresholds': results['thresholds'],
                'left_avg': results['left_avg'],
                'right_avg': results['right_avg'],
                'max_diff': results['dissimilarity'],
                'session_id': session_id  # Will be None for guest users
            })
        else:
            current_test = test_state.get('current_test', {})
            progress = (current_test_index / total_tests) * 100 if total_tests > 0 else 0
            return jsonify({
                'completed': False,
                'freq': current_test.get('frequency'),
                'ear': current_test.get('ear'),
                'level': current_test.get('current_level'),
                'progress': progress,
                'test_number': current_test_index + 1,
                'total_tests': total_tests
            })
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to get next test: {str(e)}'}), 500


@test_bp.route('/tone')
def generate_tone():
    """Generate audio tone for testing"""
    try:
        # Get and validate parameters
        freq = request.args.get('freq', 1000)
        level_db = request.args.get('level_db', 40)
        ear = request.args.get('channel', 'both')  # Support both 'channel' and 'ear'
        if ear == 'both':
            ear = request.args.get('ear', 'both')
        duration = request.args.get('duration', None)
        
        # Validate parameters
        freq, level_db, ear, duration = validate_audio_parameters(freq, level_db, ear, duration or 0.35)
        
        # Generate tone response
        return generate_tone_response(freq, level_db, ear, duration)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to generate tone: {str(e)}'}), 500


@test_bp.route('/save-results', methods=['POST'])
def save_results():
    """Save aggregated test results for authenticated users"""
    data = request.json or {}
    user_id = data.get('user_id')
    left_avg = data.get('left_avg')
    right_avg = data.get('right_avg')
    dissimilarity = data.get('dissimilarity')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = validate_user_access(user_id)
        
        # Only save for authenticated users (privacy-first approach)
        if user.auth_type != 'authenticated':
            log_user_action(user_id, "results_not_saved", "guest_session")
            return jsonify({
                'success': True,
                'message': 'Guest session - results not stored for privacy',
                'session_id': None
            })
        
        # Update user's latest results
        if left_avg is not None:
            user.left_avg = float(left_avg)
        if right_avg is not None:
            user.right_avg = float(right_avg)
        if dissimilarity is not None:
            user.dissimilarity = float(dissimilarity)
        
        db.session.commit()
        log_user_action(user_id, "results_saved", f"L={left_avg}, R={right_avg}, D={dissimilarity}")
        
        return jsonify({
            'success': True,
            'message': 'Results saved successfully',
            'user_id': user_id
        })
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500