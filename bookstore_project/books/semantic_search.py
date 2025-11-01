import numpy as np
import os
from sentence_transformers import SentenceTransformer
from .models import Book, UserBook
from django.core.cache import cache
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

# Global model variable
_model = None

def get_sentence_transformer_model():
    """Load and cache the Sentence-BERT model."""
    global _model
    if _model is None:
        try:
            # Use a smaller, efficient model for semantic search
            _model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence-BERT model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Sentence-BERT model: {e}")
            return None
    return _model

def compute_semantic_embedding(text):
    """Compute semantic embedding for a given text."""
    model = get_sentence_transformer_model()
    if model is None:
        return None

    try:
        # Clean and prepare text
        text = str(text).strip()
        if not text:
            return None

        # Generate embedding
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error computing semantic embedding: {e}")
        return None

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a = np.array(a)
    b = np.array(b)
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    return dot_product / (norm_a * norm_b) if norm_a != 0 and norm_b != 0 else 0

def semantic_search_books(query, top_n=10):
    """
    Perform semantic search on books using Sentence-BERT embeddings.

    Args:
        query (str): The search query
        top_n (int): Number of top results to return

    Returns:
        list: List of (book, similarity_score) tuples
    """
    from django.core.cache import cache
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Check cache first
        cache_key = f"semantic_search_{hash(query)}_{top_n}"
        cached_results = cache.get(cache_key)
        if cached_results:
            return cached_results

        # Compute query embedding
        query_embedding = compute_semantic_embedding(query)
        if query_embedding is None:
            logger.warning("Could not compute embedding for query")
            return []

        # Get all books with semantic embeddings
        books_with_embeddings = Book.objects.exclude(semantic_embedding__isnull=True).exclude(semantic_embedding__exact=[])

        similarities = []

        for book in books_with_embeddings:
            try:
                book_embedding = book.semantic_embedding
                if book_embedding:
                    similarity = cosine_similarity(query_embedding, book_embedding)
                    similarities.append((book, similarity))
            except Exception as e:
                logger.error(f"Error computing similarity for book {book.id}: {e}")
                continue

        # Also search UserBook model
        user_books_with_embeddings = UserBook.objects.filter(is_available=True).exclude(semantic_embedding__isnull=True).exclude(semantic_embedding__exact=[])

        for user_book in user_books_with_embeddings:
            try:
                book_embedding = user_book.semantic_embedding
                if book_embedding:
                    similarity = cosine_similarity(query_embedding, book_embedding)
                    similarities.append((user_book, similarity))
            except Exception as e:
                logger.error(f"Error computing similarity for user_book {user_book.id}: {e}")
                continue

        # Sort by similarity (higher is better)
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Cache results for 30 minutes
        cache.set(cache_key, similarities[:top_n], 60 * 30)

        logger.info(f"Semantic search found {len(similarities)} results for query: {query}")
        return similarities[:top_n]

    except Exception as e:
        logger.error(f"Error in semantic search: {e}")
        return []

def precompute_book_embeddings():
    """
    Precompute semantic embeddings for all books that don't have them.
    This should be run as a management command.
    """
    logger.info("Starting precomputation of semantic embeddings")

    # Process Book model
    books_without_embeddings = Book.objects.filter(
        Q(semantic_embedding__isnull=True) | Q(semantic_embedding__exact=[])
    )

    updated_books = 0
    for book in books_without_embeddings:
        # Create a rich text representation for embedding
        text_content = f"{book.title} {book.author} {book.genre} {book.category} {book.description}"
        embedding = compute_semantic_embedding(text_content)

        if embedding:
            book.semantic_embedding = embedding
            book.save()
            updated_books += 1
            logger.info(f"Computed embedding for book: {book.title}")

    # Process UserBook model
    user_books_without_embeddings = UserBook.objects.filter(
        is_available=True
    ).filter(
        Q(semantic_embedding__isnull=True) | Q(semantic_embedding__exact=[])
    )

    updated_user_books = 0
    for user_book in user_books_without_embeddings:
        text_content = f"{user_book.title} {user_book.author} {user_book.genre} {user_book.category} {user_book.description}"
        embedding = compute_semantic_embedding(text_content)

        if embedding:
            user_book.semantic_embedding = embedding
            user_book.save()
            updated_user_books += 1
            logger.info(f"Computed embedding for user book: {user_book.title}")

    logger.info(f"Precomputed embeddings for {updated_books} books and {updated_user_books} user books")
    return updated_books, updated_user_books
