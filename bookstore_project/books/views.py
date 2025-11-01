from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Avg, Count
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils.cache import get_cache_key
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.template.loader import get_template
from django.core.mail import send_mail
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Book, Review, Order, Wishlist, UserBook, ChatMessage, BookClubPost, BookClubComment, BookClubPostLike, BookClubCommentLike, RecentlyViewed, Deal, SellerRating, UserProfile
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
from .semantic_search import semantic_search_books
from .advanced_visual_search import find_similar_books_advanced
from .models import PaymentEvent

import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
def api_welcome(request):
    logger.info(f"Request: {request.method} {request.path}")
    return Response({'message': 'Welcome to the API'})

def home(request):
    featured_books = Book.objects.filter(is_featured=True)[:6]
    recent_books = Book.objects.order_by('-created_at')[:6]
    best_sellers = Book.objects.order_by('-total_sold')[:6]

    context = {
        'featured_books': featured_books,
        'recent_books': recent_books,
        'best_sellers': best_sellers,
    }
    return render(request, 'books/home.html', context)

@cache_page(60 * 15)  # Cache for 15 minutes
def book_list(request):
    """Display a list of books with search and filtering capabilities."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    genre = request.GET.get('genre', '')
    sort_by = request.GET.get('sort', 'title')

    books = Book.objects.all()

    # Apply semantic search if query provided
    if query:
        search_results = semantic_search_books(query, top_n=50)
        book_ids = [book.id for book, score in search_results if hasattr(book, 'id')]
        if book_ids:
            books = books.filter(id__in=book_ids)
            # Preserve semantic search order
            from django.db.models import Case, When
            preserved_order = Case(*[When(id=id_val, then=pos) for pos, id_val in enumerate(book_ids)])
            books = books.order_by(preserved_order)
        else:
            # Fallback to basic text search
            books = books.filter(
                Q(title__icontains=query) |
                Q(author__icontains=query) |
                Q(description__icontains=query)
            )

    # Apply filters
    if category:
        books = books.filter(category__iexact=category)
    if genre:
        books = books.filter(genre__iexact=genre)

    # Apply sorting
    if sort_by == 'price_low':
        books = books.order_by('price')
    elif sort_by == 'price_high':
        books = books.order_by('-price')
    elif sort_by == 'rating':
        books = books.order_by('-rating')
    elif sort_by == 'newest':
        books = books.order_by('-created_at')
    else:
        books = books.order_by('title')

    # Get unique categories and genres for filter dropdowns
    categories = Book.objects.values_list('category', flat=True).distinct()
    genres = Book.objects.values_list('genre', flat=True).distinct()

    context = {
        'books': books,
        'query': query,
        'selected_category': category,
        'selected_genre': genre,
        'categories': categories,
        'genres': genres,
        'sort_by': sort_by,
    }
    return render(request, 'books/book_list.html', context)

def book_detail(request, pk):
    """Display detailed information about a specific book."""
    book = get_object_or_404(Book, pk=pk)

    # Get reviews for this book
    reviews = Review.objects.filter(book=book).order_by('-created_at')

    # Check if book is in user's wishlist
    in_wishlist = False
    if request.user.is_authenticated:
        in_wishlist = Wishlist.objects.filter(user=request.user, book=book).exists()

    # Get similar books using semantic search
    similar_books = semantic_search_books(f"{book.title} {book.author} {book.genre}", top_n=4)
    similar_books = [b for b, score in similar_books if b.id != book.id][:3]

    # Track recently viewed
    if request.user.is_authenticated:
        RecentlyViewed.objects.get_or_create(
            user=request.user,
            book=book,
            defaults={'viewed_at': timezone.now()}
        )

    context = {
        'book': book,
        'reviews': reviews,
        'in_wishlist': in_wishlist,
        'similar_books': similar_books,
        'average_rating': reviews.aggregate(Avg('rating'))['rating__avg'] if reviews else 0,
    }
    return render(request, 'books/book_detail.html', context)

@login_required
def add_review(request, pk):
    """Add a review for a book."""
    book = get_object_or_404(Book, pk=pk)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if rating and comment:
            Review.objects.create(
                user=request.user,
                book=book,
                rating=int(rating),
                comment=comment
            )
            messages.success(request, 'Review added successfully!')
        else:
            messages.error(request, 'Please provide both rating and comment.')

    return redirect('book_detail', pk=pk)

def book_club(request):
    """Display book club forum posts."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    sort_by = request.GET.get('sort', 'recent')
    page = request.GET.get('page', 1)

    posts = BookClubPost.objects.all()

    # Apply search filters
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(author__username__icontains=query)
        )

    # Apply category filter (if we add categories later)
    if category:
        posts = posts.filter(category__iexact=category)

    # Apply sorting
    if sort_by == 'trending':
        # Trending: posts with most recent activity (comments + likes) in last 7 days
        from django.utils import timezone
        from datetime import timedelta
        week_ago = timezone.now() - timedelta(days=7)
        posts = posts.annotate(
            recent_activity=Count(
                'comments',
                filter=Q(comments__created_at__gte=week_ago)
            ) + Count(
                'post_likes',
                filter=Q(post_likes__created_at__gte=week_ago)
            )
        ).order_by('-is_pinned', '-recent_activity', '-created_at')
    elif sort_by == 'popular':
        posts = posts.order_by('-is_pinned', '-like_count', '-comment_count', '-created_at')
    elif sort_by == 'oldest':
        posts = posts.order_by('-is_pinned', 'created_at')
    else:  # recent
        posts = posts.order_by('-is_pinned', '-created_at')

    # Implement pagination
    from django.core.paginator import Paginator
    paginator = Paginator(posts, 10)  # 10 posts per page
    try:
        posts_page = paginator.page(page)
    except:
        posts_page = paginator.page(1)

    # Get trending posts (most comments in last 7 days)
    from django.utils import timezone
    from datetime import timedelta
    week_ago = timezone.now() - timedelta(days=7)
    trending_posts = BookClubPost.objects.filter(
        created_at__gte=week_ago
    ).annotate(
        recent_comments=Count('comments', filter=Q(comments__created_at__gte=week_ago))
    ).order_by('-recent_comments')[:5]

    # Get thread recommendations for authenticated users
    recommendations = []
    if request.user.is_authenticated:
        # Recommend posts from similar users or based on user's reading interests
        user_posts = BookClubPost.objects.filter(author=request.user)
        if user_posts.exists():
            # Find posts by users who commented on the same posts
            commenter_ids = BookClubComment.objects.filter(
                post__in=user_posts
            ).values_list('author', flat=True).distinct()

            recommendations = BookClubPost.objects.filter(
                author__in=commenter_ids
            ).exclude(author=request.user).order_by('-created_at')[:3]

    # Calculate total comments
    total_comments = sum(post.comment_count for post in posts)

    context = {
        'posts': posts_page,
        'query': query,
        'selected_category': category,
        'selected_sort': sort_by,
        'trending_posts': trending_posts,
        'recommendations': recommendations,
        'paginator': paginator,
        'page_obj': posts_page,
        'total_comments': total_comments,
    }
    return render(request, 'books/book_club.html', context)

