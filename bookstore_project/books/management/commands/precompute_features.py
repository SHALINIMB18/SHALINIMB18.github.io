from django.core.management.base import BaseCommand
from books.models import Book, UserBook
from books.visual_search import extract_features_from_url, extract_features_from_path
import os

class Command(BaseCommand):
    help = 'Precompute VGG16 features for all books with images'

    def handle(self, *args, **options):
        self.stdout.write('Starting feature precomputation...')

        # Process Book model
        books_with_images = Book.objects.exclude(cover_image_url__isnull=True).exclude(cover_image_url='')
        updated_books = 0

        for book in books_with_images:
            if not book.image_features:  # Only process if features not already computed
                try:
                    features = extract_features_from_url(book.cover_image_url)
                    if features:
                        book.image_features = features
                        book.save()
                        updated_books += 1
                        self.stdout.write(f'Processed book: {book.title}')
                    else:
                        self.stdout.write(f'Failed to extract features for book: {book.title}')
                except Exception as e:
                    self.stdout.write(f'Error processing book {book.title}: {e}')

        # Process UserBook model
        user_books_with_images = UserBook.objects.exclude(cover_image__isnull=True)
        updated_user_books = 0

        for user_book in user_books_with_images:
            if not user_book.image_features:  # Only process if features not already computed
                try:
                    image_path = user_book.cover_image.path
                    if os.path.exists(image_path):
                        features = extract_features_from_path(image_path)
                        if features:
                            user_book.image_features = features
                            user_book.save()
                            updated_user_books += 1
                            self.stdout.write(f'Processed user book: {user_book.title}')
                        else:
                            self.stdout.write(f'Failed to extract features for user book: {user_book.title}')
                    else:
                        self.stdout.write(f'Image file not found for user book: {user_book.title}')
                except Exception as e:
                    self.stdout.write(f'Error processing user book {user_book.title}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {updated_books} books and {updated_user_books} user books'
            )
        )
