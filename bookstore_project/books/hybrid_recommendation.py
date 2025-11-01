import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from .models import Book, Review, Order, UserProfile, UserBook
from django.db.models import Avg, Count
from django.core.cache import cache
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

def build_user_item_matrix():
    """Build user-item interaction matrix for collaborative filtering."""
    # Get all orders (purchases)
    orders = Order.objects.filter(status__in=['delivered', 'confirmed']).select_related('user', 'book', 'user_book')

    # Create user-item matrix
    user_item_data = defaultdict(lambda: defaultdict(float))

    for order in orders:
        user_id = order.user.id
        if order.book:
            item_id = f"book_{order.book.id}"
            user_item_data[user_id][item_id] = 1.0  # Purchased
        elif order.user_book:
            item_id = f"user_book_{order.user_book.id}"
            user_item_data[user_id][item_id] = 1.0

    # Convert to DataFrame
    if user_item_data:
        df = pd.DataFrame.from_dict(user_item_data, orient='index').fillna(0)
        return df
    return pd.DataFrame()

def build_content_features():
    """Build content-based features for books."""
    books = Book.objects.all()
    user_books = UserBook.objects.filter(is_available=True)

    features = []

    for book in books:
        feature_dict = {
            'id': f"book_{book.id}",
            'title': book.title or '',
            'author': book.author or '',
            'genre': book.genre or '',
            'category': book.category or '',
            'rating': book.rating or 0.0,
            'price': float(book.price or 0.0),
            'description': book.description or '',
            'type': 'book'
        }
        features.append(feature_dict)

    for user_book in user_books:
        feature_dict = {
            'id': f"user_book_{user_book.id}",
            'title': user_book.title or '',
            'author': user_book.author or '',
            'genre': user_book.genre or '',
            'category': user_book.category or '',
            'rating': 0.0,  # User books don't have ratings
            'price': float(user_book.price or 0.0),
            'description': user_book.description or '',
            'type': 'user_book'
        }
        features.append(feature_dict)

    return pd.DataFrame(features)

def calculate_content_similarity(content_df):
    """Calculate content similarity matrix using TF-IDF and cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    # Combine text features
    content_df['combined_text'] = content_df.apply(
        lambda x: f"{x['title']} {x['author']} {x['genre']} {x['category']} {x['description']}",
        axis=1
    )

    # TF-IDF vectorization
    tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
    tfidf_matrix = tfidf.fit_transform(content_df['combined_text'])

    # Calculate cosine similarity
    similarity_matrix = cosine_similarity(tfidf_matrix)

    return similarity_matrix, content_df['id'].tolist()

def hybrid_recommendation(user_id, book_id=None, top_n=10):
    """Generate hybrid recommendations combining collaborative and content-based filtering."""
    try:
        # Get cached matrices
        cache_key = 'recommendation_matrices'
        cached_data = cache.get(cache_key)

        if cached_data is None:
            # Build matrices
            user_item_df = build_user_item_matrix()
            content_df = build_content_features()
            similarity_matrix, item_ids = calculate_content_similarity(content_df)

            cached_data = {
                'user_item_df': user_item_df,
                'content_df': content_df,
                'similarity_matrix': similarity_matrix,
                'item_ids': item_ids
            }
            cache.set(cache_key, cached_data, 60 * 30)  # Cache for 30 minutes
        else:
            user_item_df = cached_data['user_item_df']
            content_df = cached_data['content_df']
            similarity_matrix = cached_data['similarity_matrix']
            item_ids = cached_data['item_ids']

        recommendations = []

        # Collaborative filtering component
        if user_id in user_item_df.index and not user_item_df.empty:
            user_ratings = user_item_df.loc[user_id]
            similar_users = user_item_df.corrwith(user_ratings).sort_values(ascending=False).dropna()

            # Get recommendations from similar users
            collab_recs = defaultdict(float)
            for similar_user, similarity in similar_users.head(10).items():
                if similarity > 0.1:
                    similar_user_ratings = user_item_df.loc[similar_user]
                    unrated_items = similar_user_ratings[similar_user_ratings > 0] - user_ratings[user_ratings > 0]
                    for item, rating in unrated_items.items():
                        collab_recs[item] += similarity * rating

            # Sort collaborative recommendations
            collab_sorted = sorted(collab_recs.items(), key=lambda x: x[1], reverse=True)
            recommendations.extend([(item, score, 'collaborative') for item, score in collab_sorted[:top_n//2]])

        # Content-based component
        if book_id:
            try:
                # Find similar books by content
                book_idx = item_ids.index(f"book_{book_id}")
                similar_scores = similarity_matrix[book_idx]
                content_recs = [(item_ids[i], score) for i, score in enumerate(similar_scores) if score > 0.1 and i != book_idx]
                content_recs.sort(key=lambda x: x[1], reverse=True)

                recommendations.extend([(item, score, 'content') for item, score in content_recs[:top_n//2]])
            except (ValueError, IndexError):
                pass

        # Combine and deduplicate
        seen_items = set()
        final_recs = []

        for item, score, method in recommendations:
            if item not in seen_items:
                final_recs.append((item, score, method))
                seen_items.add(item)
                if len(final_recs) >= top_n:
                    break

        # Convert to Book/UserBook objects
        result = []
        for item_id, score, method in final_recs:
            try:
                if item_id.startswith('book_'):
                    book_id_int = int(item_id.split('_')[1])
                    book = Book.objects.get(id=book_id_int)
                    result.append(book)
                elif item_id.startswith('user_book_'):
                    user_book_id = int(item_id.split('_')[2])
                    user_book = UserBook.objects.get(id=user_book_id)
                    result.append(user_book)
            except (Book.DoesNotExist, UserBook.DoesNotExist, ValueError):
                continue

        return result

    except Exception as e:
        logger.error(f"Error in hybrid recommendation: {e}")
        # Fallback to simple popularity-based recommendations
        return get_popular_books(top_n)

def get_recommendations(book_id, top_n=5):
    """Legacy function for backward compatibility."""
    try:
        book = Book.objects.get(id=book_id)
        # Use hybrid recommendation with None user (content-based only)
        return hybrid_recommendation(None, book_id, top_n)
    except Book.DoesNotExist:
        return []

def get_popular_books(top_n=10):
    """Get most popular books based on sales and ratings."""
    books = Book.objects.annotate(
        total_orders=Count('order'),
        avg_rating=Avg('review__rating')
    ).order_by('-total_orders', '-avg_rating')[:top_n]

    return list(books)

def get_personalized_recommendations(user_id, top_n=10):
    """Get personalized recommendations for a user."""
    return hybrid_recommendation(user_id, None, top_n)

def train_recommendation_model():
    """Train the recommendation model (for periodic retraining)."""
    try:
        logger.info("Training recommendation model...")

        # Build matrices
        user_item_df = build_user_item_matrix()
        content_df = build_content_features()

        if not user_item_df.empty:
            # Simple collaborative filtering training
            # This is a placeholder for more sophisticated model training
            logger.info(f"Built user-item matrix with {len(user_item_df)} users and {len(user_item_df.columns)} items")

        if not content_df.empty:
            similarity_matrix, item_ids = calculate_content_similarity(content_df)
            logger.info(f"Built content similarity matrix for {len(item_ids)} items")

        # Clear cache to force refresh
        cache.delete('recommendation_matrices')

        logger.info("Recommendation model training completed")
        return True

    except Exception as e:
        logger.error(f"Error training recommendation model: {e}")
        return False