@login_required
def post_detail(request, pk):
    """Display individual forum post with comments."""
    post = get_object_or_404(BookClubPost, pk=pk)
    comments = post.comments.all().order_by('created_at')

    # Check if user liked the post
    post_liked = False
    if request.user.is_authenticated:
        post_liked = BookClubPostLike.objects.filter(user=request.user, post=post).exists()

    # Check likes for comments
    comment_likes = {}
    if request.user.is_authenticated:
        for comment in comments:
            comment_likes[comment.id] = BookClubCommentLike.objects.filter(
                user=request.user, comment=comment
            ).exists()

    context = {
        'post': post,
        'comments': comments,
        'post_liked': post_liked,
        'comment_likes': comment_likes,
    }
    return render(request, 'books/post_detail.html', context)

@login_required
def create_post(request):
    """Create a new forum post."""
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')

        if title and content:
            # Moderate content
            from .moderation_utils import moderate_forum_content
            title_moderation = moderate_forum_content(title)
            content_moderation = moderate_forum_content(content)

            # Check if content is flagged
            if title_moderation['is_flagged'] or content_moderation['is_flagged']:
                messages.error(request, 'Your post contains inappropriate content and cannot be posted.')
                return render(request, 'books/create_post.html', {
                    'title': title,
                    'content': content
                })

            post = BookClubPost.objects.create(
                author=request.user,
                title=title,
                content=content
            )
            messages.success(request, 'Post created successfully!')
            return redirect('post_detail', pk=post.pk)
        else:
            messages.error(request, 'Please provide both title and content.')

    return render(request, 'books/create_post.html')

