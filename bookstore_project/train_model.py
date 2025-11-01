import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.ai_recommendation import train_recommendation_model

if __name__ == '__main__':
    print("Training recommendation model...")
    train_recommendation_model()
    print("Model trained successfully!")
