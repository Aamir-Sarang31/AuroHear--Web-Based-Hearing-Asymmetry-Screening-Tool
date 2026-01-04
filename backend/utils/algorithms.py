"""
Audiometric algorithms for AuroHear application.
Implements Hughson-Westlake and threshold computation algorithms.
"""

import uuid
from datetime import datetime
from backend.database import db
from backend.models import ScreeningSessions, User


def compute_threshold(responses):
    """
    Compute hearing threshold from test responses using Hughson-Westlake principles.
    
    Args:
        responses: List of response dictionaries with 'level' and 'heard' keys
    
    Returns:
        float: Computed threshold in dB HL
    """
    if not responses:
        return 40.0
    
    level_map = {}
    for r in responses:
        level = r.get('level')
        if level is None:
            continue
        try:
            level = float(level)
        except (TypeError, ValueError):
            continue
        
        if level not in level_map:
            level_map[level] = {'yes': 0, 'total': 0}
        
        level_map[level]['total'] += 1
        if r.get('heard'):
            level_map[level]['yes'] += 1
    
    levels = sorted(level_map.keys())
    
    # Find levels where response rate >= 50%
    candidate_levels = [l for l in levels if (level_map[l]['yes'] / level_map[l]['total']) >= 0.5]
    if candidate_levels:
        return min(candidate_levels)
    
    # Fallback: find minimum level where sound was heard
    heard_levels = [l for l in levels if level_map[l]['yes'] > 0]
    return min(heard_levels) if heard_levels else 40.0


def save_screening_session(user_id, thresholds, left_avg, right_avg, dissimilarity):
    """
    Save a completed screening session for authenticated users only.
    Guest sessions are never saved to maintain privacy.
    
    Creates individual rows in screening_sessions table for each frequency/ear combination.
    
    Args:
        user_id: User ID
        thresholds: Dict with 'left' and 'right' ear threshold data
        left_avg: Average threshold for left ear
        right_avg: Average threshold for right ear
        dissimilarity: Maximum interaural difference
    
    Returns:
        str or None: Session ID if saved, None if not saved (guest user)
    """
    try:
        user = User.query.get(user_id)
        if not user or user.auth_type != 'authenticated':
            return None
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        current_timestamp = datetime.now()
        
        # Save individual frequency results as separate rows
        session_rows = []
        for ear in ['left', 'right']:
            for freq_str, threshold in thresholds.get(ear, {}).items():
                try:
                    frequency = int(freq_str)
                    threshold_value = float(threshold)
                    
                    # Create a row for this frequency/ear combination
                    session_row = ScreeningSessions(
                        session_id=session_id,
                        user_id=user_id,
                        timestamp=current_timestamp,
                        ear=ear,
                        frequency_hz=frequency,
                        threshold_db=threshold_value
                    )
                    session_rows.append(session_row)
                    db.session.add(session_row)
                    
                except (ValueError, TypeError):
                    continue
        
        if not session_rows:
            return None
        
        db.session.commit()
        return session_id
        
    except Exception as e:
        db.session.rollback()
        return None


def initialize_test_state():
    """
    Initialize a new test state for audiometric testing.
    
    Returns:
        dict: Initial test state configuration
    """
    test_frequencies = [5000, 4000, 2000, 1000, 500, 250]
    test_sequence = [{'freq': freq, 'ear': ear} for freq in test_frequencies for ear in ['right', 'left']]

    return {
        'thresholds': {'left': {}, 'right': {}},
        'test_sequence': test_sequence,
        'current_test_index': 0,
        'total_tests': len(test_sequence),
        'current_test': {
            'frequency': test_sequence[0]['freq'],
            'ear': test_sequence[0]['ear'],
            'current_level': 40,
            'responses': [],
            'trial_count': 0,
            'max_trials': 12
        }
    }


def process_test_response(test_state, heard):
    """
    Process a test response and update test state using Hughson-Westlake algorithm.
    
    Args:
        test_state: Current test state dictionary
        heard: Boolean indicating if the tone was heard
    
    Returns:
        dict: Updated test state
    """
    current_test = test_state.get('current_test')
    if not current_test:
        return test_state

    current_test['responses'] = current_test.get('responses', [])
    current_test['trial_count'] = current_test.get('trial_count', 0) + 1
    old_level = current_test.get('current_level', 40)
    current_test['responses'].append({'level': old_level, 'heard': heard})

    # Hughson-Westlake algorithm
    if heard:
        current_test['current_level'] = int(max(-10, old_level - 10))
    else:
        current_test['current_level'] = int(min(40, old_level + 5))

    # Check if threshold should be computed
    should_compute_threshold = (
        (heard and current_test['current_level'] == old_level) or
        current_test['trial_count'] >= current_test.get('max_trials', 12)
    )

    if should_compute_threshold:
        threshold = compute_threshold(current_test['responses'])
        freq = int(current_test['frequency'])
        test_state['thresholds'][current_test['ear']][freq] = float(threshold)
        test_state['current_test_index'] += 1

        # Move to next test or complete
        if test_state['current_test_index'] < test_state['total_tests']:
            next_test_data = test_state['test_sequence'][test_state['current_test_index']]
            test_state['current_test'] = {
                'frequency': next_test_data['freq'],
                'ear': next_test_data['ear'],
                'current_level': 40,
                'responses': [],
                'trial_count': 0,
                'max_trials': 12
            }

    return test_state


def finalize_test_results(test_state):
    """
    Finalize test results and compute summary statistics.
    
    Args:
        test_state: Completed test state dictionary
    
    Returns:
        dict: Final results with averages and dissimilarity
    """
    test_frequencies = [5000, 4000, 2000, 1000, 500, 250]
    
    # Fill missing thresholds with default value
    for ear in ['left', 'right']:
        for freq in test_frequencies:
            if str(freq) not in test_state['thresholds'][ear]:
                test_state['thresholds'][ear][str(freq)] = 40.0
    
    # Calculate averages
    left_values = [test_state['thresholds']['left'][str(f)] for f in test_frequencies]
    right_values = [test_state['thresholds']['right'][str(f)] for f in test_frequencies]
    
    left_avg = sum(left_values) / len(left_values)
    right_avg = sum(right_values) / len(right_values)
    
    # Calculate maximum interaural difference
    max_diff = max(abs(l - r) for l, r in zip(left_values, right_values))
    
    # Check if results are valid (not all default values)
    is_valid = not all(val == 40.0 for val in left_values + right_values)
    
    return {
        'thresholds': test_state['thresholds'],
        'left_avg': left_avg,
        'right_avg': right_avg,
        'dissimilarity': max_diff,
        'is_valid': is_valid,
        'completed': True
    }