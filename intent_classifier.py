# intent_classifier.py - Enhanced intent classification with better training data
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pandas as pd
import joblib
import numpy as np
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

MODEL_NAME = "all-MiniLM-L6-v2"
CLF_FILE = "intent_clf.pkl"
EMBEDDER_FILE = "intent_embedder.pkl"

# Initialize embedder
try:
    embedder = SentenceTransformer(MODEL_NAME)
except Exception as e:
    logger.error(f"Failed to load sentence transformer: {e}")
    embedder = None

# Enhanced training data with more examples
ENHANCED_TRAINING_DATA = [
    # Calendar/Scheduling
    ("schedule meeting tomorrow at 4pm about project", "calendar_event"),
    ("schedule football practice next monday at 7 am", "calendar_event"),
    ("set a reminder for doctor's appointment at 5pm", "calendar_event"),
    ("remind me to call mom this evening", "calendar_event"),
    ("book meeting with shreya on friday 3pm", "calendar_event"),
    ("plan team standup for next tuesday 10am", "calendar_event"),
    ("arrange client call for thursday 2pm", "calendar_event"),
    ("schedule project review meeting tomorrow", "calendar_event"),
    ("set up interview with candidate next week", "calendar_event"),
    ("book conference room for presentation friday", "calendar_event"),
    
    # Calendar viewing
    ("show my schedule", "calendar_list"),
    ("what's on my calendar tomorrow", "calendar_list"),
    ("list my upcoming events", "calendar_list"),
    ("check my appointments for today", "calendar_list"),
    ("display calendar for next week", "calendar_list"),
    ("show me my meetings tomorrow", "calendar_list"),
    
    # Email sending
    ("send email to sid about football saying bring shoes", "send_email"),
    ("send email to shreya saying we have class at 9am", "send_email"),
    ("send email to pratham about project review", "send_email"),
    ("compose a mail to sid about the function", "send_email"),
    ("email shreya saying happy birthday", "send_email"),
    ("mail the team about meeting cancellation", "send_email"),
    ("send notification to all students about exam", "send_email"),
    ("compose email to faculty about schedule change", "send_email"),
    ("email reminder to team about deadline", "send_email"),
    ("send update to client about project status", "send_email"),
    
    # Knowledge base queries
    ("what is artificial intelligence", "rag_query"),
    ("tell me about project nova", "rag_query"),
    ("kb search quantum shield", "rag_query"),
    ("define machine learning", "rag_query"),
    ("explain neural networks", "rag_query"),
    ("search knowledge base for deep learning", "rag_query"),
    ("lookup information about data science", "rag_query"),
    ("find details about computer vision", "rag_query"),
    ("query kb about natural language processing", "rag_query"),
    
    # Web search
    ("search for latest football news", "web_search"),
    ("google weather in mangalore", "web_search"),
    ("find python tutorials", "web_search"),
    ("who is the prime minister of india", "web_search"),
    ("lookup latest AI research papers", "web_search"),
    ("search for machine learning courses", "web_search"),
    ("find restaurants near me", "web_search"),
    ("google stock market updates", "web_search"),
    ("search for flight tickets to bangalore", "web_search"),
    ("find movie showtimes", "web_search"),
    
    # Application launching
    ("open notepad", "launch_app"),
    ("run calculator", "launch_app"),
    ("launch chrome", "launch_app"),
    ("start spotify", "launch_app"),
    ("open visual studio code", "launch_app"),
    ("run powerpoint", "launch_app"),
    ("launch terminal", "launch_app"),
    ("start zoom", "launch_app"),
    ("open file explorer", "launch_app"),
    ("run cmd", "launch_app"),
    
    # Website opening
    ("open youtube.com", "web_search"),
    ("open github.com", "web_search"),
    ("visit stackoverflow.com", "web_search"),
    ("go to google.com", "web_search"),
    ("open linkedin.com", "web_search"),
    
    # File management
    ("list files in current directory", "file_manage"),
    ("create new folder called projects", "file_manage"),
    ("move file to documents folder", "file_manage"),
    ("delete old backup files", "file_manage"),
    ("rename presentation file", "file_manage"),
    ("copy files to external drive", "file_manage"),
    ("organize downloads folder", "file_manage"),
    ("backup important documents", "file_manage"),
    
    # Workflow triggers
    ("workflow trigger: dir", "workflow_trigger"),
    ("trigger n8n workflow for report generation", "workflow_trigger"),
    ("automate sending invoice", "workflow_trigger"),
    ("workflow: backup files", "workflow_trigger"),
    ("run automation script", "workflow_trigger"),
    ("execute batch process", "workflow_trigger"),
    ("trigger data sync workflow", "workflow_trigger"),
    
    # Exit commands
    ("exit", "exit"),
    ("quit", "exit"),
    ("goodbye", "exit"),
    ("close", "exit"),
    ("stop", "exit"),
    ("terminate", "exit"),
]

