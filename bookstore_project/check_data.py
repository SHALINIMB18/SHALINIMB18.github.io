import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.models import Book

books = Book.objects.all()
print(f'Total books: {books.count()}')
for book in books[:3]:
    print(f'{book.title} by {book.author} - ${book.price}')
