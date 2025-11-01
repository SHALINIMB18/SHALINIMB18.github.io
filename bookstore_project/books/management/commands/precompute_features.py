from django.core.management.base import BaseCommand
from books.models import Book, UserBook
from books.visual_search import extract_features_from_url, extract_features_from_path
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Precompute VGG16 features for all books with images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recomputation of features even if they already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write('Starting feature precomputation...')

        # Process Book model
        books_with_images = Book.objects.exclude(cover_image_url__isnull=True).exclude(cover_image_url='')
        updated_books = 0

        for book in books_with_images:
            if force or not book.image_features:  # Only process if features not already computed or force is True
                try:
                    cover = book.cover_image_url or ''
                    features = None
                    # If cover looks like a media path (local), try extracting from local file
                    if cover.startswith(settings.MEDIA_URL) or cover.startswith('/media/') or cover.startswith('media/'):
                        # Build local path from MEDIA_ROOT
                        rel_path = cover.replace(settings.MEDIA_URL, '').lstrip('/')
                        local_path = os.path.join(settings.MEDIA_ROOT, rel_path)
                        if os.path.exists(local_path):
                            features = extract_features_from_path(local_path)
                        else:
                            # Try with simple join in case cover has leading /media/
                            local_path = os.path.join(settings.BASE_DIR, cover.lstrip('/'))
                            if os.path.exists(local_path):
                                features = extract_features_from_path(local_path)
                    else:
                        # Fallback to URL extraction
                        features = extract_features_from_url(cover)

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
            if force or not user_book.image_features:  # Only process if features not already computed or force is True
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
