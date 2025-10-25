from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Avg
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Book, Review, Order, UserProfile, Wishlist, UserBook, ChatMessage, BookClub
from .serializers import BookSerializer
from django.conf import settings
import razorpay
import random
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
import imagehash
from PIL import Image
import numpy as np
from .ai_recommendation import get_recommendations
from .visual_search import find_similar_books_enhanced

import logging

logger = logging.getLogger(__name__)

def home(request):
    logger.info(f"Request: {request.method} {request.path}")
    featured_books = Book.objects.all()[:5]
    top_books = Book.objects.order_by('-rating')[:10]
    return render(request, 'books/home.html', {
        'featured_books': featured_books,
        'top_books': top_books
    })

@cache_page(60 * 15)  # Cache for 15 minutes
def book_list(request):
    logger.info(f"Request: {request.method} {request.path}")
    try:
        # Using select_related for optimized queries
        # Default: show only books that have a non-empty, non-placeholder cover_image_url
        show_all = request.GET.get('show_all')
        if show_all:
            books = Book.objects.select_related().prefetch_related('review_set').all()
        else:
            books = Book.objects.select_related().prefetch_related('review_set').exclude(cover_image_url__isnull=True).exclude(cover_image_url__exact='').exclude(cover_image_url__icontains='book_placeholder.svg')
        category = request.GET.get('category')
        genre = request.GET.get('genre')
        author = request.GET.get('author')
        sort = request.GET.get('sort', 'title')

        if category:
            books = books.filter(category=category)
        if genre:
            books = books.filter(genre=genre)
        if author:
            books = books.filter(author__icontains=author)

        if sort == 'price':
            books = books.order_by('price')
        elif sort == 'rating':
            books = books.order_by('-rating')
        elif sort == 'popularity':
            books = books.order_by('-rating')

        context = {'books': books}
        return render(request, 'books/book_list.html', context)

    except Exception as e:
        logger.error(f"Error in book_list view: {str(e)}")
        messages.error(request, "An error occurred while loading the books. Please try again.")
        return render(request, 'books/book_list.html', {'books': []})

    if category:
        books = books.filter(category=category)
    if genre:
        books = books.filter(genre=genre)
    if author:
        books = books.filter(author__icontains=author)

    if sort == 'price':
        books = books.order_by('price')
    elif sort == 'rating':
        books = books.order_by('-rating')
    elif sort == 'popularity':
        books = books.order_by('-rating')

    return render(request, 'books/book_list.html', {'books': books})

