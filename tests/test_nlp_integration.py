#!/usr/bin/env python3
"""
Test script for NLP integration with Supabase storage.

This script tests the complete pipeline:
1. NLP analysis of feedback text
2. Storage in Supabase test_nlp_insights table
3. Retrieval and verification of stored results

Usage:
    python test_nlp_integration.py
"""

import os
import uuid
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nlp_engine.store_results import analyze_and_store_feedback, get_test_insights


def test_nlp_pipeline():
    """Test the complete NLP analysis and storage pipeline"""
    
    print("🧪 Testing AuroHear NLP Integration Pipeline")
    print("=" * 50)
    
    # Test cases with different types of feedback
    test_cases = [
        {
            "feedback": "The test was excellent! Very clear instructions and comfortable audio levels.",
            "expected_sentiment": "positive",
            "description": "Positive feedback"
        },
        {
            "feedback": "I couldn't hear some tones clearly. The volume was too low and there was background noise.",
            "expected_sentiment": "negative", 
            "description": "Negative feedback with issues"
        },
        {
            "feedback": "The test was okay, not sure if I heard all the sounds correctly.",
            "expected_sentiment": "neutral",
            "description": "Uncertain/neutral feedback"
        },
        {
            "feedback": "Great interface but the headphones were uncomfortable. Mixed experience overall.",
            "expected_sentiment": "mixed",
            "description": "Mixed sentiment feedback"
        }
    ]
    
    results = []
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"Feedback: \"{test_case['feedback']}\"")
        
        # Generate unique test ID
        test_id = str(uuid.uuid4())
        print(f"Test ID: {test_id}")
        
        # Analyze and store feedback
        try:
            result = analyze_and_store_feedback(test_case['feedback'], test_id)
            
            if result:
                print("✅ Analysis and storage successful!")
                print(f"   Stored ID: {result.get('id')}")
                print(f"   Sentiment: {result.get('sentiment')}")
                print(f"   Emotions: {result.get('emotions', {})}")
                print(f"   Uncertainty: {result.get('uncertainty', 0)}")
                print(f"   Issues: {len(result.get('issues', []))} detected")
                print(f"   Intent: {result.get('intent')}")
                
                # Verify retrieval
                retrieved = get_test_insights(test_id)
                if retrieved and len(retrieved) > 0:
                    print("✅ Retrieval successful!")
                    results.append({
                        'test_case': i,
                        'success': True,
                        'result': result,
                        'retrieved': retrieved[0]
                    })
                else:
                    print("❌ Retrieval failed!")
                    results.append({
                        'test_case': i,
                        'success': False,
                        'error': 'Retrieval failed'
                    })
            else:
                print("❌ Analysis or storage failed!")
                results.append({
                    'test_case': i,
                    'success': False,
                    'error': 'Analysis/storage failed'
                })
                
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'test_case': i,
                'success': False,
                'error': str(e)
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    successful_tests = len([r for r in results if r['success']])
    total_tests = len(results)
    
    print(f"Successful tests: {successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 All tests passed! NLP integration is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        
        # Show failed tests
        failed_tests = [r for r in results if not r['success']]
        for failed in failed_tests:
            print(f"   Test {failed['test_case']}: {failed.get('error', 'Unknown error')}")
    
    return results


def test_environment_setup():
    """Test that the environment is properly configured"""
    
    print("🔧 Testing Environment Setup")
    print("-" * 30)
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        print("❌ SUPABASE_URL environment variable not set")
        return False
    else:
        print(f"✅ SUPABASE_URL: {supabase_url[:30]}...")
    
    if not supabase_key:
        print("❌ SUPABASE_KEY environment variable not set")
        return False
    else:
        print(f"✅ SUPABASE_KEY: {supabase_key[:20]}...")
    
    # Test imports
    try:
        from nlp_engine.feedback_analyzer import analyze_feedback
        print("✅ feedback_analyzer import successful")
    except ImportError as e:
        print(f"❌ feedback_analyzer import failed: {e}")
        return False
    
    try:
        from nlp_engine.store_results import NLPResultsStorage
        print("✅ store_results import successful")
    except ImportError as e:
        print(f"❌ store_results import failed: {e}")
        return False
    
    # Test Supabase connection
    try:
        storage = NLPResultsStorage()
        print("✅ Supabase connection successful")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 AuroHear NLP Integration Test Suite")
    print("=" * 60)
    
    # Test environment setup first
    if not test_environment_setup():
        print("\n❌ Environment setup failed. Please check your configuration.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Run the main pipeline tests
    try:
        results = test_nlp_pipeline()
        
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