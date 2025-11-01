import os
import django
import logging

logger = logging.getLogger(__name__)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.models import Book

books = Book.objects.all()
logger.info(f'Total books: {books.count()}')
for book in books[:3]:
    logger.info(f'{book.title} by {book.author} - ${book.price}')
