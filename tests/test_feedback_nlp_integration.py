#!/usr/bin/env python3
"""
Test script for feedback submission with automatic NLP analysis.

This script tests the complete feedback submission flow:
1. Submits feedback via the Flask endpoint
2. Verifies NLP analysis runs automatically
3. Checks that results are stored in test_nlp_insights table
4. Validates the association between feedback and NLP results

Usage:
    python test_feedback_nlp_integration.py
"""

import os
import sys
import uuid
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
BASE_URL = "http://localhost:5000"  # Adjust if your Flask app runs on different port
TEST_SESSION_ID = str(uuid.uuid4())


def test_feedback_submission_with_nlp():
    """Test the complete feedback submission flow with NLP analysis"""
    
    print("🧪 Testing Feedback Submission with Automatic NLP Analysis")
    print("=" * 60)
    
    # Test cases with different feedback types
    test_cases = [
        {
            "feedback": "The test was excellent! Very clear instructions and perfect audio quality.",
            "expected_sentiment": "positive",
            "description": "Positive feedback"
        },
        {
            "feedback": "I couldn't hear the tones clearly. The volume was too low and there was background noise.",
            "expected_sentiment": "negative",
            "description": "Negative feedback with issues"
        },
        {
            "feedback": "The test was okay, but I'm not sure if I heard all the sounds correctly.",
            "expected_sentiment": "neutral",
            "description": "Uncertain feedback"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"Feedback: \"{test_case['feedback']}\"")
        
        # Generate unique session ID for this test
        session_id = str(uuid.uuid4())
        print(f"Session ID: {session_id}")
        
        # Prepare feedback data
        feedback_data = {
            "session_id": session_id,
            "user_id": None,  # Anonymous feedback
            "test_clarity_rating": 4,
            "audio_comfort_rating": 4,
            "ease_of_use_rating": 4,
            "suggestions_text": test_case['feedback']
        }
        
        try:
            # Submit feedback
            print("📤 Submitting feedback...")
            response = requests.post(
                f"{BASE_URL}/submit_feedback",
                json=feedback_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Feedback submission successful!")
                print(f"   Feedback ID: {result.get('feedback_id')}")
                
                # Check NLP insights in response
                nlp_insights = result.get('nlp_insights', {})
                if nlp_insights.get('processed'):
                    print("✅ NLP analysis completed!")
                    print(f"   Sentiment: {nlp_insights.get('sentiment')}")
                    print(f"   Analysis ID: {nlp_insights.get('analysis_id')}")
                    
                    # Verify sentiment matches expectation
                    actual_sentiment = nlp_insights.get('sentiment')
                    expected_sentiment = test_case['expected_sentiment']
                    
                    if actual_sentiment == expected_sentiment:
                        print(f"✅ Sentiment analysis correct: {actual_sentiment}")
                    else:
                        print(f"⚠️  Sentiment mismatch: expected {expected_sentiment}, got {actual_sentiment}")
                    
                    # Test NLP insights retrieval endpoint
                    print("📊 Testing NLP insights retrieval...")
                    insights_response = requests.get(f"{BASE_URL}/nlp/insights/{session_id}")
                    
                    if insights_response.status_code == 200:
                        insights_data = insights_response.json()
                        insights_count = insights_data.get('count', 0)
                        print(f"✅ Retrieved {insights_count} NLP insights for session")
                        
                        if insights_count > 0:
                            latest_insight = insights_data['insights'][0]
                            print(f"   Latest analysis: {latest_insight.get('sentiment')}")
                            print(f"   Emotions: {latest_insight.get('emotions', {})}")
                            print(f"   Issues detected: {len(latest_insight.get('issues', []))}")
                    else:
                        print(f"❌ Failed to retrieve insights: {insights_response.status_code}")
                    
                else:
                    print("⚠️  NLP analysis not processed (may be asynchronous)")
                
                results.append({
                    'test_case': i,
                    'success': True,
                    'feedback_id': result.get('feedback_id'),
                    'nlp_processed': nlp_insights.get('processed', False),
                    'sentiment': nlp_insights.get('sentiment'),
                    'session_id': session_id
                })
                
            else:
                print(f"❌ Feedback submission failed: {response.status_code}")
                print(f"   Error: {response.text}")
                results.append({
                    'test_case': i,
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                })
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            results.append({
                'test_case': i,
                'success': False,
                'error': str(e)
            })
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            results.append({
                'test_case': i,
                'success': False,
                'error': str(e)
            })
    
    # Test reliability metrics endpoint
    print(f"\n📊 Testing NLP Reliability Metrics...")
    try:
        reliability_response = requests.get(f"{BASE_URL}/nlp/reliability?days=1")
        if reliability_response.status_code == 200:
            reliability_data = reliability_response.json()
            print("✅ Reliability metrics retrieved successfully!")
            
            reliability_score = reliability_data.get('reliability', {}).get('reliability_score')
            if reliability_score is not None:
                print(f"   Platform reliability score: {reliability_score}%")
            
            sentiment_summary = reliability_data.get('sentiment_summary')
            if sentiment_summary:
                total_analyses = sentiment_summary.get('total_analyses', 0)
                print(f"   Total analyses in period: {total_analyses}")
        else:
            print(f"⚠️  Reliability metrics not available: {reliability_response.status_code}")
    except Exception as e:
        print(f"⚠️  Reliability metrics test failed: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    successful_tests = len([r for r in results if r['success']])
    total_tests = len(results)
    nlp_processed_count = len([r for r in results if r.get('nlp_processed')])
    
    print(f"Successful submissions: {successful_tests}/{total_tests}")
    print(f"NLP analyses processed: {nlp_processed_count}/{successful_tests}")
    
    if successful_tests == total_tests:
        print("🎉 All feedback submissions successful!")
        if nlp_processed_count == successful_tests:
            print("🎉 All NLP analyses processed successfully!")
        else:
            print("⚠️  Some NLP analyses were not processed immediately")
    else:
        print("⚠️  Some feedback submissions failed")
        
        # Show failed tests
        failed_tests = [r for r in results if not r['success']]
        for failed in failed_tests:
            print(f"   Test {failed['test_case']}: {failed.get('error', 'Unknown error')}")
    
    return results


def check_flask_server():
    """Check if Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        return response.status_code == 200
    except:
        return False


if __name__ == "__main__":
    print("🚀 AuroHear Feedback + NLP Integration Test")
    print("=" * 60)
    
    # Check if Flask server is running
    if not check_flask_server():
        print(f"❌ Flask server not accessible at {BASE_URL}")
        print("   Please start the Flask application first:")
        print("   python app.py")
        sys.exit(1)
    
    print(f"✅ Flask server accessible at {BASE_URL}")
    
    # Run the tests
    try:
        results = test_feedback_submission_with_nlp()
        
        # Exit with appropriate code
        successful_tests = len([r for r in results if r['success']])
        if successful_tests == len(results):
            print("\n🎉 All tests completed successfully!")
            sys.exit(0)
        else:
            print(f"\n⚠️  {len(results) - successful_tests} tests failed.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Tests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)