def create_enhanced_training_data() -> pd.DataFrame:
    """Create enhanced training dataset"""
    # Load existing data if available
    existing_data = []
    try:
        if os.path.exists("intent_data.csv"):
            existing_df = pd.read_csv("intent_data.csv")
            existing_data = list(zip(existing_df["text"], existing_df["intent"]))
    except Exception as e:
        logger.warning(f"Could not load existing training data: {e}")
    
    # Combine with enhanced data
    all_data = existing_data + ENHANCED_TRAINING_DATA
    
    # Remove duplicates
    unique_data = list(set(all_data))
    
    df = pd.DataFrame(unique_data, columns=["text", "intent"])
    return df

def train_intent_classifier(save_model=True) -> LogisticRegression:
    """Train the intent classifier with enhanced data"""
    if embedder is None:
        raise ValueError("Sentence transformer not available")
    
    # Create training data
    df = create_enhanced_training_data()
    logger.info(f"Training with {len(df)} examples")
    
    # Prepare features and labels
    X = df["text"].tolist()
    y = df["intent"].tolist()
    
    # Create embeddings
    logger.info("Creating embeddings...")
    X_emb = embedder.encode(X, convert_to_numpy=True, show_progress_bar=True)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_emb, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train classifier
    logger.info("Training classifier...")
    clf = LogisticRegression(
        max_iter=1000,
        random_state=42,
        class_weight='balanced'  # Handle class imbalance
    )
    clf.fit(X_train, y_train)
    
    # Evaluate
    train_score = clf.score(X_train, y_train)
    test_score = clf.score(X_test, y_test)
    
    logger.info(f"Training accuracy: {train_score:.3f}")
    logger.info(f"Test accuracy: {test_score:.3f}")
    
    # Detailed evaluation
    y_pred = clf.predict(X_test)
    logger.info("\nClassification Report:")
    logger.info(classification_report(y_test, y_pred))
    
    if save_model:
        # Save classifier
        joblib.dump(clf, CLF_FILE)
        logger.info(f"Classifier saved to {CLF_FILE}")
        
        # Save training data for future reference
        df.to_csv("enhanced_intent_data.csv", index=False)
        logger.info("Enhanced training data saved")
    
    return clf

def predict_intent(text: str) -> Tuple[str, float]:
    """Predict intent with confidence score"""
    if embedder is None:
        logger.error("Sentence transformer not available")
        return "unknown", 0.0
    
    try:
        # Load classifier
        clf = joblib.load(CLF_FILE)
        
        # Create embedding
        emb = embedder.encode([text], convert_to_numpy=True)
        
        # Predict
        probs = clf.predict_proba(emb)[0]
        label = clf.classes_[probs.argmax()]
        confidence = float(probs.max())
        
        # Apply confidence threshold
        if confidence < 0.3:
            label = "unknown"
            confidence = 0.0
        
        return label, confidence
        
    except FileNotFoundError:
        logger.warning("Intent classifier not found. Training new one...")
        clf = train_intent_classifier()
        return predict_intent(text)  # Retry prediction
        
    except Exception as e:
        logger.error(f"Intent prediction error: {e}")
        return "unknown", 0.0

