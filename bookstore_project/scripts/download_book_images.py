import os
import re
import requests
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Django setup
import django
import sys
BASE_DIR = Path(__file__).resolve().parents[1]
# Ensure project root is on sys.path so Django can import settings
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.models import Book

MEDIA_DIR = BASE_DIR / 'media' / 'books'
MEDIA_DIR.mkdir(parents=True, exist_ok=True)

POPULATE_FILE = BASE_DIR / 'populate_data.py'
MAX_DOWNLOAD = 60  # number of images to download by default (increased per user request)

# Read populate_data.py and extract titles and cover_image_url values
text = POPULATE_FILE.read_text(encoding='utf-8')

# Find all title and cover_image_url occurrences (they should appear in the same order)
titles = re.findall(r"'title'\s*:\s*'([^']*)'", text)
urls = re.findall(r"'cover_image_url'\s*:\s*'([^']*)'", text)

mapping = {}
for t, u in zip(titles, urls):
    mapping[t.strip()] = u.strip()

logger.info(f'Found {len(mapping)} title->url mappings in populate_data.py')

count = 0
updated = 0
for book in Book.objects.all():
    if count >= MAX_DOWNLOAD:
        break
    url = mapping.get(book.title)
    if not url:
        continue
    if url.strip() == '':
        continue
    # Skip if already local
    if url.startswith('/media/books/'):
        continue

    try:
        logger.info(f'Downloading for "{book.title}" from {url}')
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        # Determine extension
        parsed = urlparse(url)
        fname = os.path.basename(parsed.path)
        if '.' in fname:
            ext = os.path.splitext(fname)[1]
        else:
            ext = '.jpg'
        # create safe filename
        safe_name = re.sub(r"[^0-9a-zA-Z-_]", "_", book.title).lower()[:100]
        filename = f"{safe_name}{ext}"
        out_path = MEDIA_DIR / filename
        with open(out_path, 'wb') as f:
            f.write(resp.content)

        # Update model to point to local media path
        book.cover_image_url = f'/media/books/{filename}'
        book.save()
        updated += 1
        count += 1
    except (requests.RequestException, OSError) as e:
        logger.error(f'Failed to download for "{book.title}": {e}')
        count += 1
        continue

logger.info(f'Downloaded and updated {updated} book cover URLs (attempted {count}).')
