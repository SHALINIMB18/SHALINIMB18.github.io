import numpy as np
import cv2
import os
from PIL import Image
from .models import Book, UserBook
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def extract_advanced_features(image_path):
    """
    Extract advanced visual features using OpenCV and TensorFlow/Keras.
    Uses a combination of color histograms, texture features, and CNN features.
    """
    try:
        # Load image
        if isinstance(image_path, str):
            img = cv2.imread(image_path)
        else:
            # Assume PIL Image
            img = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR)

        if img is None:
            return None

        # Resize for consistent processing
        img = cv2.resize(img, (224, 224))

        features = []

        # 1. Color Histogram Features (HSV color space)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist_h = cv2.calcHist([hsv], [0], None, [16], [0, 180]).flatten()
        hist_s = cv2.calcHist([hsv], [1], None, [8], [0, 256]).flatten()
        hist_v = cv2.calcHist([hsv], [2], None, [8], [0, 256]).flatten()
        color_features = np.concatenate([hist_h, hist_s, hist_v])
        color_features = color_features / np.linalg.norm(color_features)  # Normalize
        features.extend(color_features)

        # 2. Texture Features using Gabor filters
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        texture_features = []

        # Apply Gabor filters with different orientations
        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            gabor_kernel = cv2.getGaborKernel((21, 21), 8.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(gray, cv2.CV_8UC3, gabor_kernel)
            texture_features.extend([filtered.mean(), filtered.std(), filtered.var()])

        texture_features = np.array(texture_features)
        texture_features = texture_features / np.linalg.norm(texture_features) if np.linalg.norm(texture_features) > 0 else texture_features
        features.extend(texture_features)

        # 3. Edge features using Canny
        edges = cv2.Canny(gray, 100, 200)
        edge_density = np.sum(edges > 0) / edges.size
        features.append(edge_density)

        # 4. Basic shape features
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            perimeter = cv2.arcLength(largest_contour, True)
            compactness = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            features.extend([area/10000, perimeter/1000, compactness])  # Normalize
        else:
            features.extend([0, 0, 0])

        return features

    except Exception as e:
        logger.error(f"Error extracting advanced features: {e}")
        return None

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b) if norm_a != 0 and norm_b != 0 else 0

def find_similar_books_advanced(uploaded_image, top_n=5):
    """
    Find visually similar books using advanced feature extraction.

    Args:
        uploaded_image: PIL Image or file path
        top_n: Number of top results to return

    Returns:
        list: List of (book, similarity_score) tuples
    """
    try:
        # Extract features from uploaded image
        if hasattr(uploaded_image, 'read'):  # File-like object
            img = Image.open(uploaded_image)
            uploaded_features = extract_advanced_features(img)
        else:  # Assume it's a path or PIL Image
            uploaded_features = extract_advanced_features(uploaded_image)

        if uploaded_features is None:
            logger.warning("Could not extract features from uploaded image")
            return []

        uploaded_features = np.array(uploaded_features)

        # Use caching for book features
        cache_key = f"advanced_visual_search_{hash(str(uploaded_features[:10]))}_{top_n}"
        cached_results = cache.get(cache_key)
        if cached_results:
            return cached_results

        similarities = []

        # Compare with Book model
        books_with_features = Book.objects.exclude(image_features__isnull=True)
        for book in books_with_features:
            try:
                book_features = np.array(book.image_features)
                similarity = cosine_similarity(uploaded_features, book_features)
                similarities.append((book, similarity))
            except (ValueError, TypeError) as e:
                logger.error(f"Error comparing with book {book.id}: {e}")
                continue

        # Compare with UserBook model
        user_books_with_features = UserBook.objects.filter(is_available=True).exclude(image_features__isnull=True)
        for user_book in user_books_with_features:
            try:
                book_features = np.array(user_book.image_features)
                similarity = cosine_similarity(uploaded_features, book_features)
                similarities.append((user_book, similarity))
            except (ValueError, TypeError) as e:
                logger.error(f"Error comparing with user_book {user_book.id}: {e}")
                continue

        # Sort by similarity (higher is better)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Cache results
        results = similarities[:top_n]
        cache.set(cache_key, results, 60 * 30)  # Cache for 30 minutes

        logger.info(f"Advanced visual search found {len(results)} results")
        return results

    except Exception as e:
        logger.error(f"Error in advanced visual search: {e}")
        return []
