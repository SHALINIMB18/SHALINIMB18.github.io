import os
import sys
import django
import traceback

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore_project.settings')
django.setup()

from books.models import Book
from books import ai_recommendation, visual_search, chatbot_utils


def safe_print(title, fn, *args, **kwargs):
    print('\n' + '='*40)
    print(title)
    print('-'*40)
    try:
        res = fn(*args, **kwargs)
        print('Result:', res)
    except Exception as e:
        print('ERROR:', e)
        traceback.print_exc()


def test_recommendation():
    book = Book.objects.first()
    if not book:
        print('No books in DB to test recommendations')
        return
    print(f'Testing recommendations for Book id={book.id} title={book.title}')
    recs = ai_recommendation.get_recommendations(book.id, top_n=5)
    print('Recommendations count:', len(recs))
    for r in recs:
        try:
            print(f' - ({getattr(r, "id", "?")}) {getattr(r, "title", str(r))}')
        except Exception:
            print(' - (could not read title)')


def test_chatbot():
    bot = chatbot_utils.chatbot
    queries = [
        'Recommend me a good mystery book',
        'Find books by Agatha Christie',
        'Hello',
        'I want books about productivity'
    ]
    for q in queries:
        resp = bot.chat(q)
        print(f'Q: {q}\nA: {resp}\n')


def test_visual_search():
    # Try to find a local image in media/books
    media_books_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'media', 'books')
    image_path = None
    if os.path.isdir(media_books_dir):
        for fname in os.listdir(media_books_dir):
            if fname.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(media_books_dir, fname)
                break
    if image_path:
        print('Using local image:', image_path)
        feats = visual_search.extract_features_from_path(image_path)
        print('Extracted feature length:', None if feats is None else len(feats))
        sim = visual_search.find_similar_books_enhanced(image_path, top_n=5)
        print('Visual search results (len):', len(sim))
        for item in sim:
            print(' -', getattr(item[0], 'title', str(item[0])), 'sim=', item[1])
    else:
        print('No local images found in media/books — trying a fallback OpenLibrary cover URL')
        # Use Open Library cover for 'The Hobbit' (ISBN or OLID may vary); this is a generic cover URL
        ol_cover = 'https://covers.openlibrary.org/b/olid/OL26331930M-L.jpg'
        feats = visual_search.extract_features_from_url(ol_cover)
        print('Extracted feature length from URL:', None if feats is None else len(feats))
        if feats:
            # use the bytes stream path test function
            sim = visual_search.find_similar_books_enhanced(ol_cover, top_n=5)
            print('Visual search results (len):', len(sim))
            for item in sim:
                print(' -', getattr(item[0], 'title', str(item[0])), 'sim=', item[1])


if __name__ == '__main__':
    print('Running AI & Visual Search smoke tests')
    try:
        safe_print('Recommendation test', test_recommendation)
        safe_print('Chatbot test', test_chatbot)
        safe_print('Visual search test', test_visual_search)
    except Exception as e:
        print('Unexpected error during tests:', e)
        traceback.print_exc()
    print('\nFinished tests')
