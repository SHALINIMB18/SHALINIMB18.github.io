from django.core.management.base import BaseCommand
from books.semantic_search import precompute_book_embeddings

class Command(BaseCommand):
    help = 'Precompute semantic embeddings for all books using Sentence-BERT'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recomputation of embeddings even if they already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        self.stdout.write('Starting semantic embedding precomputation...')

        if force:
            self.stdout.write('Force mode enabled - recomputing all embeddings')

        updated_books, updated_user_books = precompute_book_embeddings()

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully computed embeddings for {updated_books} books and {updated_user_books} user books'
            )
        )
