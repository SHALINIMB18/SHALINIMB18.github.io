import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch, MagicMock
from .models import Book, Review, Order, UserProfile, Wishlist, UserBook
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
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        mock_send_mail.assert_called_once()


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
