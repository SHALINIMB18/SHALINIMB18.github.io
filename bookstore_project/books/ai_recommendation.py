import pickle
import os
import math
from collections import Counter
import pandas as pd
from .models import Book

def cosine_similarity_manual(a, b):
    """Compute cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x ** 2 for x in a))
    norm_b = math.sqrt(sum(y ** 2 for y in b))
    return dot_product / (norm_a * norm_b) if norm_a != 0 and norm_b != 0 else 0

def compute_tf_idf(documents):
    """Compute TF-IDF vectors for a list of documents."""
    # Tokenize documents (simple split for now, can be enhanced with nltk)
    tokenized_docs = [doc.lower().split() for doc in documents]

    # Compute document frequency
    df = Counter()
    for doc in tokenized_docs:
        unique_words = set(doc)
        for word in unique_words:
            df[word] += 1

    # Compute TF-IDF
    tfidf_vectors = []
    num_docs = len(documents)
    for doc in tokenized_docs:
        tf = Counter(doc)
        tfidf_vector = {}
        for word in tf:
            tf_val = tf[word] / len(doc)
            idf_val = math.log(num_docs / df[word])
            tfidf_vector[word] = tf_val * idf_val
        tfidf_vectors.append(tfidf_vector)

    return tfidf_vectors

MODEL_PATH = 'store/ai_models/model.pkl'

def train_recommendation_model():
    """Train and save the recommendation model based on book categories and authors."""
    books = Book.objects.all().values('id', 'title', 'author', 'category', 'genre')
    if not books:
        return

    df = pd.DataFrame(books)
    df['features'] = df['category'] + ' ' + df['genre'] + ' ' + df['author']

    # Compute TF-IDF manually
    documents = df['features'].tolist()
    tfidf_vectors = compute_tf_idf(documents)

    # Simple clustering replacement: group by category for now (can be enhanced)
    categories = df['category'].tolist()
    unique_categories = list(set(categories))
    category_clusters = {cat: i for i, cat in enumerate(unique_categories)}

    model_data = {
        'tfidf_vectors': tfidf_vectors,
        'book_ids': df['id'].tolist(),
        'features': df['features'].tolist(),
        'categories': categories,
        'category_clusters': category_clusters
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model_data, f)

def get_recommendations(book_id, top_n=5):
    """Get book recommendations based on category, author, and genre similarity."""
    from django.core.cache import cache
    import logging
    logger = logging.getLogger(__name__)

    # Try to get recommendations from cache first
    cache_key = f'book_recommendations_{book_id}'
    cached_recommendations = cache.get(cache_key)
    if cached_recommendations:
        return cached_recommendations

    if not os.path.exists(MODEL_PATH):
        try:
            train_recommendation_model()
        except Exception as e:
            logger.error(f"Failed to train recommendation model: {e}")
            default_recommendations = Book.objects.all()[:top_n]
            cache.set(cache_key, default_recommendations, 60 * 30)  # Cache for 30 minutes
            return default_recommendations

    try:
        with open(MODEL_PATH, 'rb') as f:
            model_data = pickle.load(f)

        tfidf_vectors = model_data['tfidf_vectors']
        book_ids = model_data['book_ids']
        features = model_data['features']
        categories = model_data['categories']
        category_clusters = model_data['category_clusters']

        if book_id not in book_ids:
            logger.warning(f"Book ID {book_id} not found in trained model")
            default_recommendations = Book.objects.all()[:top_n]
            cache.set(cache_key, default_recommendations, 60 * 30)
            return default_recommendations

        book_index = book_ids.index(book_id)
        book_category = categories[book_index]
        book_vector = tfidf_vectors[book_index]

        # Find similar books by cosine similarity
        similarities = []
        for i, (other_id, other_vector, other_category) in enumerate(zip(book_ids, tfidf_vectors, categories)):
            if other_id == book_id:
                continue
            # Boost similarity if same category
            similarity = cosine_similarity_manual(list(book_vector.values()), list(other_vector.values()))
            if other_category == book_category:
                similarity *= 1.5  # Boost for same category
            similarities.append((other_id, similarity))

        # Sort by similarity and get top recommendations
        similarities.sort(key=lambda x: x[1], reverse=True)
        recommended_ids = [book_id for book_id, sim in similarities[:top_n]]
        recommended_books = list(Book.objects.filter(id__in=recommended_ids))

        # Cache the recommendations
        cache.set(cache_key, recommended_books, 60 * 30)  # Cache for 30 minutes
        return recommended_books

    except Exception as e:
        logger.error(f"Error in recommendation system: {e}")
        default_recommendations = Book.objects.all()[:top_n]
        cache.set(cache_key, default_recommendations, 60 * 30)
        return default_recommendations
