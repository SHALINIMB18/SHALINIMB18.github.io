import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import re
import random
from .models import Book, Review, UserBook
from django.db.models import Q

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

class BookChatbot:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))

        # Intent patterns using regex
        self.intent_patterns = {
            'recommendation': [
                r'recommend.*book', r'suggest.*book', r'what.*read',
                r'book.*recommend', r'find.*book', r'good.*book'
            ],
            'search': [
                r'find.*by', r'search.*for', r'look.*for',
                r'books.*about', r'books.*author'
            ],
            'help': [
                r'help', r'what.*can.*do', r'how.*work', r'assist'
            ],
            'greeting': [
                r'hello', r'hi', r'hey', r'good.*morning', r'good.*afternoon'
            ],
            'farewell': [
                r'bye', r'goodbye', r'see.*you', r'thanks'
            ]
        }

        # Response templates
        self.responses = {
            'recommendation': [
                "Based on your interests, I recommend: {books}",
                "You might enjoy these books: {books}",
                "Here are some great recommendations: {books}",
                "I think you'll love these: {books}"
            ],
            'search': [
                "I found these books matching your query: {books}",
                "Here are the books I found: {books}",
                "Check out these results: {books}"
            ],
            'help': [
                "I can help you find book recommendations, search for books, or answer questions about our bookstore!",
                "Try asking me to recommend books by genre, author, or topic. I can also help with general bookstore questions.",
                "I'm here to help with book recommendations, searches, and general inquiries!"
            ],
            'greeting': [
                "Hello! I'm your AI book assistant. How can I help you discover amazing books today?",
                "Hi there! Ready to find your next great read?",
                "Welcome! I'm here to help you find the perfect book."
            ],
            'farewell': [
                "Happy reading! Come back anytime for more recommendations.",
                "Enjoy your books! See you soon.",
                "Take care and keep reading!"
            ],
            'unknown': [
                "I'm not sure I understand. Could you rephrase that?",
                "Hmm, I'm still learning. Can you try asking differently?",
                "I didn't catch that. Try asking about book recommendations or searches."
            ]
        }

    def preprocess_text(self, text):
        """Preprocess text for better matching"""
        # Tokenize
        tokens = word_tokenize(text.lower())

        # Remove stopwords and lemmatize
        tokens = [self.lemmatizer.lemmatize(token) for token in tokens
                 if token not in self.stop_words and token.isalnum()]

        return tokens

    def classify_intent(self, text):
        """Classify user intent using regex patterns"""
        text_lower = text.lower()

        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return intent

        return 'unknown'

    def extract_keywords(self, text):
        """Extract relevant keywords from user input"""
        tokens = self.preprocess_text(text)

        # Keywords for book search
        genres = ['fiction', 'non-fiction', 'mystery', 'romance', 'science', 'history',
                 'biography', 'fantasy', 'thriller', 'horror', 'comedy', 'drama']

        authors = ['stephen king', 'j.k. rowling', 'agatha christie', 'dan brown',
                  'harry potter', 'sherlock holmes']

        topics = ['habit', 'productivity', 'self-help', 'business', 'technology',
                 'programming', 'cooking', 'travel', 'health']

        found_genres = [g for g in genres if g in ' '.join(tokens)]
        found_authors = [a for a in authors if a in text.lower()]
        found_topics = [t for t in topics if t in ' '.join(tokens)]

        return {
            'genres': found_genres,
            'authors': found_authors,
            'topics': found_topics,
            'tokens': tokens
        }

    def search_books(self, keywords, limit=3):
        """Search for books based on keywords"""
        query = Q()

        if keywords['genres']:
            genre_query = Q()
            for genre in keywords['genres']:
                genre_query |= Q(genre__icontains=genre) | Q(category__icontains=genre)
            query &= genre_query

        if keywords['authors']:
            author_query = Q()
            for author in keywords['authors']:
                author_query |= Q(author__icontains=author)
            query &= author_query

        if keywords['topics']:
            topic_query = Q()
            for topic in keywords['topics']:
                topic_query |= Q(title__icontains=topic) | Q(description__icontains=topic)
            query &= topic_query

        # Search in both Book and UserBook models
        books = list(Book.objects.filter(query).order_by('-rating')[:limit])
        user_books = list(UserBook.objects.filter(query, is_available=True).order_by('-created_at')[:limit])

        all_books = books + user_books

        if not all_books:
            # Fallback: search by title or general keywords
            general_query = Q()
            for token in keywords['tokens'][:3]:  # Use first 3 tokens
                general_query |= Q(title__icontains=token) | Q(author__icontains=token)

            books = list(Book.objects.filter(general_query).order_by('-rating')[:limit])
            user_books = list(UserBook.objects.filter(general_query, is_available=True).order_by('-created_at')[:limit])
            all_books = books + user_books

        return all_books[:limit]

    def get_recommendations(self, user=None, limit=3):
        """Get personalized recommendations"""
        if user and user.is_authenticated:
            # Get user's review history
            user_reviews = Review.objects.filter(user=user)
            if user_reviews.exists():
                # Recommend based on reviewed genres
                genres = [review.book.genre for review in user_reviews]
                books = Book.objects.filter(genre__in=genres).exclude(
                    id__in=[review.book.id for review in user_reviews]
                ).order_by('-rating')[:limit]
                return list(books)

        # Default recommendations: top rated books
        return list(Book.objects.order_by('-rating')[:limit])

    def generate_response(self, intent, keywords=None, user=None):
        """Generate response based on intent and keywords"""
        if intent == 'recommendation':
            books = self.search_books(keywords) if keywords else self.get_recommendations(user)
            if books:
                book_titles = [book.title for book in books]
                template = random.choice(self.responses['recommendation'])
                return template.format(books=', '.join(book_titles))
            else:
                return "I couldn't find specific recommendations. Try our top-rated books!"

        elif intent == 'search':
            books = self.search_books(keywords)
            if books:
                book_titles = [book.title for book in books]
                template = random.choice(self.responses['search'])
                return template.format(books=', '.join(book_titles))
            else:
                return "I couldn't find books matching your search. Try different keywords!"

        elif intent == 'help':
            return random.choice(self.responses['help'])

        elif intent == 'greeting':
            return random.choice(self.responses['greeting'])

        elif intent == 'farewell':
            return random.choice(self.responses['farewell'])

        else:
            return random.choice(self.responses['unknown'])

    def chat(self, message, user=None):
        """Main chat function"""
        # Classify intent
        intent = self.classify_intent(message)

        # Extract keywords
        keywords = self.extract_keywords(message)

        # Generate response
        response = self.generate_response(intent, keywords, user)

        return response

# Global chatbot instance
chatbot = BookChatbot()
