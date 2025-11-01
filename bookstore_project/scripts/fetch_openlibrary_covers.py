import os
import sys
import re
import requests
import logging
from pathlib import Path
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


# Django setup
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
import django
django.setup()

from books.models import Book

MEDIA_DIR = BASE_DIR / 'media' / 'books'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

# Helpful helper to create safe filenames
def safe_filename(title, ext='.jpg'):
    safe = re.sub(r"[^0-9a-zA-Z-_]", "_", title).lower()[:80]
    return f"{safe}{ext}"

# Search Open Library for a book by title+author, return cover id if found
def find_openlibrary_cover_id(title, author=None):
    base = 'https://openlibrary.org/search.json'
    q = f'title={quote_plus(title)}'
    if author:
        q += f'&author={quote_plus(author)}'
    url = f'{base}?{q}&limit=5'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        docs = data.get('docs', [])
        for doc in docs:
            # Prefer doc that has a cover_i
            cover_i = doc.get('cover_i')
            if cover_i:
                return cover_i
        # fallback: sometimes 'edition_key' can be used but cover_i is best
        return None
    except (requests.RequestException, ValueError) as e:
        logger.error(f'OpenLibrary search error for "{title}" (author: {author}): {e}')
        return None

# Download cover by cover id: https://covers.openlibrary.org/b/id/{cover_id}-L.jpg
def download_cover_by_id(cover_id, out_path):
    url = f'https://covers.openlibrary.org/b/id/{cover_id}-L.jpg'
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        with open(out_path, 'wb') as f:
            f.write(r.content)
        return True
    except (requests.RequestException, OSError) as e:
        logger.error(f'Failed to download cover id {cover_id}: {e}')
        return False


def main(limit=None):
    books = Book.objects.all()
    total = books.count()
    logger.info(f'Total books: {total}')
    updated = 0
    tried = 0
    for book in books:
        if limit and tried >= limit:
            break
        # If book already has a local media path, skip
        if book.cover_image_url and str(book.cover_image_url).startswith('/media/books/'):
            tried += 1
            continue
        title = book.title
        author = book.author
        logger.info(f'Searching Open Library for: "{title}" by "{author}"')
        cover_id = find_openlibrary_cover_id(title, author)
        if not cover_id:
            # try without author
            cover_id = find_openlibrary_cover_id(title, None)
        if cover_id:
            fname = safe_filename(title, ext='.jpg')
            out_path = MEDIA_DIR / fname
            if download_cover_by_id(cover_id, out_path):
                book.cover_image_url = f'/media/books/{fname}'
                book.save()
                updated += 1
                logger.info(f'Updated: {book.title} -> /media/books/{fname}')
        else:
            logger.info(f'No cover found for "{title}"')
        tried += 1
    logger.info(f'Done. Updated {updated} books (attempted {tried}).')

if __name__ == '__main__':
    # optional CLI arg: limit
    lim = None
    if len(sys.argv) > 1:
        try:
            lim = int(sys.argv[1])
        except:
            pass
    main(limit=lim)
