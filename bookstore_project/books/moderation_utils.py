"""
AI-powered content moderation for book club forum.
Uses scikit-learn to classify toxic content and flag inappropriate posts/comments.
"""

import os
import pickle
import re
from typing import List, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import pandas as pd
import logging

logger = logging.getLogger(__name__)

class ContentModerator:
    """AI-powered content moderation system for forum posts and comments."""

    def __init__(self, model_path: str = 'moderation_model.pkl'):
        self.model_path = os.path.join('books', 'models', model_path)
        self.model = None
        self.vectorizer = None
        self.is_trained = False

    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for classification."""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove URLs
        text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)

        # Remove special characters and numbers
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\d+', '', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text.strip()

    def load_toxic_dataset(self) -> Tuple[List[str], List[int]]:
        """Load and prepare toxic comment dataset for training."""
        # For demo purposes, we'll create a small synthetic dataset
        # In production, you'd load from a real dataset like Jigsaw Toxic Comment Classification
        toxic_words = [
            'hate', 'stupid', 'idiot', 'dumb', 'moron', 'asshole', 'bastard', 'shit', 'fuck',
            'damn', 'hell', 'crap', 'bullshit', 'suck', 'terrible', 'awful', 'horrible',
            'worst', 'pathetic', 'useless', 'garbage', 'trash', 'jerk', 'loser'
        ]

        non_toxic_words = [
            'great', 'excellent', 'wonderful', 'amazing', 'fantastic', 'good', 'nice',
            'beautiful', 'perfect', 'awesome', 'brilliant', 'superb', 'outstanding',
            'love', 'enjoy', 'happy', 'pleased', 'satisfied', 'delighted'
        ]

        texts = []
        labels = []

        # Generate toxic examples
        for word in toxic_words:
            texts.extend([
                f"This book is {word}",
                f"The author is such a {word}",
                f"I {word} this story",
                f"What a {word} ending",
                f"This is completely {word}"
            ])
            labels.extend([1] * 5)

        # Generate non-toxic examples
        for word in non_toxic_words:
            texts.extend([
                f"This book is {word}",
                f"The author is {word}",
                f"I {word} this story",
                f"What a {word} ending",
                f"This is {word}"
            ])
            labels.extend([0] * 5)

        # Add some neutral examples
        neutral_texts = [
            "I finished reading this book yesterday",
            "The plot was interesting but predictable",
            "I would recommend this to my friends",
            "The characters were well developed",
            "The writing style was engaging",
            "I learned a lot from this book",
            "The ending was surprising",
            "This author has a unique voice",
            "I couldn't put this book down",
            "The setting was beautifully described"
        ]
        texts.extend(neutral_texts)
        labels.extend([0] * len(neutral_texts))

        return texts, labels

    def train_model(self, save_model: bool = True) -> None:
        """Train the toxicity classification model."""
        logger.info("Training content moderation model...")

        # Load dataset
        texts, labels = self.load_toxic_dataset()

        # Preprocess texts
        processed_texts = [self.preprocess_text(text) for text in texts]

        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            processed_texts, labels, test_size=0.2, random_state=42, stratify=labels
        )

        # Create pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('classifier', LogisticRegression(random_state=42, max_iter=1000))
        ])

        # Train model
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        logger.info("Model training completed")
        logger.info(f"Classification Report:\n{classification_report(y_test, y_pred)}")

        self.is_trained = True

        if save_model:
            self.save_model()

    def predict_toxicity(self, text: str, threshold: float = 0.7) -> Tuple[bool, float]:
        """
        Predict if text is toxic.

        Returns:
            Tuple of (is_toxic: bool, confidence: float)
        """
        if not self.is_trained and not self.load_model():
            logger.warning("Model not trained and no saved model found")
            return False, 0.0

        processed_text = self.preprocess_text(text)

        if not processed_text:
            return False, 0.0

        try:
            # Get prediction probabilities
            probabilities = self.model.predict_proba([processed_text])[0]
            toxic_probability = probabilities[1]  # Probability of class 1 (toxic)

            is_toxic = toxic_probability >= threshold
            return is_toxic, toxic_probability

        except Exception as e:
            logger.error(f"Error predicting toxicity: {e}")
            return False, 0.0

    def save_model(self) -> bool:
        """Save the trained model to disk."""
        if not self.is_trained:
            logger.warning("Cannot save untrained model")
            return False

        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump(self.model, f)
            logger.info(f"Model saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False

    def load_model(self) -> bool:
        """Load a trained model from disk."""
        try:
            if os.path.exists(self.model_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.is_trained = True
                logger.info(f"Model loaded from {self.model_path}")
                return True
            else:
                logger.warning(f"Model file not found: {self.model_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def moderate_content(self, content: str) -> dict:
        """
        Moderate content and return moderation result.

        Returns:
            dict with keys: 'is_approved', 'is_flagged', 'confidence', 'reason'
        """
        is_toxic, confidence = self.predict_toxicity(content)

        result = {
            'is_approved': not is_toxic,
            'is_flagged': is_toxic,
            'confidence': confidence,
            'reason': 'toxic_content' if is_toxic else None
        }

        return result

# Global moderator instance
moderator = ContentModerator()

def moderate_forum_content(content: str) -> dict:
    """
    Convenience function to moderate forum content.

    Args:
        content: The text content to moderate

    Returns:
        dict with moderation results
    """
    return moderator.moderate_content(content)

def initialize_moderator():
    """Initialize the content moderator by loading or training the model."""
    if not moderator.load_model():
        logger.info("No saved model found, training new model...")
        moderator.train_model()

# Initialize moderator when module is imported
try:
    initialize_moderator()
except Exception as e:
    logger.error(f"Failed to initialize content moderator: {e}")