@login_required
def create_comment(request, post_id):
    """Create a comment on a forum post."""
    post = get_object_or_404(BookClubPost, pk=post_id)

    if request.method == 'POST':
        content = request.POST.get('content')

        if content:
            # Moderate content
            from .moderation_utils import moderate_forum_content
            content_moderation = moderate_forum_content(content)

            # Check if content is flagged
            if content_moderation['is_flagged']:
                messages.error(request, 'Your comment contains inappropriate content and cannot be posted.')
                return redirect('post_detail', pk=post_id)

            BookClubComment.objects.create(
                author=request.user,
                post=post,
                content=content
            )
            messages.success(request, 'Comment added successfully!')
        else:
            messages.error(request, 'Please provide comment content.')

    return redirect('post_detail', pk=post_id)

@login_required
def like_post(request, post_id):
    """Like or unlike a forum post."""
    post = get_object_or_404(BookClubPost, pk=post_id)

    like, created = BookClubPostLike.objects.get_or_create(
        user=request.user,
        post=post
    )

    if not created:
        like.delete()
        post.like_count -= 1
        post.save()
        liked = False
        messages.info(request, 'Post unliked.')
    else:
        post.like_count += 1
        post.save()
        liked = True
        messages.success(request, 'Post liked!')

    # Handle AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': post.like_count
        })

    return redirect('post_detail', pk=post_id)

@login_required
def like_comment(request, comment_id):
    """Like or unlike a forum comment."""
    comment = get_object_or_404(BookClubComment, pk=comment_id)

    like, created = BookClubCommentLike.objects.get_or_create(
        user=request.user,
        comment=comment
    )

    if not created:
        like.delete()
        liked = False
        messages.info(request, 'Comment unliked.')
    else:
        liked = True
        messages.success(request, 'Comment liked!')

    # Handle AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': comment.like_count
        })

    return redirect('post_detail', pk=comment.post.pk)

def signup(request):
    """Handle user registration."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'books/signup.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'books/signup.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'books/signup.html')

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        messages.success(request, 'Account created successfully!')
        return redirect('home')

    return render(request, 'books/signup.html')

def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Logged in successfully!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid credentials.')

    return render(request, 'books/login.html')

def logout_view(request):
    """Handle user logout."""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('home')

def forgot_password(request):
    """Handle forgot password functionality."""
    if request.method == 'POST':
        email = request.POST.get('email')
        # For demo purposes, just show a message
        messages.info(request, 'Password reset link sent to your email.')
        return redirect('login')

    return render(request, 'books/forgot_password.html')

def verify_otp(request):
    """Handle OTP verification for password reset."""
    if request.method == 'POST':
        otp = request.POST.get('otp')
        # For demo purposes, just redirect
        messages.success(request, 'OTP verified successfully!')
        return redirect('login')

    return render(request, 'books/forgot_password.html')

@login_required
def user_dashboard(request):
    """Display user dashboard with orders and activity."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    wishlist_items = Wishlist.objects.filter(user=request.user)
    recently_viewed = RecentlyViewed.objects.filter(user=request.user)[:10]

    context = {
        'orders': orders,
        'wishlist_items': wishlist_items,
        'recently_viewed': recently_viewed,
    }
    return render(request, 'books/dashboard.html', context)

