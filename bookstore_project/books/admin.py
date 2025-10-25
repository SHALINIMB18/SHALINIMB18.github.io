from django.contrib import admin
from .models import Book, Review, Order, UserProfile

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'price', 'rating', 'stock')
    search_fields = ('title', 'author', 'genre')
    list_filter = ('genre', 'category')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'rating', 'created_at')
    search_fields = ('user__username', 'book__title')
    list_filter = ('rating', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'quantity', 'status', 'ordered_at')
    search_fields = ('user__username', 'book__title')
    list_filter = ('status', 'ordered_at')

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'preferences')
    search_fields = ('user__username',)
