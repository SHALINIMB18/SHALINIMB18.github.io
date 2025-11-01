from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    genre = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # For deals
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    stock = models.PositiveIntegerField(default=0)
    cover_image_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    image_hash = models.CharField(max_length=64, blank=True, null=True)  # Store perceptual hash
    image_features = models.JSONField(blank=True, null=True)  # Store VGG16 features for visual search
    semantic_embedding = models.JSONField(blank=True, null=True)  # Store Sentence-BERT embeddings for semantic search
    # New ImageField to store uploaded/local cover images under MEDIA_ROOT/books/
    image = models.ImageField(upload_to='books/', blank=True, null=True)
    total_sold = models.PositiveIntegerField(default=0)  # Track sales for best sellers
    is_featured = models.BooleanField(default=False)  # For featured products
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_cover_url(self):
        """Return the best available cover URL: uploaded image -> cover_image_url -> placeholder"""
        try:
            if self.image and hasattr(self.image, 'url'):
                return self.image.url
        except Exception:
            pass
        if self.cover_image_url:
            return self.cover_image_url
        return '/media/books/book_placeholder.svg'

    @property
    def current_price(self):
        """Return the current price considering any active deals"""
        active_deals = Deal.objects.filter(
            book=self,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        )
        if active_deals.exists():
            deal = active_deals.first()
            return self.price * (1 - deal.discount_percentage / 100)
        return self.price

    def get_active_deal(self):
        """Get the active deal for this book if any"""
        return Deal.objects.filter(
            book=self,
            is_active=True,
            start_date__lte=timezone.now(),
            end_date__gte=timezone.now()
        ).first()

class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('cart', 'In Cart'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)
    user_book = models.ForeignKey('UserBook', on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='cart')
    ordered_at = models.DateTimeField(auto_now_add=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    tracking_id = models.CharField(max_length=100, blank=True, null=True)
    delivery_date = models.DateTimeField(blank=True, null=True)
    shipping_address = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.book:
            self.total_price = self.book.current_price * self.quantity
        elif self.user_book:
            self.total_price = self.user_book.price * self.quantity
        super().save(*args, **kwargs)

    def get_book_title(self):
        """Get the title of the book or user book"""
        if self.book:
            return self.book.title
        elif self.user_book:
            return self.user_book.title
        return "Unknown Book"

    def get_book_author(self):
        """Get the author of the book or user book"""
        if self.book:
            return self.book.author
        elif self.user_book:
            return self.user_book.author
        return "Unknown Author"

    def __str__(self):
        book_title = self.get_book_title()
        return f"{self.user.username} - {book_title}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferences = models.JSONField(default=dict)
    history = models.ManyToManyField(Book, related_name='viewed_by', blank=True)

    def __str__(self):
        return self.user.username

    @property
    def average_seller_rating(self):
        """Calculate average rating for this user as a seller"""
        ratings = SellerRating.objects.filter(seller=self.user)
        if ratings.exists():
            return ratings.aggregate(Avg('rating'))['rating__avg']
        return None

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

class UserBook(models.Model):
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
    ]

    seller = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    genre = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='good')
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='user_book_covers/', blank=True, null=True)
    image_hash = models.CharField(max_length=64, blank=True, null=True)  # Store perceptual hash
    image_features = models.JSONField(blank=True, null=True)  # Store VGG16 features for visual search
    semantic_embedding = models.JSONField(blank=True, null=True)  # Store Sentence-BERT embeddings for semantic search
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.seller.username}"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, null=True, blank=True)  # Optional: link to book discussion

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"

class BookClubPost(models.Model):
    """Main discussion threads/posts in the book club forum."""
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_moderated = models.BooleanField(default=False)
    moderation_reason = models.CharField(max_length=100, blank=True, null=True)
    moderation_confidence = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"{self.title} - {self.author.username}"

    @property
    def comment_count(self):
        """Get total number of comments (including nested replies)."""
        return self.comments.count()

    @property
    def recent_activity(self):
        """Get the timestamp of the most recent comment or post update."""
        latest_comment = self.comments.order_by('-created_at').first()
        if latest_comment:
            return max(self.updated_at, latest_comment.created_at)
        return self.updated_at

    def moderate_content(self):
        """Auto-moderate post content using AI."""
        from .moderation_utils import moderate_forum_content

        if self.content:
            result = moderate_forum_content(self.content)
            self.is_moderated = result['is_flagged']
            if result['is_flagged']:
                self.moderation_reason = result['reason']
                self.moderation_confidence = result['confidence']
            self.save()

class BookClubComment(models.Model):
    """Threaded comments/replies in book club discussions."""
    post = models.ForeignKey(BookClubPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    parent_comment = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    like_count = models.PositiveIntegerField(default=0)
    is_moderated = models.BooleanField(default=False)
    moderation_reason = models.CharField(max_length=100, blank=True, null=True)
    moderation_confidence = models.FloatField(default=0.0)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.title}"

    @property
    def is_reply(self):
        """Check if this is a reply to another comment."""
        return self.parent_comment is not None

    @property
    def reply_count(self):
        """Get number of direct replies to this comment."""
        return self.replies.count()

    def moderate_content(self):
        """Auto-moderate comment content using AI."""
        from .moderation_utils import moderate_forum_content

        if self.content:
            result = moderate_forum_content(self.content)
            self.is_moderated = result['is_flagged']
            if result['is_flagged']:
                self.moderation_reason = result['reason']
                self.moderation_confidence = result['confidence']
            self.save()

class BookClubPostLike(models.Model):
    """User likes for book club posts."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(BookClubPost, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.username} liked {self.post.title}"

class BookClubCommentLike(models.Model):
    """User likes for book club comments."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(BookClubComment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')

    def __str__(self):
        return f"{self.user.username} liked comment by {self.comment.author.username}"

class RecentlyViewed(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-viewed_at']
        unique_together = ('user', 'book')

    def __str__(self):
        return f"{self.user.username} viewed {self.book.title}"

class Deal(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(100)])
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.discount_percentage}% off on {self.book.title}"

    @property
    def is_currently_active(self):
        now = timezone.now()
        return self.is_active and self.start_date <= now <= self.end_date

class SellerRating(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_ratings')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_ratings')
    user_book = models.ForeignKey(UserBook, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('buyer', 'user_book')

    def __str__(self):
        return f"{self.buyer.username} rated {self.seller.username} - {self.rating} stars"


class PaymentEvent(models.Model):
    """Simple model to record incoming payment/webhook events for auditing."""
    event = models.CharField(max_length=200)
    payload = models.JSONField(blank=True, null=True)
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event} @ {self.received_at.isoformat()}"

class BookRecommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(1.0)])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'book')
        ordering = ['-score']

    def __str__(self):
        return f"Recommendation for {self.user.username}: {self.book.title} (Score: {self.score})"