@login_required
def cart(request):
    """Display user's shopping cart."""
    cart_items = Order.objects.filter(user=request.user, status='pending')
    total = sum(item.total_price for item in cart_items)

    context = {
        'cart_items': cart_items,
        'total': total,
    }
    return render(request, 'books/cart.html', context)

@login_required
def checkout(request):
    """Handle checkout process."""
    cart_items = Order.objects.filter(user=request.user, status='pending')
    if not cart_items:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    total = sum(item.total_price for item in cart_items)

    if request.method == 'POST':
        # Process payment and create order
        shipping_info = {
            'first_name': request.POST.get('first_name'),
            'last_name': request.POST.get('last_name'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'state': request.POST.get('state'),
            'zip': request.POST.get('zip'),
        }

        # Create Razorpay order
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        razorpay_order = client.order.create({
            'amount': int(total * 100),  # Amount in paisa
            'currency': 'INR',
            'payment_capture': '1'
        })

        # Update cart items status
        order_ids = []
        for item in cart_items:
            item.status = 'confirmed'
            item.save()
            order_ids.append(item.id)

        # Send confirmation email
        pdf_buffer = generate_invoice_pdf(order_ids, shipping_info)
        send_order_confirmation_email(request.user, order_ids, shipping_info, pdf_buffer)

        messages.success(request, 'Order placed successfully!')
        return redirect('order_confirmation', order_id=order_ids[0])

    context = {
        'cart_items': cart_items,
        'total': total,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'books/checkout.html', context)

@login_required
def update_cart(request, pk):
    """Update cart item quantity."""
    order = get_object_or_404(Order, pk=pk, user=request.user, status='pending')

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        if quantity > 0:
            order.quantity = quantity
            order.total_price = order.book.price * quantity
            order.save()
            messages.success(request, 'Cart updated successfully!')
        else:
            order.delete()
            messages.success(request, 'Item removed from cart!')

    return redirect('cart')

@login_required
def remove_from_cart(request, pk):
    """Remove item from cart."""
    order = get_object_or_404(Order, pk=pk, user=request.user, status='pending')
    order.delete()
    messages.success(request, 'Item removed from cart!')
    return redirect('cart')

@login_required
def add_to_cart(request, pk):
    """Add book to cart."""
    book = get_object_or_404(Book, pk=pk)

    # Check if item already in cart
    existing_order = Order.objects.filter(user=request.user, book=book, status='pending').first()
    if existing_order:
        existing_order.quantity += 1
        existing_order.total_price = existing_order.book.price * existing_order.quantity
        existing_order.save()
    else:
        Order.objects.create(
            user=request.user,
            book=book,
            quantity=1,
            total_price=book.price,
            status='pending'
        )

    messages.success(request, 'Book added to cart!')
    return redirect('cart')

@login_required
def buy_now(request, pk):
    """Buy book immediately."""
    book = get_object_or_404(Book, pk=pk)

    order = Order.objects.create(
        user=request.user,
        book=book,
        quantity=1,
        total_price=book.price,
        status='confirmed'
    )

    messages.success(request, 'Order placed successfully!')
    return redirect('order_confirmation', order_id=order.id)

@login_required
def add_to_wishlist(request, pk):
    """Add book to wishlist."""
    book = get_object_or_404(Book, pk=pk)

    wishlist_item, created = Wishlist.objects.get_or_create(
        user=request.user,
        book=book
    )

    if created:
        messages.success(request, 'Book added to wishlist!')
    else:
        messages.info(request, 'Book already in wishlist!')

    return redirect('book_detail', pk=pk)

@login_required
def remove_from_wishlist(request, pk):
    """Remove book from wishlist."""
    book = get_object_or_404(Book, pk=pk)
    Wishlist.objects.filter(user=request.user, book=book).delete()
    messages.success(request, 'Book removed from wishlist!')
    return redirect('wishlist')

@login_required
def wishlist(request):
    """Display user's wishlist."""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('book')
    return render(request, 'books/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def order_confirmation(request, order_id):
    """Display order confirmation."""
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'books/order_confirmation.html', {'order': order})

@login_required
def sell_book(request):
    """Allow users to sell their books."""
    if request.method == 'POST':
        title = request.POST.get('title')
        author = request.POST.get('author')
        category = request.POST.get('category')
        genre = request.POST.get('genre')
        description = request.POST.get('description')
        price = request.POST.get('price')
        condition = request.POST.get('condition')
        cover_image = request.FILES.get('cover_image')

        UserBook.objects.create(
            seller=request.user,
            title=title,
            author=author,
            category=category,
            genre=genre,
            description=description,
            price=price,
            condition=condition,
            cover_image=cover_image,
            is_available=True
        )

        messages.success(request, 'Book listed for sale successfully!')
        return redirect('my_listings')

    return render(request, 'books/sell_book.html')

@login_required
def my_listings(request):
    """Display user's book listings."""
    listings = UserBook.objects.filter(seller=request.user)
    return render(request, 'books/my_listings.html', {'listings': listings})

@login_required
def edit_listing(request, pk):
    """Edit user's book listing."""
    listing = get_object_or_404(UserBook, pk=pk, seller=request.user)

    if request.method == 'POST':
        listing.title = request.POST.get('title')
        listing.author = request.POST.get('author')
        listing.category = request.POST.get('category')
        listing.genre = request.POST.get('genre')
        listing.description = request.POST.get('description')
        listing.price = request.POST.get('price')
        listing.condition = request.POST.get('condition')

        if request.FILES.get('cover_image'):
            listing.cover_image = request.FILES.get('cover_image')

        listing.save()
        messages.success(request, 'Listing updated successfully!')
        return redirect('my_listings')

    return render(request, 'books/edit_listing.html', {'listing': listing})

@login_required
def delete_listing(request, pk):
    """Delete user's book listing."""
    listing = get_object_or_404(UserBook, pk=pk, seller=request.user)
    listing.delete()
    messages.success(request, 'Listing deleted successfully!')
    return redirect('my_listings')

@login_required
def buy_user_book(request, pk):
    """Buy a user-sold book."""
    user_book = get_object_or_404(UserBook, pk=pk, is_available=True)

    if request.method == 'POST':
        # Create order for user book
        Order.objects.create(
            user=request.user,
            user_book=user_book,
            quantity=1,
            total_price=user_book.price,
            status='confirmed'
        )

        # Mark book as sold
        user_book.is_available = False
        user_book.save()

        messages.success(request, 'Book purchased successfully!')
        return redirect('order_confirmation', order_id=user_book.id)

    return render(request, 'books/buy_user_book.html', {'user_book': user_book})

def user_book_detail(request, pk):
    """Display details of a user-sold book."""
    user_book = get_object_or_404(UserBook, pk=pk)
    return render(request, 'books/user_book_detail.html', {'user_book': user_book})

def marketplace(request):
    """Display marketplace with user-sold books."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')

    books = UserBook.objects.filter(is_available=True)

    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(description__icontains=query)
        )

    if category:
        books = books.filter(category__iexact=category)

    categories = UserBook.objects.values_list('category', flat=True).distinct()

    context = {
        'books': books,
        'query': query,
        'selected_category': category,
        'categories': categories,
    }
    return render(request, 'books/marketplace.html', context)

@login_required
def add_to_comparison(request, pk):
    """Add book to comparison list."""
    book = get_object_or_404(Book, pk=pk)

    # For simplicity, store in session
    comparison_list = request.session.get('comparison_list', [])
    if pk not in comparison_list:
        comparison_list.append(pk)
        request.session['comparison_list'] = comparison_list
        messages.success(request, 'Book added to comparison!')
    else:
        messages.info(request, 'Book already in comparison list!')

    return redirect('book_detail', pk=pk)

@login_required
def remove_from_comparison(request, pk):
    """Remove book from comparison list."""
    comparison_list = request.session.get('comparison_list', [])
    if pk in comparison_list:
        comparison_list.remove(pk)
        request.session['comparison_list'] = comparison_list
        messages.success(request, 'Book removed from comparison!')

    return redirect('comparison')

@login_required
def comparison(request):
    """Display book comparison."""
    comparison_list = request.session.get('comparison_list', [])
    books = Book.objects.filter(id__in=comparison_list)
    return render(request, 'books/comparison.html', {'books': books})

@login_required
def clear_comparison(request):
    """Clear comparison list."""
    request.session['comparison_list'] = []
    messages.success(request, 'Comparison list cleared!')
    return redirect('comparison')

@login_required
def rate_seller(request, user_book_id):
    """Rate a seller after purchasing their book."""
    user_book = get_object_or_404(UserBook, pk=user_book_id)

    if request.method == 'POST':
        rating = int(request.POST.get('rating'))
        comment = request.POST.get('comment')

        SellerRating.objects.create(
            buyer=request.user,
            seller=user_book.seller,
            user_book=user_book,
            rating=rating,
            comment=comment
        )

        messages.success(request, 'Seller rated successfully!')
        return redirect('dashboard')

    return render(request, 'books/rate_seller.html', {'user_book': user_book})

# API Views
@api_view(['GET'])
def api_book_list(request):
    """API endpoint for book list with semantic search."""
    query = request.GET.get('q', '')
    category = request.GET.get('category', '')
    genre = request.GET.get('genre', '')
    sort_by = request.GET.get('sort', 'title')

    books = Book.objects.all()

    # Apply semantic search if query provided
    if query:
        search_results = semantic_search_books(query, top_n=50)
        book_ids = [book.id for book, score in search_results if hasattr(book, 'id')]
        if book_ids:
            books = books.filter(id__in=book_ids)

    # Apply filters
    if category:
        books = books.filter(category__iexact=category)
    if genre:
        books = books.filter(genre__iexact=genre)

    # Apply sorting
    if sort_by == 'price_low':
        books = books.order_by('price')
    elif sort_by == 'price_high':
        books = books.order_by('-price')
    elif sort_by == 'rating':
        books = books.order_by('-rating')
    elif sort_by == 'newest':
        books = books.order_by('-created_at')
    else:
        books = books.order_by('title')

    serializer = BookSerializer(books[:20], many=True)  # Limit to 20 results
    return Response(serializer.data)

@api_view(['GET'])
def api_recommendations(request):
    """API endpoint for AI-powered book recommendations."""
    user_id = request.GET.get('user_id')
    book_id = request.GET.get('book_id')

    if user_id:
        recommendations = get_recommendations(user_id=user_id)
    elif book_id:
        recommendations = get_recommendations(book_id=book_id)
    else:
        return Response({'error': 'user_id or book_id required'}, status=400)

    return Response({'recommendations': recommendations})

@api_view(['POST'])
def api_chatbot(request):
    """API endpoint for chatbot interaction."""
    message = request.data.get('message')
    user_id = request.data.get('user_id')

    if not message:
        return Response({'error': 'Message is required'}, status=400)

    # Import chatbot logic here to avoid circular imports
    from .chatbot_utils import get_chatbot_response
    response = get_chatbot_response(message, user_id)

    return Response({'response': response})

@api_view(['GET'])
def api_chat_messages(request):
    """API endpoint to get chat messages."""
    user_id = request.GET.get('user_id')
    if not user_id:
        return Response({'error': 'user_id required'}, status=400)

    messages = ChatMessage.objects.filter(user_id=user_id).order_by('-created_at')[:50]
    message_data = [
        {
            'id': msg.id,
            'message': msg.message,
            'response': msg.response,
            'created_at': msg.created_at,
        }
        for msg in messages
    ]

    return Response({'messages': message_data})

@api_view(['POST'])
def api_send_chat_message(request):
    """API endpoint to send a chat message."""
    message = request.data.get('message')
    user_id = request.data.get('user_id')

    if not message or not user_id:
        return Response({'error': 'message and user_id required'}, status=400)

    from .chatbot_utils import get_chatbot_response
    response = get_chatbot_response(message, user_id)

    # Save to database
    ChatMessage.objects.create(
        user_id=user_id,
        message=message,
        response=response
    )

    return Response({'response': response})

@api_view(['POST'])
def api_visual_search(request):
    """API endpoint for visual search."""
    if 'image' not in request.FILES:
        return Response({'error': 'Image file required'}, status=400)

    image_file = request.FILES['image']

    try:
        # Use advanced visual search
        similar_books = find_similar_books_advanced(image_file, top_n=10)
        results = [
            {
                'book_id': book.id,
                'title': book.title,
                'author': book.author,
                'similarity_score': score,
                'cover_image': book.cover_image.url if book.cover_image else None,
            }
            for book, score in similar_books
        ]

        return Response({'results': results})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def api_process_payment(request):
    """API endpoint for payment processing."""
    order_id = request.data.get('order_id')
    payment_id = request.data.get('payment_id')
    signature = request.data.get('signature')

    if not all([order_id, payment_id, signature]):
        return Response({'error': 'Missing payment data'}, status=400)

    # Verify payment with Razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })

        # Update order status
        order = Order.objects.get(razorpay_order_id=order_id)
        order.status = 'paid'
        order.razorpay_payment_id = payment_id
        order.save()

        # Create payment event
        PaymentEvent.objects.create(
            event='payment_successful',
            payload={
                'order_id': order.id,
                'amount': float(order.total_price),
                'payment_id': payment_id
            }
        )

        return Response({'status': 'success'})

    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
def api_payment_webhook(request):
    """Handle Razorpay payment webhooks."""
    # Webhook signature verification would go here
    data = request.data

    # Process webhook data
    if data.get('event') == 'payment.captured':
        payment_id = data['payload']['payment']['entity']['id']
        order_id = data['payload']['payment']['entity']['order_id']

        try:
            order = Order.objects.get(razorpay_order_id=order_id)
            order.status = 'paid'
            order.razorpay_payment_id = payment_id
            order.save()

            PaymentEvent.objects.create(
                event='webhook_payment_captured',
                payload={
                    'order_id': order.id,
                    'amount': float(order.total_price),
                    'payment_id': payment_id
                }
            )

        except Order.DoesNotExist:
            pass

    return Response({'status': 'ok'})

# Helper Functions
def generate_invoice_pdf(order_ids, shipping_info):
    """Generate PDF invoice for orders."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title = Paragraph("Order Invoice", styles['Heading1'])
    story.append(title)
    story.append(Spacer(1, 12))

    # Order details
    for order_id in order_ids:
        order = Order.objects.get(id=order_id)

        order_info = [
            ['Order ID:', str(order.id)],
            ['Date:', order.created_at.strftime('%Y-%m-%d %H:%M:%S')],
            ['Book:', order.book.title if order.book else order.user_book.title],
            ['Quantity:', str(order.quantity)],
            ['Price:', f'₹{order.total_price}'],
        ]

        table = Table(order_info)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 12))

    # Shipping info
    shipping_title = Paragraph("Shipping Information", styles['Heading2'])
    story.append(shipping_title)
    story.append(Spacer(1, 12))

    shipping_data = [
        ['Name:', f"{shipping_info['first_name']} {shipping_info['last_name']}"],
        ['Address:', shipping_info['address']],
        ['City:', shipping_info['city']],
        ['State:', shipping_info['state']],
        ['ZIP:', shipping_info['zip']],
    ]

    shipping_table = Table(shipping_data)
    shipping_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(shipping_table)

    doc.build(story)
    buffer.seek(0)
    return buffer

def send_order_confirmation_email(user, order_ids, shipping_info, pdf_buffer):
    """Send order confirmation email with PDF invoice."""
    subject = 'Order Confirmation - BiblioTrack'
    html_message = get_template('books/order_confirmation_email.html').render({
        'user': user,
        'order_ids': order_ids,
        'shipping_info': shipping_info,
    })

    # In a real application, you would attach the PDF
    # For demo purposes, just send the email
    send_mail(
        subject,
        'Your order has been confirmed. Please find the invoice attached.',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=True,
    )
