"""
User routes for AuroHear application.
Handles user profile, test history, and analysis endpoints.
"""

from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from backend.database import db
from backend.models import User, ScreeningSessions
from backend.utils.helpers import validate_user_access, log_user_action

user_bp = Blueprint('user', __name__)


@user_bp.route('/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        user = validate_user_access(user_id)
        
        return jsonify({
            'user': user.to_dict(),
            'has_test_history': bool(user.left_avg or user.right_avg)
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@user_bp.route('/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile information"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    data = request.json or {}
    
    try:
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Update allowed fields
        if 'name' in data:
            user.name = data['name']
        if 'surname' in data:
            user.surname = data['surname']
        if 'age_group' in data:
            user.age_group = data['age_group']
        if 'gender' in data:
            user.gender = data['gender']
        
        db.session.commit()
        log_user_action(user_id, "profile_updated")
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@user_bp.route('/test-history', methods=['GET'])
def get_test_history():
    """
    Get comprehensive test history for authenticated users from screening_sessions table.
    
    Query Parameters:
    - user_id (required): User ID to fetch history for
    - limit (optional): Maximum number of sessions to return (default: 50)
    - offset (optional): Number of sessions to skip for pagination (default: 0)
    
    Returns:
    - Grouped results by session_id
    - Sessions ordered by timestamp (latest first)
    - Detailed frequency-specific thresholds
    - Summary statistics per session
    """
    user_id = request.args.get('user_id')
    limit = min(int(request.args.get('limit', 50)), 100)  # Cap at 100 sessions
    offset = int(request.args.get('offset', 0))
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        # Verify user exists and has proper access
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Get all screening session rows for this user
        all_results = ScreeningSessions.query.filter_by(user_id=user.id)\
            .order_by(ScreeningSessions.timestamp.desc()).all()
        
        if not all_results:
            return jsonify({
                'user_id': user.id,
                'user_type': user.auth_type,
                'statistics': {
                    'total_sessions': 0,
                    'returned_sessions': 0,
                    'recent_sessions_30d': 0,
                    'has_more': False,
                    'pagination': {'limit': limit, 'offset': offset, 'next_offset': None}
                },
                'history': []
            })
        
        # Group results by session_id
        sessions_dict = {}
        for result in all_results:
            session_id = result.session_id
            if session_id not in sessions_dict:
                sessions_dict[session_id] = {
                    'session_id': session_id,
                    'timestamp': result.timestamp,
                    'results': []
                }
            sessions_dict[session_id]['results'].append(result)
        
        # Convert to list and sort by timestamp (latest first)
        sessions_list = list(sessions_dict.values())
        sessions_list.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Apply pagination
        total_sessions = len(sessions_list)
        paginated_sessions = sessions_list[offset:offset + limit]
        
        history = []
        for session_data in paginated_sessions:
            session_id = session_data['session_id']
            timestamp = session_data['timestamp']
            results = session_data['results']
            
            # Organize results by ear and frequency
            thresholds = {'left': {}, 'right': {}}
            for result in results:
                thresholds[result.ear][result.frequency_hz] = result.threshold_db
            
            # Calculate summary statistics using the class method
            summary = ScreeningSessions.get_session_summary(session_id)
            
            # Calculate session completeness
            expected_frequencies = [250, 500, 1000, 2000, 4000, 5000]
            completeness = {
                'left': len([f for f in expected_frequencies if f in thresholds['left']]),
                'right': len([f for f in expected_frequencies if f in thresholds['right']]),
                'total_expected': len(expected_frequencies) * 2,
                'total_recorded': len(results)
            }
            
            # Determine session quality
            is_complete = completeness['total_recorded'] >= completeness['total_expected']
            is_valid = summary and summary['left_avg'] is not None and summary['right_avg'] is not None
            
            # Compute interaural differences for this session
            interaural_analysis = ScreeningSessions.compute_interaural_differences(thresholds)
            
            session_entry = {
                'session_id': session_id,
                'timestamp': timestamp.isoformat(),
                'date': timestamp.strftime('%Y-%m-%d'),
                'time': timestamp.strftime('%H:%M:%S'),
                'summary': {
                    'left_avg': summary['left_avg'] if summary else None,
                    'right_avg': summary['right_avg'] if summary else None,
                    'dissimilarity': summary['dissimilarity'] if summary else None,
                    'asymmetry_detected': (summary['dissimilarity'] >= 20) if (summary and summary['dissimilarity']) else False
                },
                'thresholds': thresholds,
                'interaural_differences': {
                    'per_frequency': interaural_analysis['per_frequency'] if interaural_analysis else {},
                    'summary_stats': interaural_analysis['summary_stats'] if interaural_analysis else None,
                    'has_analysis': interaural_analysis is not None
                },
                'metadata': {
                    'test_type': 'screening',
                    'is_complete': is_complete,
                    'is_valid': is_valid,
                    'completeness': completeness,
                    'frequency_count': len(results)
                }
            }
            
            history.append(session_entry)
        
        # Calculate summary statistics
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_sessions = [s for s in sessions_list if s['timestamp'] >= thirty_days_ago]
        
        summary_stats = {
            'total_sessions': total_sessions,
            'returned_sessions': len(history),
            'recent_sessions_30d': len(recent_sessions),
            'has_more': (offset + len(history)) < total_sessions,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'next_offset': offset + limit if (offset + len(history)) < total_sessions else None
            }
        }
        
        # Add trend analysis and educational summary if sufficient data
        trend_analysis = None
        educational_summary = None
        
        if total_sessions >= 2:
            try:
                trend_analysis = ScreeningSessions.analyze_session_trends(user.id, min(total_sessions, 10))
                educational_summary = ScreeningSessions.generate_educational_summary(user.id, min(total_sessions, 10))
            except Exception as e:
                pass  # Analysis failed (non-critical)
        
        log_user_action(user_id, "test_history_retrieved", f"sessions={len(history)}")
        
        return jsonify({
            'user_id': user.id,
            'user_type': user.auth_type,
            'statistics': summary_stats,
            'trend_analysis': trend_analysis,
            'educational_summary': educational_summary,
            'history': history
        })
        
    except ValueError as e:
        if 'authenticated' in str(e):
            return jsonify({
                'error': 'Test history only available for authenticated users',
                'auth_required': True
            }), 403
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/session/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """
    Get detailed information for a specific screening session.
    
    Path Parameters:
    - session_id: UUID of the screening session
    
    Query Parameters:
    - user_id (required): User ID for access control
    
    Returns:
    - Complete session data with all frequency results
    - Session metadata and quality indicators
    """
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        # Verify user authentication and ownership
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Find all results for this session and verify ownership
        results = ScreeningSessions.query.filter_by(
            session_id=session_id, 
            user_id=user.id
        ).all()
        
        if not results:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get session summary
        summary = ScreeningSessions.get_session_summary(session_id)
        
        # Organize detailed results
        detailed_results = []
        thresholds = {'left': {}, 'right': {}}
        
        for result in results:
            detailed_results.append(result.to_dict())
            thresholds[result.ear][result.frequency_hz] = result.threshold_db
        
        session_data = {
            'session': {
                'session_id': session_id,
                'timestamp': results[0].timestamp.isoformat(),
                'user_id': user.id,
                'summary': summary
            },
            'thresholds': thresholds,
            'detailed_results': detailed_results,
            'analysis': {
                'frequencies_tested': len(set(r.frequency_hz for r in results)),
                'ears_tested': len(set(r.ear for r in results)),
                'asymmetry_detected': (summary['dissimilarity'] >= 20) if (summary and summary['dissimilarity']) else False,
                'significant_frequencies': []
            }
        }
        
        # Identify frequencies with significant asymmetry (>15 dB difference)
        frequencies = set(r.frequency_hz for r in results)
        for freq in frequencies:
            left_val = thresholds['left'].get(freq)
            right_val = thresholds['right'].get(freq)
            
            if left_val is not None and right_val is not None:
                diff = abs(left_val - right_val)
                if diff >= 15:
                    session_data['analysis']['significant_frequencies'].append({
                        'frequency_hz': freq,
                        'left_threshold': left_val,
                        'right_threshold': right_val,
                        'difference': diff
                    })
        
        return jsonify(session_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/sessions/compare', methods=['POST'])
def compare_sessions():
    """
    Compare multiple screening sessions for trend analysis.
    
    Request Body:
    - user_id (required): User ID for access control
    - session_ids (required): Array of session IDs to compare (max 5)
    
    Returns:
    - Comparative analysis of sessions
    - Trend indicators and changes over time
    """
    data = request.json or {}
    user_id = data.get('user_id')
    session_ids = data.get('session_ids', [])
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    if not session_ids or len(session_ids) > 5:
        return jsonify({'error': 'Provide 1-5 session IDs for comparison'}), 400
    
    try:
        # Verify user authentication
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Fetch session summaries for comparison
        session_summaries = []
        for session_id in session_ids:
            # Verify ownership by checking if any results exist for this user/session
            results = ScreeningSessions.query.filter_by(
                session_id=session_id,
                user_id=user.id
            ).first()
            
            if not results:
                return jsonify({'error': f'Session {session_id} not found or access denied'}), 404
            
            summary = ScreeningSessions.get_session_summary(session_id)
            if summary:
                session_summaries.append(summary)
        
        if len(session_summaries) != len(session_ids):
            return jsonify({'error': 'One or more sessions could not be processed'}), 404
        
        # Sort by timestamp
        session_summaries.sort(key=lambda x: x['timestamp'])
        
        # Build comparison data
        comparison = {
            'user_id': user.id,
            'sessions': [],
            'trends': {
                'left_avg_trend': [],
                'right_avg_trend': [],
                'dissimilarity_trend': [],
                'time_span_days': 0
            }
        }
        
        for summary in session_summaries:
            comparison['sessions'].append({
                'session_id': summary['session_id'],
                'timestamp': summary['timestamp'].isoformat(),
                'left_avg': summary['left_avg'],
                'right_avg': summary['right_avg'],
                'dissimilarity': summary['dissimilarity']
            })
            
            comparison['trends']['left_avg_trend'].append(summary['left_avg'])
            comparison['trends']['right_avg_trend'].append(summary['right_avg'])
            comparison['trends']['dissimilarity_trend'].append(summary['dissimilarity'])
        
        # Calculate time span
        if len(session_summaries) > 1:
            time_span = session_summaries[-1]['timestamp'] - session_summaries[0]['timestamp']
            comparison['trends']['time_span_days'] = time_span.days
        
        return jsonify(comparison)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500


@user_bp.route('/interaural-analysis', methods=['POST'])
def analyze_interaural_differences():
    """
    Analyze interaural threshold differences for given threshold data.
    
    Request Body:
    - thresholds (required): Object with 'left' and 'right' ear data
    - user_id (optional): For access logging
    
    Returns:
    - Per-frequency interaural differences
    - Summary statistics
    - No diagnostic interpretation or severity assignment
    """
    data = request.json or {}
    thresholds = data.get('thresholds')
    user_id = data.get('user_id')
    
    if not thresholds:
        return jsonify({'error': 'Threshold data required'}), 400
    
    try:
        # Compute interaural differences
        analysis = ScreeningSessions.compute_interaural_differences(thresholds)
        
        if not analysis:
            return jsonify({
                'error': 'Unable to compute differences - insufficient data',
                'details': 'Need matching frequency data for both ears'
            }), 400
        
        # Log analysis request (without sensitive data)
        if user_id:
            log_user_action(user_id, "interaural_analysis_requested")
        
        response_data = {
            'analysis_type': 'interaural_threshold_differences',
            'timestamp': datetime.now().isoformat(),
            'frequencies_analyzed': analysis['summary_stats']['frequencies_compared'],
            'per_frequency_differences': analysis['per_frequency'],
            'summary_statistics': analysis['summary_stats'],
            'notes': {
                'measurement_unit': 'dB HL',
                'difference_calculation': 'absolute_difference = |left - right|',
                'signed_difference_interpretation': 'positive = left ear higher threshold (worse), negative = right ear higher threshold (worse)',
                'disclaimer': 'This analysis provides objective measurements only. No diagnostic interpretation is provided.'
            }
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': 'Analysis computation failed'}), 500


@user_bp.route('/session/<session_id>/interaural-analysis', methods=['GET'])
def get_session_interaural_analysis(session_id):
    """
    Get detailed interaural analysis for a specific session.
    
    Path Parameters:
    - session_id: UUID of the screening session
    
    Query Parameters:
    - user_id (required): User ID for access control
    
    Returns:
    - Comprehensive interaural difference analysis for the session
    - Per-frequency comparisons
    - Summary statistics without diagnostic interpretation
    """
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        # Verify user authentication and ownership
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Get session data and verify ownership
        results = ScreeningSessions.query.filter_by(
            session_id=session_id, 
            user_id=user.id
        ).all()
        
        if not results:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # Get session summary with interaural analysis
        summary = ScreeningSessions.get_session_summary(session_id)
        
        if not summary or not summary.get('interaural_differences'):
            return jsonify({
                'error': 'Insufficient data for interaural analysis',
                'details': 'Need threshold data for both ears at matching frequencies'
            }), 400
        
        # Organize response data
        analysis_data = {
            'session_id': session_id,
            'timestamp': summary['timestamp'].isoformat(),
            'analysis_type': 'session_interaural_differences',
            'per_frequency_analysis': summary['interaural_differences'],
            'summary_statistics': summary['interaural_stats'],
            'session_metadata': {
                'total_frequencies': summary['frequency_count'],
                'ears_tested': summary['ears_tested'],
                'left_ear_average': summary['left_avg'],
                'right_ear_average': summary['right_avg']
            },
            'measurement_details': {
                'unit': 'dB HL',
                'calculation_method': 'Per-frequency absolute difference |left - right|',
                'signed_difference_meaning': 'Positive = left ear worse, Negative = right ear worse',
                'max_difference_frequency': None,
                'min_difference_frequency': None
            }
        }
        
        # Find frequencies with max and min differences
        if summary['interaural_differences']:
            max_diff = 0
            min_diff = float('inf')
            max_freq = None
            min_freq = None
            
            for freq, data in summary['interaural_differences'].items():
                abs_diff = data['absolute_difference']
                if abs_diff > max_diff:
                    max_diff = abs_diff
                    max_freq = freq
                if abs_diff < min_diff:
                    min_diff = abs_diff
                    min_freq = freq
            
            analysis_data['measurement_details']['max_difference_frequency'] = max_freq
            analysis_data['measurement_details']['min_difference_frequency'] = min_freq
        
        return jsonify(analysis_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        return jsonify({'error': 'Analysis computation failed'}), 500


@user_bp.route('/trend-analysis', methods=['GET'])
def get_user_trend_analysis():
    """
    Analyze trends in user session history using simple heuristics.
    
    Query Parameters:
    - user_id (required): User ID for access control
    - limit (optional): Maximum number of recent sessions to analyze (default: 10)
    
    Returns:
    - Trend classification: stable, variable, or changing
    - Objective metrics without medical interpretation
    - Simple variance and trend calculations
    """
    user_id = request.args.get('user_id')
    limit = min(int(request.args.get('limit', 10)), 20)  # Cap at 20 sessions
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        # Verify user authentication
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Perform trend analysis
        trend_analysis = ScreeningSessions.analyze_session_trends(user.id, limit)
        
        # Add user context
        response_data = {
            'user_id': user.id,
            'analysis_timestamp': datetime.now().isoformat(),
            'trend_analysis': trend_analysis,
            'methodology': {
                'classification_types': {
                    'stable': 'Low variance across sessions (≤25 dB²)',
                    'variable': 'Moderate variance, normal fluctuation (≤100 dB²)',
                    'changing': 'High variance or clear directional trend (>100 dB² or >2 dB/session)'
                },
                'metrics_calculated': [
                    'Variance in overall hearing thresholds',
                    'Variance in left and right ear averages',
                    'Variance in interaural differences',
                    'Linear trend slopes over time'
                ],
                'disclaimer': 'Analysis provides objective measurement patterns only. No predictive modeling or medical interpretation.'
            }
        }
        
        log_user_action(user_id, "trend_analysis_completed", trend_analysis['classification'])
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        return jsonify({'error': 'Trend analysis computation failed'}), 500


@user_bp.route('/measurement-summary', methods=['GET'])
def get_measurement_summary():
    """
    Generate neutral, educational summary based on multiple sessions.
    
    Query Parameters:
    - user_id (required): User ID for access control
    - limit (optional): Maximum number of recent sessions to analyze (default: 10)
    
    Returns:
    - Educational summary highlighting consistency or variability
    - Neutral language avoiding clinical interpretation
    - Appropriate medical disclaimers and professional consultation guidance
    """
    user_id = request.args.get('user_id')
    limit = min(int(request.args.get('limit', 10)), 20)  # Cap at 20 sessions
    
    if not user_id:
        return jsonify({'error': 'User ID required'}), 400
    
    try:
        # Verify user authentication
        user = validate_user_access(user_id, require_authenticated=True)
        
        # Generate educational summary
        summary = ScreeningSessions.generate_educational_summary(user.id, limit)
        
        # Add user context and metadata
        response_data = {
            'user_id': user.id,
            'generated_at': datetime.now().isoformat(),
            'summary': summary,
            'important_notes': {
                'screening_nature': 'This is a preliminary screening tool, not a diagnostic test',
                'professional_evaluation': 'Professional audiological assessment is recommended for comprehensive hearing evaluation',
                'measurement_limitations': 'Screening measurements may be influenced by environmental factors and equipment variations',
                'consultation_guidance': 'Consult healthcare providers for hearing concerns or questions about results'
            },
            'when_to_seek_professional_help': [
                'Sudden changes in hearing ability',
                'Persistent tinnitus (ringing in ears)',
                'Difficulty understanding speech in noisy environments',
                'Concerns about hearing loss affecting daily activities',
                'Family history of hearing loss',
                'Exposure to loud noises or ototoxic medications'
            ]
        }
        
        log_user_action(user_id, "measurement_summary_generated", summary['summary_type'])
        return jsonify(response_data)
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 403 if 'authenticated' in str(e) else 400
    except Exception as e:
        return jsonify({'error': 'Summary generation failed'}), 500