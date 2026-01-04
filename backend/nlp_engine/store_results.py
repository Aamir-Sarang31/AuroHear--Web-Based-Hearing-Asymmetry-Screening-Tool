"""
NLP Results Storage Module for AuroHear

This module handles the storage of NLP analysis results from feedback_analyzer.py
into the Supabase test_nlp_insights table. It follows clean architecture principles
with proper error handling and data validation.

Author: AuroHear Team
"""

import os
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from supabase import create_client, Client
from dotenv import load_dotenv

from .feedback_analyzer import analyze_feedback

# Load environment variables
load_dotenv()

# Configure logging
# logging.basicConfig(level=logging.INFO)  # REMOVED: Managed by app
logger = logging.getLogger(__name__)


@dataclass
class NLPInsight:
    """Data class for NLP analysis results"""
    test_id: str
    sentiment: str
    emotions: Dict[str, float]
    uncertainty: float
    issues: List[Dict[str, Any]]
    intent: str
    created_at: Optional[datetime] = None
    id: Optional[str] = None


class NLPResultsStorage:
    """
    Handles storage of NLP analysis results in Supabase.
    
    This class provides a clean interface for analyzing feedback text
    and storing the results in the test_nlp_insights table.
    """
    
    def __init__(self):
        """Initialize Supabase client and validate configuration"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        
        # Try service role key first (for backend bypass RLS), then fallback to anon key
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY (or SUPABASE_SERVICE_ROLE_KEY) environment variables are required")
        
        try:
            self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
            
            # Log which key type is being used (without exposing the key)
            key_type = "SERVICE_ROLE" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "ANON"
            logger.info(f"Supabase client initialized successfully using {key_type} key")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def _normalize_sentiment(self, sentiment_result: Dict[str, Any]) -> str:
        """
        Normalize sentiment analysis result to standard format.
        
        Args:
            sentiment_result: Raw sentiment from transformers pipeline
            
        Returns:
            Normalized sentiment string: 'positive', 'negative', 'neutral'
        """
        try:
            label = sentiment_result.get('label', '').upper()
            confidence = sentiment_result.get('score', 0.0)
            
            # Map transformers labels to our standard format
            if label == 'POSITIVE':
                return 'positive'
            elif label == 'NEGATIVE':
                return 'negative'
            else:
                # If confidence is low, classify as neutral
                if confidence < 0.6:
                    return 'neutral'
                return 'mixed'
                
        except Exception as e:
            logger.warning(f"Error normalizing sentiment: {e}")
            return 'neutral'
    
    def _normalize_emotions(self, emotions_result: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Normalize emotion analysis results to dictionary format.
        
        Args:
            emotions_result: Raw emotions from transformers pipeline
            
        Returns:
            Dictionary of emotion scores
        """
        try:
            emotions_dict = {}
            for emotion in emotions_result:
                label = emotion.get('label', '').lower()
                score = emotion.get('score', 0.0)
                emotions_dict[label] = round(score, 3)
            
            return emotions_dict
            
        except Exception as e:
            logger.warning(f"Error normalizing emotions: {e}")
            return {}
    
    def _normalize_issues(self, issues_list: List[str]) -> List[Dict[str, Any]]:
        """
        Convert issues list to structured format with severity assessment.
        
        Args:
            issues_list: List of detected issue types
            
        Returns:
            List of structured issue objects
        """
        try:
            structured_issues = []
            
            # Define severity mapping based on issue type
            severity_mapping = {
                'audibility': 'high',      # Critical for hearing test
                'noise': 'medium',         # Affects test quality
                'delay': 'medium',         # Impacts user experience
                'confusion': 'high',       # Critical for test validity
                'device': 'medium'         # Hardware-related
            }
            
            for issue_type in issues_list:
                structured_issues.append({
                    'type': issue_type,
                    'severity': severity_mapping.get(issue_type, 'low'),
                    'detected_at': datetime.utcnow().isoformat()
                })
            
            return structured_issues
            
        except Exception as e:
            logger.warning(f"Error normalizing issues: {e}")
            return []
    
    def _validate_test_id(self, test_id: str) -> bool:
        """
        Validate that test_id is a valid UUID format.
        
        Args:
            test_id: Test session identifier
            
        Returns:
            True if valid UUID format, False otherwise
        """
        try:
            uuid.UUID(test_id)
            return True
        except (ValueError, TypeError):
            return False
    
    def analyze_and_store(self, feedback_text: str, test_id: str) -> Optional[Dict[str, Any]]:
        """
        Analyze feedback text and store results in Supabase.
        
        This is the main public method that orchestrates the entire process:
        1. Validates input parameters
        2. Calls the NLP analyzer
        3. Normalizes the results
        4. Stores in Supabase
        5. Returns the stored results
        
        Args:
            feedback_text: User feedback text to analyze
            test_id: UUID of the test session
            
        Returns:
            Dictionary containing stored NLP results, or None if failed
        """
        try:
            # Input validation
            if not feedback_text or not feedback_text.strip():
                logger.error("Feedback text is empty or None")
                return None
            
            if not test_id or not self._validate_test_id(test_id):
                logger.error(f"Invalid test_id format: {test_id}")
                return None
            
            logger.info(f"Starting NLP analysis for test_id: {test_id}")
            
            # Step 1: Analyze feedback using existing NLP module
            try:
                raw_analysis = analyze_feedback(feedback_text)
                logger.info("NLP analysis completed successfully")
            except Exception as e:
                logger.error(f"NLP analysis failed: {e}")
                return None
            
            # Step 2: Normalize and structure the results
            try:
                normalized_sentiment = self._normalize_sentiment(raw_analysis['sentiment'])
                normalized_emotions = self._normalize_emotions(raw_analysis['emotions'])
                normalized_issues = self._normalize_issues(raw_analysis['issues'])
                
                # Create NLP insight object
                insight = NLPInsight(
                    test_id=test_id,
                    sentiment=normalized_sentiment,
                    emotions=normalized_emotions,
                    uncertainty=round(raw_analysis['uncertainty'], 3),
                    issues=normalized_issues,
                    intent=raw_analysis['intent'],
                    created_at=datetime.utcnow()
                )
                
                logger.info(f"Results normalized - Sentiment: {normalized_sentiment}, Issues: {len(normalized_issues)}")
                
            except Exception as e:
                logger.error(f"Result normalization failed: {e}")
                return None
            
            # Step 3: Store in Supabase
            try:
                stored_result = self._store_in_supabase(insight)
                if stored_result:
                    logger.info(f"NLP results stored successfully with ID: {stored_result.get('id')}")
                    return stored_result
                else:
                    logger.error("Failed to store results in Supabase")
                    return None
                    
            except Exception as e:
                logger.error(f"Supabase storage failed: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error in analyze_and_store: {e}")
            return None
    
    def _store_in_supabase(self, insight: NLPInsight) -> Optional[Dict[str, Any]]:
        """
        Store NLP insight in Supabase test_nlp_insights table.
        
        Args:
            insight: NLPInsight object to store
            
        Returns:
            Stored record data or None if failed
        """
        try:
            # Prepare data for insertion
            insert_data = {
                'id': insight.id or str(uuid.uuid4()),  # Generate ID explicitly if not provided
                'test_id': insight.test_id,
                'sentiment': insight.sentiment,
                'emotions': insight.emotions,
                'uncertainty': insight.uncertainty,
                'issues': insight.issues,
                'intent': insight.intent,
                'created_at': insight.created_at.isoformat() if insight.created_at else datetime.utcnow().isoformat()
            }
            
            # Insert into Supabase
            result = self.supabase.table('test_nlp_insights').insert(insert_data).execute()
            
            if result.data and len(result.data) > 0:
                stored_record = result.data[0]
                logger.info(f"Successfully stored NLP insight with ID: {stored_record.get('id')}")
                return stored_record
            else:
                logger.error("Supabase insert returned no data")
                return None
                
        except Exception as e:
            error_msg = str(e)
            if "row-level security" in error_msg or "42501" in error_msg:
                # Explicitly warn about RLS
                current_key = self.supabase_key
                key_type = "SERVICE_ROLE (Trusted)" if os.getenv("SUPABASE_SERVICE_ROLE_KEY") else "ANON (Restricted)"
                key_preview = current_key[:10] + "..." if current_key else "None"
                
                logger.error(f"RLS POLICY VIOLATION: The current key ({key_type}) cannot write to 'test_nlp_insights'.")
                logger.error(f"Key used: {key_preview}")
                logger.error("Ensure SUPABASE_SERVICE_ROLE_KEY is set in .env and loaded.")
            
            logger.error(f"Error storing in Supabase: {e}")
            return None
    
    def get_insights_by_test_id(self, test_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all NLP insights for a specific test session.
        
        Args:
            test_id: Test session identifier
            
        Returns:
            List of NLP insight records
        """
        try:
            if not self._validate_test_id(test_id):
                logger.error(f"Invalid test_id format: {test_id}")
                return []
            
            result = self.supabase.table('test_nlp_insights')\
                .select('*')\
                .eq('test_id', test_id)\
                .order('created_at', desc=True)\
                .execute()
            
            if result.data:
                logger.info(f"Retrieved {len(result.data)} insights for test_id: {test_id}")
                return result.data
            else:
                logger.info(f"No insights found for test_id: {test_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving insights: {e}")
            return []
    
    def get_recent_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieve recent NLP insights for monitoring and analytics.
        
        Args:
            limit: Maximum number of records to retrieve
            
        Returns:
            List of recent NLP insight records
        """
        try:
            result = self.supabase.table('test_nlp_insights')\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            if result.data:
                logger.info(f"Retrieved {len(result.data)} recent insights")
                return result.data
            else:
                logger.info("No recent insights found")
                return []
                
        except Exception as e:
            logger.error(f"Error retrieving recent insights: {e}")
            return []


# Convenience functions for easy integration
def analyze_and_store_feedback(feedback_text: str, test_id: str) -> Optional[Dict[str, Any]]:
    """
    Convenience function to analyze feedback and store results.
    
    This function provides a simple interface for the most common use case:
    analyzing user feedback and storing the results in one call.
    
    Args:
        feedback_text: User feedback text to analyze
        test_id: UUID of the test session
        
    Returns:
        Dictionary containing stored NLP results, or None if failed
        
    Example:
        >>> result = analyze_and_store_feedback(
        ...     "The test was great but the volume was too low",
        ...     "550e8400-e29b-41d4-a716-446655440000"
        ... )
        >>> print(result['sentiment'])  # 'mixed'
    """
    try:
        storage = NLPResultsStorage()
        return storage.analyze_and_store(feedback_text, test_id)
    except Exception as e:
        logger.error(f"Error in analyze_and_store_feedback: {e}")
        return None


def get_test_insights(test_id: str) -> List[Dict[str, Any]]:
    """
    Convenience function to retrieve insights for a test session.
    
    Args:
        test_id: Test session identifier
        
    Returns:
        List of NLP insight records for the test session
    """
    try:
        storage = NLPResultsStorage()
        return storage.get_insights_by_test_id(test_id)
    except Exception as e:
        logger.error(f"Error in get_test_insights: {e}")
        return []


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    sample_feedback = "The test was confusing and I couldn't hear some of the tones clearly. The headphones were uncomfortable."
    sample_test_id = str(uuid.uuid4())
    
    print("Testing NLP Results Storage...")
    print(f"Sample feedback: {sample_feedback}")
    print(f"Sample test_id: {sample_test_id}")
    
    # Test the main function
    result = analyze_and_store_feedback(sample_feedback, sample_test_id)
    
    if result:
        print("\n✅ Success! Stored NLP results:")
        print(f"ID: {result.get('id')}")
        print(f"Sentiment: {result.get('sentiment')}")
        print(f"Emotions: {result.get('emotions')}")
        print(f"Uncertainty: {result.get('uncertainty')}")
        print(f"Issues: {result.get('issues')}")
        print(f"Intent: {result.get('intent')}")
        
        # Test retrieval
        retrieved = get_test_insights(sample_test_id)
        print(f"\n📊 Retrieved {len(retrieved)} insights for test session")
        
    else:
        print("\n❌ Failed to store NLP results")