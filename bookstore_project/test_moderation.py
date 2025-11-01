#!/usr/bin/env python
"""
Test script for the AI moderation system.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bookstore.settings')
django.setup()

from books.moderation_utils import moderate_forum_content
from books.models import BookClubPost, BookClubComment
from django.contrib.auth.models import User

def test_moderation_function():
    """Test the moderation function directly."""
    print("Testing moderation_utils.moderate_forum_content()...")

    # Test non-toxic content
    result1 = moderate_forum_content("This is a great book! I really enjoyed reading it.")
    print(f"Non-toxic test: {result1}")

    # Test toxic content
    result2 = moderate_forum_content("This book sucks and the author is stupid")
    print(f"Toxic test: {result2}")

    # Test another toxic example
    result3 = moderate_forum_content("What a terrible piece of garbage, I hate this")
    print(f"Another toxic test: {result3}")

    print("Direct function tests completed.\n")

def test_model_moderation():
    """Test moderation on model instances."""
    print("Testing model moderation methods...")

    # Create a test user if not exists
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={'email': 'test@example.com'}
    )

    # Test BookClubPost moderation
    post = BookClubPost.objects.create(
        author=user,
        title="Test Post",
        content="This is a test post with some content"
    )
    print(f"Created test post: {post}")

    # Moderate the post
    post.moderate_content()
    print(f"Post moderation result: is_moderated={post.is_moderated}, reason={post.moderation_reason}, confidence={post.moderation_confidence}")

    # Test BookClubComment moderation
    comment = BookClubComment.objects.create(
        post=post,
        author=user,
        content="This is a test comment"
    )
    print(f"Created test comment: {comment}")

    # Moderate the comment
    comment.moderate_content()
    print(f"Comment moderation result: is_moderated={comment.is_moderated}, reason={comment.moderation_reason}, confidence={comment.moderation_confidence}")

    # Clean up
    comment.delete()
    post.delete()
    if created:
        user.delete()

    print("Model moderation tests completed.\n")

def test_database_fields():
    """Test that new fields exist in database."""
    print("Testing database fields...")

    from django.db import connection
    cursor = connection.cursor()

    # Check BookClubPost fields
    cursor.execute("PRAGMA table_info(books_bookclubpost)")
    post_columns = [row[1] for row in cursor.fetchall()]
    required_post_fields = ['moderation_reason', 'moderation_confidence']
    missing_post_fields = [field for field in required_post_fields if field not in post_columns]
    if missing_post_fields:
        print(f"Missing BookClubPost fields: {missing_post_fields}")
    else:
        print("All BookClubPost moderation fields present")

    # Check BookClubComment fields
    cursor.execute("PRAGMA table_info(books_bookclubcomment)")
    comment_columns = [row[1] for row in cursor.fetchall()]
    required_comment_fields = ['moderation_reason', 'moderation_confidence']
    missing_comment_fields = [field for field in required_comment_fields if field not in comment_columns]
    if missing_comment_fields:
        print(f"Missing BookClubComment fields: {missing_comment_fields}")
    else:
        print("All BookClubComment moderation fields present")

    print("Database field tests completed.\n")

if __name__ == "__main__":
    print("Starting AI Moderation System Tests...\n")

    try:
        test_moderation_function()
        test_model_moderation()
        test_database_fields()
        print("All tests completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
