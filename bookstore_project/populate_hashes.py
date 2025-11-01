import os
import django
import imagehash
import logging
from PIL import Image

logger = logging.getLogger(__name__)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.models import Book, UserBook

def generate_image_hash(image_path):
    """Generate perceptual hash for an image."""
    try:
        img = Image.open(image_path)
        hash_value = imagehash.phash(img)
        return str(hash_value)
    except (OSError, IOError) as e:
        logger.error(f"Error processing image {image_path}: {e}")
        return None

def populate_book_hashes():
    """Populate image hashes for Book model."""
    logger.info("Populating image hashes for Book model...")
    books = Book.objects.all()
    updated_count = 0

    for book in books:
        if book.cover_image_url:
            # For URL images, we'll skip for now as they require downloading
            # In a real implementation, you'd download and hash the images
            logger.info(f"Skipping URL image for book: {book.title}")
            continue

        # For local images, we would need to handle them differently
        # This is a placeholder for local image handling
        logger.info(f"Book {book.title} has no local image to hash")

    logger.info(f"Updated {updated_count} books with image hashes")

def populate_user_book_hashes():
    """Populate image hashes for UserBook model."""
    logger.info("Populating image hashes for UserBook model...")
    user_books = UserBook.objects.filter(is_available=True)
    updated_count = 0

    for user_book in user_books:
        if user_book.cover_image and not user_book.image_hash:
            try:
                # Get the full path to the image
                image_path = user_book.cover_image.path
                hash_value = generate_image_hash(image_path)

                if hash_value:
                    user_book.image_hash = hash_value
                    user_book.save()
                    updated_count += 1
                    logger.info(f"Updated hash for user book: {user_book.title}")
                else:
                    logger.warning(f"Failed to generate hash for user book: {user_book.title}")

            except Exception as e:
                logger.error(f"Error processing user book {user_book.title}: {e}")

    logger.info(f"Updated {updated_count} user books with image hashes")

if __name__ == '__main__':
    populate_book_hashes()
    populate_user_book_hashes()
    logger.info("Image hash population completed!")
