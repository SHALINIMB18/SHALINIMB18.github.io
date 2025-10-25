from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=100)
    genre = models.CharField(max_length=50)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rating = models.FloatField(default=0.0, validators=[MinValueValidator(0.0), MaxValueValidator(5.0)])
    stock = models.PositiveIntegerField(default=0)
    cover_image_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True)
    image_hash = models.CharField(max_length=64, blank=True, null=True)  # Store perceptual hash
    image_features = models.JSONField(blank=True, null=True)  # Store VGG16 features for visual search
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

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
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
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
            self.total_price = self.book.price * self.quantity
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

class BookClub(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    discussion_topic = models.CharField(max_length=200)
    comments = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.discussion_topic} - {self.user.username}"