@cache_page(60 * 5)  # Cache for 5 minutes
def book_detail(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    try:
        # Get book details with related data
        book = Book.objects.select_related().get(pk=pk)
        
        # Cache key for reviews
        cache_key = f'book_reviews_{pk}'
        reviews = cache.get(cache_key)
        
        if reviews is None:
            reviews = Review.objects.filter(book=book).select_related('user').order_by('-created_at')
            cache.set(cache_key, reviews, 60 * 5)  # Cache for 5 minutes
        
        # Cache recommendations
        rec_cache_key = f'book_recommendations_{pk}'
        similar_books = cache.get(rec_cache_key)
        
        if similar_books is None:
            similar_books = get_recommendations(book.id)
            cache.set(rec_cache_key, similar_books, 60 * 15)  # Cache for 15 minutes
        
        context = {
            'book': book,
            'reviews': reviews,
            'similar_books': similar_books
        }
        return render(request, 'books/book_detail.html', context)

    except Book.DoesNotExist:
        logger.warning(f"Book with id {pk} not found")
        messages.error(request, "Book not found.")
        return redirect('book_list')
    except Exception as e:
        logger.error(f"Error in book_detail view: {str(e)}")
        messages.error(request, "An error occurred while loading the book details. Please try again.")
        return redirect('book_list')

def book_club(request):
    logger.info(f"Request: {request.method} {request.path}")
    discussions = BookClub.objects.all().order_by('-created_at')
    return render(request, 'books/book_club.html', {'discussions': discussions})

@login_required
def add_to_cart(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    book = get_object_or_404(Book, pk=pk)
    cart_item, created = Order.objects.get_or_create(
        user=request.user,
        book=book,
        status='cart',
        defaults={'quantity': 1}
    )
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    messages.success(request, f"{book.title} added to cart!")
    return redirect('book_detail', pk=pk)
@login_required
def cart(request):
    logger.info(f"Request: {request.method} {request.path}")
    cart_items = Order.objects.filter(user=request.user, status='cart')
    total = sum(item.total_price for item in cart_items)
    return render(request, 'books/cart.html', {
        'cart_items': cart_items,
        'total': total
    })

@login_required
def update_cart(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        cart_item = get_object_or_404(Order, pk=pk, user=request.user, status='cart')
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
        else:
            cart_item.delete()
        messages.success(request, "Cart updated!")
    return redirect('cart')

@login_required
def remove_from_cart(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    cart_item = get_object_or_404(Order, pk=pk, user=request.user, status='cart')
    cart_item.delete()
    messages.success(request, f"{cart_item.book.title} removed from cart!")
    return redirect('cart')

@login_required
def checkout(request):
    logger.info(f"Request: {request.method} {request.path}")
    try:
        # Use select_related to optimize queries
        cart_items = Order.objects.filter(
            user=request.user, 
            status='cart'
        ).select_related('book', 'user_book')

        if not cart_items:
            messages.error(request, "Your cart is empty!")
            return redirect('cart')

        # Calculate totals
        total = sum(item.total_price for item in cart_items)
        amount_in_paisa = int(float(total) * 100)  # Convert to paisa for Razorpay

        # Check stock availability
        for item in cart_items:
            # 'Book' model uses 'stock' field for available quantity
            if item.book and getattr(item.book, 'stock', 0) < item.quantity:
                messages.error(request, f"Sorry, {item.book.title} is out of stock!")
                return redirect('cart')

        # Initialize Razorpay client
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payment_data = {
                'amount': amount_in_paisa,
                'currency': 'INR',
                'receipt': f'order_{cart_items[0].id}',
                'payment_capture': 1
            }
            razorpay_order = client.order.create(data=payment_data)
        except Exception as e:
            logger.error(f"Razorpay error: {str(e)}")
            messages.error(request, "Payment gateway error. Please try again later.")
            return redirect('cart')

        context = {
            'cart_items': cart_items,
            'total': total,
            'amount_in_paisa': amount_in_paisa,
            'razorpay_order_id': razorpay_order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID
        }
        return render(request, 'books/checkout.html', context)

    except Exception as e:
        logger.error(f"Error in checkout view: {str(e)}")
        messages.error(request, "An error occurred during checkout. Please try again.")
        return redirect('cart')

@login_required
def add_review(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    book = get_object_or_404(Book, pk=pk)
    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment', '')
        Review.objects.create(user=request.user, book=book, rating=rating, comment=comment)
        messages.success(request, "Review added successfully!")
    return redirect('book_detail', pk=pk)

@login_required
def user_dashboard(request):
    logger.info(f"Request: {request.method} {request.path}")
    orders = Order.objects.filter(user=request.user)
    reviews = Review.objects.filter(user=request.user)
    return render(request, 'books/dashboard.html', {
        'orders': orders,
        'reviews': reviews
    })

@login_required
def add_to_wishlist(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    book = get_object_or_404(Book, pk=pk)
    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        book=book
    )
    if created:
        messages.success(request, f"{book.title} added to wishlist!")
    else:
        messages.info(request, f"{book.title} is already in your wishlist!")
    return redirect('book_detail', pk=pk)

@login_required
def remove_from_wishlist(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    wishlist_item = get_object_or_404(Wishlist, pk=pk, user=request.user)
    book_title = wishlist_item.book.title
    wishlist_item.delete()
    messages.success(request, f"{book_title} removed from wishlist!")
    return redirect('wishlist')

@login_required
def wishlist(request):
    logger.info(f"Request: {request.method} {request.path}")
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('book')
    return render(request, 'books/wishlist.html', {
        'wishlist_items': wishlist_items
    })

@login_required
def buy_now(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    book = get_object_or_404(Book, pk=pk)
    # Create order with status 'pending' for immediate purchase
    order = Order.objects.create(
        user=request.user,
        book=book,
        quantity=1,
        status='pending',
        total_price=book.price
    )
    messages.success(request, f"You have purchased '{book.title}'!")
    return redirect('order_confirmation', order_id=order.id)

@login_required
def sell_book(request):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        genre = request.POST.get('genre')
        category = request.POST.get('category')
        price = request.POST.get('price')
        condition = request.POST.get('condition')
        description = request.POST.get('description', '')
        cover_image = request.FILES.get('cover_image')

        try:
            UserBook.objects.create(
                seller=request.user,
                title=title,
                author=author,
                genre=genre,
                category=category,
                price=price,
                condition=condition,
                description=description,
                cover_image=cover_image
            )
            messages.success(request, "Your book has been listed for sale!")
            return redirect('my_listings')
        except Exception as e:
            messages.error(request, f"Error listing book: {str(e)}")

    return render(request, 'books/sell_book.html')

@login_required
def my_listings(request):
    logger.info(f"Request: {request.method} {request.path}")
    user_books = UserBook.objects.filter(seller=request.user).order_by('-created_at')
    return render(request, 'books/my_listings.html', {
        'user_books': user_books
    })

@login_required
def edit_listing(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    user_book = get_object_or_404(UserBook, pk=pk, seller=request.user)

    if request.method == 'POST':
        user_book.title = request.POST.get('title')
        user_book.author = request.POST.get('author')
        user_book.genre = request.POST.get('genre')
        user_book.category = request.POST.get('category')
        user_book.price = request.POST.get('price')
        user_book.condition = request.POST.get('condition')
        user_book.description = request.POST.get('description', '')

        if request.FILES.get('cover_image'):
            user_book.cover_image = request.FILES.get('cover_image')

        try:
            user_book.save()
            messages.success(request, "Listing updated successfully!")
            return redirect('my_listings')
        except Exception as e:
            messages.error(request, f"Error updating listing: {str(e)}")

    return render(request, 'books/edit_listing.html', {
        'user_book': user_book
    })

@login_required
def delete_listing(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    user_book = get_object_or_404(UserBook, pk=pk, seller=request.user)
    if request.method == 'POST':
        user_book.delete()
        messages.success(request, "Listing deleted successfully!")
    return redirect('my_listings')

@login_required
def buy_user_book(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    user_book = get_object_or_404(UserBook, pk=pk, is_available=True)

    if user_book.seller == request.user:
        messages.error(request, "You cannot buy your own book!")
        return redirect('user_book_detail', pk=pk)

    if request.method == 'POST':
        # Create order for user book
        Order.objects.create(
            user=request.user,
            user_book=user_book,  # Fixed: use user_book instead of book
            quantity=1,
            status='pending',
            total_price=user_book.price
        )

        # Mark book as unavailable
        user_book.is_available = False
        user_book.save()

        messages.success(request, f"You have purchased '{user_book.title}'!")
        return redirect('order_confirmation', order_id=Order.objects.latest('id').id)

    return render(request, 'books/buy_user_book.html', {
        'user_book': user_book
    })

def user_book_detail(request, pk):
    logger.info(f"Request: {request.method} {request.path}")
    user_book = get_object_or_404(UserBook, pk=pk)
    return render(request, 'books/user_book_detail.html', {
        'user_book': user_book
    })

def marketplace(request):
    logger.info(f"Request: {request.method} {request.path}")
    user_books = UserBook.objects.filter(is_available=True).order_by('-created_at')
    category = request.GET.get('category')
    genre = request.GET.get('genre')
    condition = request.GET.get('condition')
    sort = request.GET.get('sort', 'newest')

    if category:
        user_books = user_books.filter(category=category)
    if genre:
        user_books = user_books.filter(genre=genre)
    if condition:
        user_books = user_books.filter(condition=condition)

    if sort == 'price_low':
        user_books = user_books.order_by('price')
    elif sort == 'price_high':
        user_books = user_books.order_by('-price')
    elif sort == 'oldest':
        user_books = user_books.order_by('created_at')

    return render(request, 'books/marketplace.html', {
        'user_books': user_books
    })

def signup(request):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        from django.contrib.auth.models import User
        user = User.objects.create_user(username=username, email=email, password=password)
        UserProfile.objects.create(user=user)
        login(request, user)
        return redirect('home')
    return render(request, 'books/signup.html')

def login_view(request):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'books/login.html')

def logout_view(request):
    logger.info(f"Request: {request.method} {request.path}")
    logout(request)
    return redirect('home')

def forgot_password(request):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            # Store OTP in session (in production, use cache or database)
            request.session['reset_otp'] = otp
            request.session['reset_email'] = email
            request.session.set_expiry(300)  # 5 minutes

            # Send OTP email
            subject = 'Password Reset OTP - BiblioTrack'
            message = f"""
            Dear {user.username},

            You have requested to reset your password. Your OTP is: {otp}

            This OTP will expire in 5 minutes.

            If you didn't request this, please ignore this email.

            Best regards,
            BiblioTrack Team
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'OTP sent to your email address.')
                return render(request, 'books/forgot_password.html', {'otp_sent': True, 'email': email})
            except Exception as e:
                messages.error(request, 'Failed to send email. Please try again.')
                return redirect('forgot_password')

        except User.DoesNotExist:
            messages.error(request, 'No account found with this email address.')
            return redirect('forgot_password')

    return render(request, 'books/forgot_password.html', {'otp_sent': False})

def verify_otp(request):
    logger.info(f"Request: {request.method} {request.path}")
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'books/forgot_password.html', {'otp_sent': True, 'email': email})

        # Check password strength
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'books/forgot_password.html', {'otp_sent': True, 'email': email})

        # Verify OTP
        stored_otp = request.session.get('reset_otp')
        stored_email = request.session.get('reset_email')

        if not stored_otp or not stored_email or stored_email != email:
            messages.error(request, 'Invalid session. Please try again.')
            return redirect('forgot_password')

        if otp != stored_otp:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'books/forgot_password.html', {'otp_sent': True, 'email': email})

        # Update password
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # Clear session
            del request.session['reset_otp']
            del request.session['reset_email']

            messages.success(request, 'Password reset successfully. You can now login with your new password.')
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, 'User not found.')
            return redirect('forgot_password')

    return redirect('forgot_password')

# API Views
@api_view(['GET'])
def api_book_list(request):
    logger.info(f"Request: {request.method} {request.path}")
    books = Book.objects.all()
    serializer = BookSerializer(books, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def api_recommendations(request):
    logger.info(f"Request: {request.method} {request.path}")
    user = request.user if request.user.is_authenticated else None
    if user:
        # Simple collaborative filtering based on user's reviews
        user_reviews = Review.objects.filter(user=user)
        genres = [review.book.genre for review in user_reviews]
        recommendations = Book.objects.filter(genre__in=genres).exclude(
            id__in=[review.book.id for review in user_reviews]
        ).distinct()[:5]
    else:
        recommendations = Book.objects.order_by('-rating')[:5]
    serializer = BookSerializer(recommendations, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def api_chatbot(request):
    logger.info(f"Request: {request.method} {request.path}")
    from .chatbot_utils import chatbot

    query = request.data.get('query', '')
    user = request.user if request.user.is_authenticated else None

    # Check if this is a visual search request
    if request.FILES.get('image'):
        # Handle visual search through chatbot using enhanced VGG16 search
        image = request.FILES.get('image')
        try:
            similar_books = find_similar_books_enhanced(image, top_n=3)

            if similar_books:
                book_titles = []
                for book, similarity, book_type in similar_books:
                    book_titles.append(book.title)
                response = f"I found these similar books: {', '.join(book_titles)}. Would you like more details about any of them?"
            else:
                response = "I couldn't find any books similar to your image. Try uploading a clearer photo of a book cover."

        except Exception as e:
            response = "Sorry, I had trouble processing your image. Please try again."
    else:
        # Use the AI-powered chatbot
        response = chatbot.chat(query, user)

    return Response({'response': response})

@api_view(['GET'])
def api_chat_messages(request):
    logger.info(f"Request: {request.method} {request.path}")
    """Get recent chat messages for book club"""
    messages = ChatMessage.objects.select_related('user', 'book').order_by('-created_at')[:50]
    data = []
    for msg in messages:
        data.append({
            'id': msg.id,
            'user': msg.user.username,
            'message': msg.message,
            'created_at': msg.created_at.isoformat(),
            'book': msg.book.title if msg.book else None
        })
    return Response(data)

@api_view(['POST'])
def api_send_chat_message(request):
    logger.info(f"Request: {request.method} {request.path}")
    """Send a new chat message"""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=401)

    message_text = request.data.get('message', '').strip()
    book_id = request.data.get('book_id')

    if not message_text:
        return Response({'error': 'Message cannot be empty'}, status=400)

    book = None
    if book_id:
        try:
            book = Book.objects.get(id=book_id)
        except Book.DoesNotExist:
            pass

    chat_message = ChatMessage.objects.create(
        user=request.user,
        message=message_text,
        book=book
    )

    return Response({
        'id': chat_message.id,
        'user': chat_message.user.username,
        'message': chat_message.message,
        'created_at': chat_message.created_at.isoformat(),
        'book': chat_message.book.title if chat_message.book else None
    })

@api_view(['POST'])
def api_visual_search(request):
    logger.info(f"Request: {request.method} {request.path}")
    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'No image provided'}, status=400)

    try:
        # Use enhanced VGG16-based visual search
        similar_books = find_similar_books_enhanced(image)

        if similar_books:
            # Serialize based on type
            results = []
            for book, similarity, book_type in similar_books:
                if book_type == 'book':
                    serializer = BookSerializer(book)
                    data = serializer.data
                    data['type'] = 'book'
                    data['similarity'] = similarity
                else:  # user_book
                    data = {
                        'id': book.id,
                        'title': book.title,
                        'author': book.author,
                        'genre': book.genre,
                        'category': book.category,
                        'price': str(book.price),
                        'condition': book.condition,
                        'description': book.description,
                        'cover_image': book.cover_image.url if book.cover_image else None,
                        'seller': book.seller.username,
                        'type': 'user_book',
                        'similarity': similarity
                    }
                results.append(data)
            return Response(results)
        else:
            return Response({'message': 'No similar books found'}, status=404)

    except Exception as e:
        return Response({'error': f'Error processing image: {str(e)}'}, status=500)

@api_view(['POST'])
def api_process_payment(request):
    logger.info(f"Request: {request.method} {request.path}")
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=401)

    try:
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.set_app_details({"title": "BiblioTrack", "version": "1.0"})

        data = request.data
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_signature = data.get('razorpay_signature')
        shipping_info = data.get('shipping_info')

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            logger.error("Missing payment information")
            return Response({'error': 'Incomplete payment information'}, status=400)

        # Verify payment signature
        params_dict = {
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_order_id': razorpay_order_id,
            'razorpay_signature': razorpay_signature
        }

        try:
            client.utility.verify_payment_signature(params_dict)
        except Exception as e:
            logger.error(f"Payment signature verification failed: {str(e)}")
            return Response({'error': 'Invalid payment signature'}, status=400)

        # Get payment details from Razorpay
        try:
            payment = client.payment.fetch(razorpay_payment_id)
            if payment['status'] != 'captured':
                logger.error(f"Payment not captured: {payment['status']}")
                return Response({'error': 'Payment not captured'}, status=400)
        except Exception as e:
            logger.error(f"Error fetching payment details: {str(e)}")
            return Response({'error': 'Could not verify payment'}, status=400)

        # Process the order in a transaction
        from django.db import transaction
        with transaction.atomic():
            # Update cart items to pending orders
            cart_items = Order.objects.filter(user=request.user, status='cart')
            if not cart_items:
                return Response({'error': 'No items in cart'}, status=400)

            order_ids = []
            for item in cart_items:
                # Check stock availability
                if item.book and item.book.quantity < item.quantity:
                    transaction.set_rollback(True)
                    return Response({
                        'error': f'Insufficient stock for {item.book.title}'
                    }, status=400)

                # Update order status and payment details
                item.status = 'confirmed'
                item.razorpay_payment_id = razorpay_payment_id
                item.razorpay_order_id = razorpay_order_id
                item.shipping_address = shipping_info.get('address', '')
                item.save()

                # Update book stock
                if item.book:
                    # Use 'stock' field on Book model
                    item.book.stock = max(0, getattr(item.book, 'stock', 0) - item.quantity)
                    item.book.save()

                order_ids.append(item.id)

            try:
                # Generate invoice PDF
                pdf_buffer = generate_invoice_pdf(order_ids, shipping_info)

                # Send confirmation email with invoice
                send_order_confirmation_email(request.user, order_ids, shipping_info, pdf_buffer)
            except Exception as e:
                logger.error(f"Error in post-payment processing: {str(e)}")
                # Don't rollback the transaction, just log the error
                # The order is still valid even if email/PDF generation fails

            return Response({
                'success': True,
                'order_id': order_ids[0] if order_ids else None,
                'message': 'Payment processed successfully'
            })

    except Exception as e:
        logger.error(f"Payment processing error: {str(e)}")
        return Response({
            'error': 'An error occurred while processing the payment'
        }, status=500)

@login_required
def order_confirmation(request, order_id):
    logger.info(f"Request: {request.method} {request.path}")
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = Order.objects.filter(user=request.user, status='pending', razorpay_order_id=order.razorpay_order_id)
        total = sum(item.total_price for item in order_items)

        # Mock shipping info - in real app, store this in database
        shipping_info = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': request.user.email,
            'address': '123 Main St',
            'city': 'Anytown',
            'state': 'CA',
            'zip': '12345'
        }

        return render(request, 'books/order_confirmation.html', {
            'order_id': order_id,
            'order_date': order.ordered_at,
            'order_items': order_items,
            'total': total,
            'shipping_info': shipping_info
        })
    except Order.DoesNotExist:
        messages.error(request, "Order not found.")
        return redirect('dashboard')

def generate_invoice_pdf(order_ids, shipping_info):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph("BiblioTrack - Invoice", styles['Title'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Order details
    order_info = f"Order IDs: {', '.join(map(str, order_ids))}<br/>Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    story.append(Paragraph(order_info, styles['Normal']))
    story.append(Spacer(1, 12))

    # Shipping info
    shipping_title = Paragraph("Shipping Information", styles['Heading2'])
    story.append(shipping_title)
    shipping_details = f"""
    Name: {shipping_info.get('first_name', '')} {shipping_info.get('last_name', '')}<br/>
    Email: {shipping_info.get('email', '')}<br/>
    Address: {shipping_info.get('address', '')}<br/>
    City: {shipping_info.get('city', '')}, {shipping_info.get('state', '')} {shipping_info.get('zip', '')}
    """
    story.append(Paragraph(shipping_details, styles['Normal']))
    story.append(Spacer(1, 12))

    # Order items table
    order_items = Order.objects.filter(id__in=order_ids)
    data = [['Book Title', 'Quantity', 'Price', 'Total']]
    total_amount = 0
    for item in order_items:
        data.append([item.book.title, str(item.quantity), f"${item.book.price}", f"${item.total_price}"])
        total_amount += item.total_price
    data.append(['', '', 'Grand Total', f"${total_amount}"])

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(table)

    doc.build(story)
    buffer.seek(0)
    return buffer

def send_order_confirmation_email(user, order_ids, shipping_info, pdf_buffer):
    subject = 'Order Confirmation - BiblioTrack'
    message = f"""
    Dear {user.username},

    Thank you for your order! Your order has been successfully placed.

    Order Details:
    Order IDs: {', '.join(map(str, order_ids))}
    Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

    Shipping Information:
    Name: {shipping_info.get('first_name', '')} {shipping_info.get('last_name', '')}
    Address: {shipping_info.get('address', '')}
    City: {shipping_info.get('city', '')}, {shipping_info.get('state', '')} {shipping_info.get('zip', '')}

    You can track your order status in your dashboard.

    Best regards,
    BiblioTrack Team
    """

    # Send email with PDF attachment
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
            attachments=[('invoice.pdf', pdf_buffer.getvalue(), 'application/pdf')]
        )
    except Exception as e:
        # Log the error but don't fail the order
        print(f"Email sending failed: {e}")
        # For demo purposes, we'll continue without failing
        pass
