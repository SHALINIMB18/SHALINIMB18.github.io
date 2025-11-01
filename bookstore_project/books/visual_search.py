import numpy as np
import os
import requests
from io import BytesIO
from PIL import Image
from .models import Book, UserBook

def cosine_similarity_manual(a, b):
    """Compute cosine similarity between two vectors."""
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b) if norm_a != 0 and norm_b != 0 else 0

def extract_features_from_image(img):
    """Extract features from PIL Image using simple color histogram."""
    # Convert to RGB if necessary to ensure consistent feature dimensions
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img = img.resize((64, 64))
    img_array = np.array(img)
    # Simple feature extraction: flatten and normalize
    features = img_array.flatten() / 255.0
    return features.tolist()

def extract_features_from_url(image_url):
    """Extract features from image URL."""
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
        return extract_features_from_image(img)
    except requests.RequestException as e:
        print(f"Error extracting features from URL {image_url}: {e}")
        return None

def extract_features_from_path(img_path):
    """Extract features from local image path."""
    try:
        img = Image.open(img_path)
        return extract_features_from_image(img)
    except (OSError, ValueError) as e:
        print(f"Error extracting features from path {img_path}: {e}")
        return None

def find_similar_books_enhanced(uploaded_image, top_n=5):
    """Find visually similar books using simple features and cosine similarity."""
    from django.core.cache import cache
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Extract features from uploaded image
        if hasattr(uploaded_image, 'read'):  # File-like object
            img = Image.open(uploaded_image)
            uploaded_features = extract_features_from_image(img)
        else:  # Assume it's a path
            uploaded_features = extract_features_from_path(uploaded_image)

        if uploaded_features is None:
            logger.warning("Could not extract features from uploaded image")
            return Book.objects.all()[:top_n]

        uploaded_features = np.array(uploaded_features).reshape(1, -1)

        # Use caching for book features
        cache_key = 'book_features'
        cached_features = cache.get(cache_key)

        if cached_features is None:
            # Get all books with features using select_related for optimization
            books_with_features = Book.objects.exclude(image_features__isnull=True).select_related()
            user_books_with_features = UserBook.objects.filter(
                is_available=True
            ).exclude(
                image_features__isnull=True
            ).select_related('seller')

            # Pre-process all features
            book_features = []
            for book in books_with_features:
                try:
                    features = np.array(book.image_features).reshape(1, -1)
                    book_features.append((book, features, 'book'))
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing book {book.id}: {e}")
                    continue

            for user_book in user_books_with_features:
                try:
                    features = np.array(user_book.image_features).reshape(1, -1)
                    book_features.append((user_book, features, 'user_book'))
                except (ValueError, TypeError) as e:
                    logger.error(f"Error processing user_book {user_book.id}: {e}")
                    continue

            cache.set(cache_key, book_features, 60 * 15)  # Cache for 15 minutes
            cached_features = book_features

        # Calculate similarities using vectorized operations
        similarities = []
        for book, features, book_type in cached_features:
            try:
                similarity = cosine_similarity_manual(uploaded_features.flatten(), features.flatten())
                if similarity > 0.5:  # Only include reasonably similar items
                    similarities.append((book, similarity, book_type))
            except (ValueError, TypeError) as e:
                logger.error(f"Error calculating similarity for {book_type} {book.id}: {e}")
                continue

        # Sort by similarity (higher is better)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Log the results
        logger.info(f"Found {len(similarities)} similar books")
        return similarities[:top_n]

    except Exception as e:
        logger.error(f"Error in enhanced visual search: {e}")
        return []

# Legacy function for backward compatibility
def extract_features(img_path):
    """Extract features from image using simple features."""
    return extract_features_from_path(img_path)

def find_similar_books(uploaded_image_path, top_n=5):
    """Find visually similar books based on simple features using cosine similarity."""
    try:
        uploaded_features = extract_features_from_path(uploaded_image_path)
        if uploaded_features is None:
            return Book.objects.all()[:top_n]

        uploaded_features = np.array(uploaded_features).reshape(1, -1)

        # Get all books with features
        books_with_features = Book.objects.exclude(image_features__isnull=True)
        user_books_with_features = UserBook.objects.filter(is_available=True).exclude(image_features__isnull=True)

        similarities = []

        # Compare with Book model
        for book in books_with_features:
            try:
                book_features = np.array(book.image_features).reshape(1, -1)
                similarity = cosine_similarity_manual(uploaded_features.flatten(), book_features.flatten())
                similarities.append((book, similarity))
            except (ValueError, TypeError) as e:
                print(f"Error comparing with book {book.id}: {e}")
                continue

        # Compare with UserBook model
        for user_book in user_books_with_features:
            try:
                book_features = np.array(user_book.image_features).reshape(1, -1)
                similarity = cosine_similarity_manual(uploaded_features.flatten(), book_features.flatten())
                similarities.append((user_book, similarity))
            except (ValueError, TypeError) as e:
                print(f"Error comparing with user_book {user_book.id}: {e}")
                continue

        # Sort by similarity (higher is better)
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [book for book, sim in similarities[:top_n]]

    except Exception as e:
        print(f"Error in visual search: {e}")
        return Book.objects.all()[:top_n]
