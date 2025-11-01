from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.files import File
from books.models import Book
import os


class Command(BaseCommand):
    help = 'Sync local cover_image_url (under MEDIA) into the Book.image ImageField for easier admin management'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show actions without writing files')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of books to process (0 = all)')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        qs = Book.objects.filter(image__isnull=True).exclude(cover_image_url__isnull=True).exclude(cover_image_url__exact='')
        processed = 0

        for book in qs:
            if limit and processed >= limit:
                break

            cover = book.cover_image_url
            if not cover:
                continue

            # Check if cover is a local media path
            rel = None
            if cover.startswith(settings.MEDIA_URL):
                rel = cover.replace(settings.MEDIA_URL, '').lstrip('/')
            elif cover.startswith('/media/') or cover.startswith('media/'):
                rel = cover.split('/media/')[-1]

            if not rel:
                self.stdout.write(f"Skipping (not local media): {book.title}")
                continue

            src_path = os.path.join(settings.MEDIA_ROOT, rel)
            if not os.path.exists(src_path):
                self.stdout.write(f"File not found for {book.title}: {src_path}")
                continue

            filename = os.path.basename(src_path)
            if dry_run:
                self.stdout.write(f"[DRY] Would copy {src_path} -> Book.image for '{book.title}'")
                processed += 1
                continue

            try:
                with open(src_path, 'rb') as f:
                    django_file = File(f)
                    # Save into image field; keep original filename to avoid collisions
                    book.image.save(filename, django_file, save=True)
                    self.stdout.write(f"Copied {src_path} -> Book.image for '{book.title}'")
                    processed += 1
            except Exception as e:
                self.stdout.write(f"Error copying for {book.title}: {e}")

        self.stdout.write(self.style.SUCCESS(f"Processed {processed} books"))
