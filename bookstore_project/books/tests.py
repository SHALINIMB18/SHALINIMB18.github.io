import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from .models import Book, Review, Order, UserProfile, Wishlist, UserBook, PaymentEvent, BookClubPost, BookClubComment
from .serializers import BookSerializer
from rest_framework.test import APITestCase
from rest_framework import status
from io import BytesIO
from PIL import Image


class BookModelTest(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99,
            rating=4.5,
            stock=10,
            description="A test book description"
        )

    def test_book_creation(self):
        self.assertEqual(self.book.title, "Test Book")
        self.assertEqual(self.book.author, "Test Author")
        self.assertEqual(self.book.price, 29.99)
        self.assertEqual(self.book.rating, 4.5)
        self.assertEqual(self.book.stock, 10)

    def test_book_str(self):
        self.assertEqual(str(self.book), "Test Book")

    def test_rating_validation(self):
        # Test valid rating
        self.book.rating = 5.0
        self.book.save()
        self.assertEqual(self.book.rating, 5.0)

        # Test invalid rating (should raise ValidationError)
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            invalid_book = Book(
                title="Invalid Book",
                author="Author",
                genre="Fiction",
                category="Novel",
                price=10.00,
                rating=6.0  # Invalid rating > 5
            )
            invalid_book.full_clean()  # This will trigger validation

    def test_rating_validation_min(self):
        # Test invalid rating below 0
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            invalid_book = Book(
                title="Invalid Book",
                author="Author",
                genre="Fiction",
                category="Novel",
                price=10.00,
                rating=-1.0  # Invalid rating < 0
            )
            invalid_book.full_clean()  # This will trigger validation


class ReviewModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99
        )
        self.review = Review.objects.create(
            user=self.user,
            book=self.book,
            rating=4,
            comment="Great book!"
        )

    def test_review_creation(self):
        self.assertEqual(self.review.user, self.user)
        self.assertEqual(self.review.book, self.book)
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.comment, "Great book!")

    def test_review_str(self):
        self.assertEqual(str(self.review), "testuser - Test Book")


class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99
        )
        self.order = Order.objects.create(
            user=self.user,
            book=self.book,
            quantity=2,
            status='cart'
        )

    def test_order_creation(self):
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.book, self.book)
        self.assertEqual(self.order.quantity, 2)
        self.assertEqual(self.order.status, 'cart')
        self.assertEqual(self.order.total_price, 59.98)  # 29.99 * 2

    def test_order_str(self):
        self.assertEqual(str(self.order), "testuser - Test Book")


class WishlistModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99
        )
        self.wishlist = Wishlist.objects.create(
            user=self.user,
            book=self.book
        )

    def test_wishlist_creation(self):
        self.assertEqual(self.wishlist.user, self.user)
        self.assertEqual(self.wishlist.book, self.book)

    def test_wishlist_str(self):
        self.assertEqual(str(self.wishlist), "testuser - Test Book")

    def test_unique_wishlist(self):
        # Test that duplicate wishlist entries are not allowed
        with self.assertRaises(Exception):
            Wishlist.objects.create(
                user=self.user,
                book=self.book
            )


class UserBookModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='seller', password='testpass')
        # Create a simple image for testing
        image = Image.new('RGB', (100, 100), color='red')
        image_io = BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        self.image_file = SimpleUploadedFile("test_image.jpg", image_io.getvalue(), content_type="image/jpeg")

        self.user_book = UserBook.objects.create(
            seller=self.user,
            title="User Book",
            author="User Author",
            genre="Fiction",
            category="Novel",
            price=15.99,
            condition="good",
            description="A used book",
            cover_image=self.image_file
        )

    def test_user_book_creation(self):
        self.assertEqual(self.user_book.seller, self.user)
        self.assertEqual(self.user_book.title, "User Book")
        self.assertEqual(self.user_book.price, 15.99)
        self.assertEqual(self.user_book.condition, "good")
        self.assertTrue(self.user_book.is_available)

    def test_user_book_str(self):
        self.assertEqual(str(self.user_book), "User Book - seller")


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99,
            rating=4.5,
            stock=10
        )

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/home.html')
        self.assertIn('featured_books', response.context)
        self.assertIn('top_books', response.context)

    def test_book_list_view(self):
        response = self.client.get(reverse('book_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_list.html')
        self.assertIn('books', response.context)

    def test_book_detail_view(self):
        response = self.client.get(reverse('book_detail', args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_detail.html')
        self.assertEqual(response.context['book'], self.book)

    def test_signup_view_get(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/signup.html')

    def test_signup_view_post(self):
        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123'
        }
        response = self.client.post(reverse('signup'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful signup
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/login.html')

    def test_login_view_post_valid(self):
        data = {
            'username': 'testuser',
            'password': 'testpass'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful login

    def test_login_view_post_invalid(self):
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        response = self.client.post(reverse('login'), data)
        self.assertEqual(response.status_code, 200)  # Stay on login page
        # Check for messages in response context instead of raw content
        messages = list(response.context['messages'])
        self.assertTrue(any('Invalid credentials' in str(message) for message in messages))

    def test_add_to_cart_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('add_to_cart', args=[self.book.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect to book_detail
        self.assertTrue(Order.objects.filter(user=self.user, book=self.book, status='cart').exists())

    def test_cart_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/cart.html')

    def test_wishlist_view_authenticated(self):
        self.client.login(username='testuser', password='testpass')
        response = self.client.get(reverse('wishlist'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/wishlist.html')


class IntegrationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='testpass', email='test@example.com')
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            genre="Fiction",
            category="Novel",
            price=29.99,
            rating=4.5,
            stock=10
        )

    def test_user_registration_login_flow(self):
        # Register user
        signup_data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'newpass123'
        }
        response = self.client.post(reverse('signup'), signup_data)
        self.assertEqual(response.status_code, 302)

        # Login user
        login_data = {
            'username': 'newuser',
            'password': 'newpass123'
        }
        response = self.client.post(reverse('login'), login_data)
        self.assertEqual(response.status_code, 302)

        # Check if user is logged in
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_add_to_cart_checkout_flow(self):
        # Login user
        self.client.login(username='testuser', password='testpass')

        # Add to cart
        response = self.client.get(reverse('add_to_cart', args=[self.book.pk]))
        self.assertEqual(response.status_code, 302)

        # View cart
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart_items', response.context)
        self.assertGreater(len(response.context['cart_items']), 0)

        # Checkout
        response = self.client.get(reverse('checkout'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart_items', response.context)
        self.assertIn('total', response.context)


class APITests(APITestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="API Test Book",
            author="API Author",
            genre="Fiction",
            category="Novel",
            price=19.99,
            rating=4.0,
            stock=5
        )

    def test_api_book_list(self):
        url = reverse('api_book_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        self.assertEqual(response.data[0]['title'], "API Test Book")

    def test_api_recommendations_authenticated(self):
        user = User.objects.create_user(username='apiuser', password='apipass')
        self.client.force_authenticate(user=user)
        url = reverse('api_recommendations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_recommendations_unauthenticated(self):
        url = reverse('api_recommendations')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_api_chatbot(self):
        url = reverse('api_chatbot')
        data = {'query': 'recommend fiction books'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('response', response.data)

    def test_payment_webhook(self):
        url = reverse('api_payment_webhook')

        # Create a user and an order that will be updated by the webhook
        user = User.objects.create_user(username='webhookuser', password='wp', email='webhook@example.com')
        book = Book.objects.create(title='Webhook Book', author='A', genre='F', category='N', price=9.99, stock=5)
        order = Order.objects.create(user=user, book=book, quantity=1, status='pending', razorpay_order_id='order_test123')

        # Prepare a payload similar to Razorpay's payment.captured structure
        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test123',
                        'order_id': 'order_test123',
                        'status': 'captured'
                    }
                }
            }
        }

        # Mock the razorpay utility verification to avoid SDK dependency in tests
        with patch('books.views.razorpay.Utility.verify_webhook_signature') as mock_verify:
            mock_verify.return_value = None
            response = self.client.post(url, data=payload, format='json', HTTP_X_RAZORPAY_SIGNATURE='sig')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data.get('status'), 'ok')
            # Ensure PaymentEvent persisted
            self.assertEqual(PaymentEvent.objects.count(), 1)
            # Reload order and ensure status updated and payment id set
            order.refresh_from_db()
            self.assertEqual(order.status, 'confirmed')
            self.assertEqual(order.razorpay_payment_id, 'pay_test123')
            # Ensure stock decremented
            book.refresh_from_db()
            self.assertEqual(book.stock, 4)

    def test_payment_webhook_idempotent(self):
        """Posting the same webhook twice should not decrement stock twice."""
        url = reverse('api_payment_webhook')

        user = User.objects.create_user(username='webhookuser2', password='wp2', email='webhook2@example.com')
        book = Book.objects.create(title='Webhook Book 2', author='A', genre='F', category='N', price=9.99, stock=5)
        order = Order.objects.create(user=user, book=book, quantity=1, status='pending', razorpay_order_id='order_test_idemp')

        payload = {
            'event': 'payment.captured',
            'payload': {
                'payment': {
                    'entity': {
                        'id': 'pay_test_idemp',
                        'order_id': 'order_test_idemp',
                        'status': 'captured'
                    }
                }
            }
        }

        with patch('books.views.razorpay.Utility.verify_webhook_signature') as mock_verify:
            mock_verify.return_value = None
            # First delivery
            resp1 = self.client.post(url, data=payload, format='json', HTTP_X_RAZORPAY_SIGNATURE='sig')
            self.assertEqual(resp1.status_code, status.HTTP_200_OK)
            # Second delivery (duplicate)
            resp2 = self.client.post(url, data=payload, format='json', HTTP_X_RAZORPAY_SIGNATURE='sig')
            self.assertEqual(resp2.status_code, status.HTTP_200_OK)

            # Verify order status and payment id set once
            order.refresh_from_db()
            self.assertEqual(order.status, 'confirmed')
            self.assertEqual(order.razorpay_payment_id, 'pay_test_idemp')

            # Ensure stock decremented only once (from 5 to 4)
            book.refresh_from_db()
            self.assertEqual(book.stock, 4)

    @patch('books.views.send_mail')
    def test_api_process_payment(self, mock_send_mail):
        user = User.objects.create_user(username='payuser', password='paypass')
        self.client.force_authenticate(user=user)

        # Add item to cart
        Order.objects.create(user=user, book=self.book, quantity=1, status='cart')

        url = reverse('api_process_payment')
        data = {
            'razorpay_payment_id': 'pay_test123',
            'razorpay_order_id': 'order_test123',
            'razorpay_signature': 'sig_test123',
            'shipping_info': {
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john@example.com',
                'address': '123 Main St',
                'city': 'Anytown',
                'state': 'CA',
                'zip': '12345'
            }
        }

        # Mock Razorpay client to avoid network calls and simulate successful verification
        with patch('books.views.razorpay.Client') as mock_razor_client:
            mock_client_instance = MagicMock()
            # utility.verify_payment_signature should not raise
            mock_client_instance.utility.verify_payment_signature.return_value = None
            # payment.fetch returns a captured payment
            mock_client_instance.payment.fetch.return_value = {'status': 'captured'}
            mock_razor_client.return_value = mock_client_instance

            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(response.data.get('success'))
            mock_send_mail.assert_called_once()

    def test_api_process_payment_idempotent(self):
        """Calling the process payment endpoint twice with the same payment id should be idempotent."""
        user = User.objects.create_user(username='idempuser', password='idemppass', email='idem@example.com')
        self.client.force_authenticate(user=user)

        # Add item to cart
        Order.objects.create(user=user, book=self.book, quantity=1, status='cart')

        url = reverse('api_process_payment')
        data = {
            'razorpay_payment_id': 'pay_idempotent',
            'razorpay_order_id': 'order_idempotent',
            'razorpay_signature': 'sig_idemp',
            'shipping_info': {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane@example.com',
                'address': '456 Main St',
                'city': 'Anytown',
                'state': 'CA',
                'zip': '54321'
            }
        }

        with patch('books.views.razorpay.Client') as mock_razor_client, patch('books.views.send_mail') as mock_send:
            mock_client_instance = MagicMock()
            mock_client_instance.utility.verify_payment_signature.return_value = None
            mock_client_instance.payment.fetch.return_value = {'status': 'captured'}
            mock_razor_client.return_value = mock_client_instance

            # First processing - should process and reduce stock
            resp1 = self.client.post(url, data, format='json')
            self.assertEqual(resp1.status_code, status.HTTP_200_OK)
            self.assertTrue(resp1.data.get('success'))

            # Reload book stock
            self.book.refresh_from_db()
            stock_after_first = self.book.stock

            # Second processing - should be idempotent and not reduce stock again
            resp2 = self.client.post(url, data, format='json')
            self.assertEqual(resp2.status_code, status.HTTP_200_OK)
            self.assertTrue(resp2.data.get('success'))

            self.book.refresh_from_db()
            self.assertEqual(self.book.stock, stock_after_first)


class ForumTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='forumuser', password='testpass')
        self.post = BookClubPost.objects.create(
            author=self.user,
            title="Test Forum Post",
            content="This is a test post content."
        )

    def test_book_club_view(self):
        response = self.client.get(reverse('book_club'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/book_club.html')
        self.assertIn('posts', response.context)

    def test_post_detail_view(self):
        response = self.client.get(reverse('post_detail', args=[self.post.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/post_detail.html')
        self.assertEqual(response.context['post'], self.post)

    def test_create_post_view_authenticated(self):
        self.client.login(username='forumuser', password='testpass')
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'books/create_post.html')

    def test_create_post_view_unauthenticated(self):
        response = self.client.get(reverse('create_post'))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_post_post_authenticated(self):
        self.client.login(username='forumuser', password='testpass')
        data = {
            'title': 'New Test Post',
            'content': 'This is new test content.'
        }
        response = self.client.post(reverse('create_post'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        self.assertTrue(BookClubPost.objects.filter(title='New Test Post').exists())

    def test_create_comment_authenticated(self):
        self.client.login(username='forumuser', password='testpass')
        data = {'content': 'This is a test comment.'}
        response = self.client.post(reverse('create_comment', args=[self.post.pk]), data)
        self.assertEqual(response.status_code, 302)  # Redirect after creation
        self.assertTrue(BookClubComment.objects.filter(content='This is a test comment.').exists())

    def test_like_post_authenticated(self):
        self.client.login(username='forumuser', password='testpass')
        response = self.client.post(reverse('like_post', args=[self.post.pk]), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.post.refresh_from_db()
        self.assertEqual(self.post.like_count, 1)

    def test_like_comment_authenticated(self):
        comment = BookClubComment.objects.create(
            post=self.post,
            author=self.user,
            content="Test comment"
        )
        self.client.login(username='forumuser', password='testpass')
        response = self.client.post(reverse('like_comment', args=[comment.pk]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        comment.refresh_from_db()
        self.assertEqual(comment.like_count, 1)


class SerializerTests(TestCase):
    def setUp(self):
        self.book = Book.objects.create(
            title="Serializer Test Book",
            author="Serializer Author",
            genre="Fiction",
            category="Novel",
            price=24.99,
            rating=4.2,
            stock=8
        )
        self.serializer = BookSerializer(instance=self.book)

    def test_book_serializer_fields(self):
        data = self.serializer.data
        self.assertEqual(data['title'], "Serializer Test Book")
        self.assertEqual(data['author'], "Serializer Author")
        self.assertEqual(data['price'], "24.99")  # Decimal serialized as string
        self.assertEqual(data['rating'], 4.2)
        self.assertEqual(data['stock'], 8)

    def test_book_serializer_valid_data(self):
        valid_data = {
            'title': 'New Book',
            'author': 'New Author',
            'genre': 'Non-Fiction',
            'category': 'Biography',
            'price': '15.99',
            'rating': 3.8,
            'stock': 12,
            'description': 'A new book description'
        }
        serializer = BookSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid())
        book = serializer.save()
        self.assertEqual(book.title, 'New Book')
        self.assertEqual(float(book.price), 15.99)
