"""
AuroHear NLP Engine

This package provides natural language processing capabilities for analyzing
user feedback from hearing tests. It includes sentiment analysis, emotion
detection, issue categorization, and result storage in Supabase.

Main Components:
- feedback_analyzer.py: Core NLP analysis using transformers
- store_results.py: Supabase integration and result storage

Usage:
    from nlp_engine.store_results import analyze_and_store_feedback
    
    result = analyze_and_store_feedback(
        feedback_text="The test was great!",
        test_id="550e8400-e29b-41d4-a716-446655440000"
    )
"""

from .feedback_analyzer import analyze_feedback
from .store_results import (
    analyze_and_store_feedback,
    get_test_insights,
    NLPResultsStorage,
    NLPInsight
)

__version__ = "1.0.0"
__author__ = "AuroHear Team"

# Public API
__all__ = [
    'analyze_feedback',
    'analyze_and_store_feedback', 
    'get_test_insights',
    'NLPResultsStorage',
    'NLPInsight'
]