def predict_top_intents(text: str, top_k: int = 3) -> List[Tuple[str, float]]:
    """Get top-k intent predictions with confidence scores"""
    if embedder is None:
        return [("unknown", 0.0)]
    
    try:
        clf = joblib.load(CLF_FILE)
        emb = embedder.encode([text], convert_to_numpy=True)
        probs = clf.predict_proba(emb)[0]
        
        # Get top-k predictions
        top_indices = np.argsort(probs)[::-1][:top_k]
        top_predictions = [
            (clf.classes_[idx], float(probs[idx])) 
            for idx in top_indices
        ]
        
        return top_predictions
        
    except Exception as e:
        logger.error(f"Top-k intent prediction error: {e}")
        return [("unknown", 0.0)]

def get_intent_examples(intent: str, num_examples: int = 5) -> List[str]:
    """Get example phrases for a given intent"""
    examples = []
    for text, intent_label in ENHANCED_TRAINING_DATA:
        if intent_label == intent:
            examples.append(text)
        if len(examples) >= num_examples:
            break
    
    return examples

def validate_classifier_performance() -> dict:
    """Validate classifier performance on test data"""
    if embedder is None:
        return {"error": "Embedder not available"}
    
    try:
        # Load test data
        df = create_enhanced_training_data()
        X = df["text"].tolist()
        y = df["intent"].tolist()
        
        # Create embeddings
        X_emb = embedder.encode(X, convert_to_numpy=True)
        
        # Load classifier
        clf = joblib.load(CLF_FILE)
        
        # Predict
        y_pred = clf.predict(X_emb)
        y_prob = clf.predict_proba(X_emb)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support
        
        accuracy = accuracy_score(y, y_pred)
        precision, recall, f1, support = precision_recall_fscore_support(y, y_pred, average='weighted')
        
        # Per-class metrics
        unique_labels = sorted(set(y))
        per_class_metrics = {}
        
        for label in unique_labels:
            label_indices = [i for i, true_label in enumerate(y) if true_label == label]
            if label_indices:
                label_probs = [y_prob[i][list(clf.classes_).index(label)] for i in label_indices]
                avg_confidence = np.mean(label_probs)
                per_class_metrics[label] = {
                    "count": len(label_indices),
                    "avg_confidence": float(avg_confidence)
                }
        
        return {
            "accuracy": float(accuracy),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
            "per_class_metrics": per_class_metrics,
            "total_samples": len(y)
        }
        
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return {"error": str(e)}

def retrain_with_feedback(feedback_data: List[Tuple[str, str, bool]]):
    """Retrain classifier with user feedback data"""
    # feedback_data: [(text, predicted_intent, was_correct), ...]
    
    # Load existing training data
    df = create_enhanced_training_data()
    
    # Add correctly predicted examples to training data
    new_examples = []
    for text, predicted_intent, was_correct in feedback_data:
        if was_correct:
            new_examples.append((text, predicted_intent))
    
    if new_examples:
        # Add to dataframe
        new_df = pd.DataFrame(new_examples, columns=["text", "intent"])
        df = pd.concat([df, new_df], ignore_index=True)
        
        # Remove duplicates
        df = df.drop_duplicates()
        
        # Retrain
        logger.info(f"Retraining with {len(new_examples)} new examples")
        X = df["text"].tolist()
        y = df["intent"].tolist()
        
        X_emb = embedder.encode(X, convert_to_numpy=True)
        
        clf = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
        clf.fit(X_emb, y)
        
        # Save updated model
        joblib.dump(clf, CLF_FILE)
        df.to_csv("enhanced_intent_data.csv", index=False)
        
        logger.info("Classifier retrained with feedback")

import os

if __name__ == "__main__":
    print("Training enhanced intent classifier...")
    train_intent_classifier()
    
    # Test predictions
    test_phrases = [
        "schedule meeting tomorrow",
        "send email to team",
        "what is machine learning",
        "open notepad",
        "search for news"
    ]
    
    print("\nTest predictions:")
    for phrase in test_phrases:
        intent, confidence = predict_intent(phrase)
        print(f"'{phrase}' -> {intent} (confidence: {confidence:.3f})")