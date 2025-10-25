import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
import pandas as pd
from .models import Book

MODEL_PATH = 'store/ai_models/model.pkl'

def train_recommendation_model():
    """Train and save the recommendation model based on book categories and authors."""
    books = Book.objects.all().values('id', 'title', 'author', 'category', 'genre')
    if not books:
        return

    df = pd.DataFrame(books)
    df['features'] = df['category'] + ' ' + df['genre'] + ' ' + df['author']

    vectorizer = TfidfVectorizer(stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(df['features'])

    kmeans = KMeans(n_clusters=min(10, len(df)), random_state=42)
    kmeans.fit(tfidf_matrix)

    model_data = {
        'vectorizer': vectorizer,
        'kmeans': kmeans,
        'book_ids': df['id'].tolist(),
        'features': df['features'].tolist()
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

        vectorizer = model_data['vectorizer']
        kmeans = model_data['kmeans']
        book_ids = model_data['book_ids']
        features = model_data['features']

        if book_id not in book_ids:
            logger.warning(f"Book ID {book_id} not found in trained model")
            default_recommendations = Book.objects.all()[:top_n]
            cache.set(cache_key, default_recommendations, 60 * 30)
            return default_recommendations

        book_index = book_ids.index(book_id)
        book_vector = vectorizer.transform([features[book_index]])
        cluster = kmeans.predict(book_vector)[0]

        # Get books in the same cluster using vectorized operations
        all_vectors = vectorizer.transform(features)
        all_clusters = kmeans.predict(all_vectors)
        cluster_mask = (all_clusters == cluster) & (pd.Series(book_ids) != book_id)
        cluster_books = pd.Series(book_ids)[cluster_mask].tolist()[:top_n]

        recommended_books = list(Book.objects.filter(id__in=cluster_books))
        
        # Cache the recommendations
        cache.set(cache_key, recommended_books, 60 * 30)  # Cache for 30 minutes
        return recommended_books

    except Exception as e:
        logger.error(f"Error in recommendation system: {e}")
        default_recommendations = Book.objects.all()[:top_n]
        cache.set(cache_key, default_recommendations, 60 * 30)
        return default_recommendations
