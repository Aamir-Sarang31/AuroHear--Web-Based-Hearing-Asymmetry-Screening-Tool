from transformers import pipeline
import re

sentiment_model = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english"
)

emotion_model = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=True
)

def clean_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text

UNCERTAINTY_PHRASES = [
    "not sure", "maybe", "i think", "couldnt tell", "probably", "not certain"
]

ISSUE_KEYWORDS = {
    "audibility": ["couldnt hear", "too soft", "low volume", "not loud"],
    "noise": ["noisy", "background", "disturbance"],
    "delay": ["delay", "lag", "slow"],
    "confusion": ["confusing", "unclear", "hard to understand"],
    "device": ["headphone", "earphone", "speaker"]
}

def detect_uncertainty(text):
    score = 0
    for phrase in UNCERTAINTY_PHRASES:
        if phrase in text:
            score += 1
    return min(score / len(UNCERTAINTY_PHRASES), 1.0)

def extract_issues(text):
    issues = []
    for issue, words in ISSUE_KEYWORDS.items():
        for w in words:
            if w in text:
                issues.append(issue)
                break
    return issues

def detect_intent(text):
    if any(w in text for w in ["couldnt", "noisy", "delay", "problem", "issue"]):
        return "report_problem"
    if any(w in text for w in ["good", "nice", "smooth", "easy"]):
        return "positive_experience"
    return "neutral_comment"

def analyze_feedback(raw_text):
    text = clean_text(raw_text)

    sentiment = sentiment_model(text)[0]
    emotions = emotion_model(text)[0]
    uncertainty = detect_uncertainty(text)
    issues = extract_issues(text)
    intent = detect_intent(text)

    return {
        "sentiment": sentiment,
        "emotions": emotions,
        "uncertainty": uncertainty,
        "issues": issues,
        "intent": intent
    }

if __name__ == "__main__":
    sample = "I wasn't sure I heard the sound. The room was noisy and the headphones were uncomfortable."
    result = analyze_feedback(sample)
    print("\nNLP OUTPUT:\n", result)

