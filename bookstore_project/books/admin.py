from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Book, Review, Order, Wishlist, UserBook, ChatMessage, BookClubPost, BookClubComment, RecentlyViewed, Deal, SellerRating, PaymentEvent

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    def cover_preview(self, obj):
        if obj.image and hasattr(obj.image, 'url'):
            return mark_safe(f"<img src='{obj.image.url}' style='height:60px; object-fit:cover; border-radius:4px;' />")
        if obj.cover_image_url:
            return mark_safe(f"<img src='{obj.cover_image_url}' style='height:60px; object-fit:cover; border-radius:4px;' />")
        return '(no image)'

    cover_preview.short_description = 'Cover'

    list_display = ('cover_preview', 'title', 'author', 'price', 'current_price', 'rating', 'stock', 'total_sold', 'is_featured')
    list_filter = ('genre', 'category', 'rating', 'is_featured')
    search_fields = ('title', 'author')
    list_editable = ('is_featured',)
    readonly_fields = ('cover_preview',)
    fields = ('cover_preview', 'title', 'author', 'genre', 'category', 'price', 'original_price', 'rating', 'stock', 'cover_image_url', 'image', 'description', 'is_featured')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'user_book', 'quantity', 'status', 'ordered_at', 'total_price')
    list_filter = ('status', 'ordered_at')
    search_fields = ('user__username', 'book__title', 'user_book__title')
    list_editable = ('status',)

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'added_at')
    search_fields = ('user__username', 'book__title')

@admin.register(UserBook)
class UserBookAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'price', 'condition', 'is_available')
    list_filter = ('condition', 'is_available')
    search_fields = ('title', 'seller__username')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'created_at')
    search_fields = ('user__username', 'message')

@admin.register(BookClubPost)
class BookClubPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'view_count', 'like_count', 'comment_count', 'is_pinned', 'is_moderated')
    list_filter = ('is_pinned', 'is_moderated', 'created_at')
    search_fields = ('title', 'content', 'author__username')
    list_editable = ('is_pinned', 'is_moderated')

@admin.register(BookClubComment)
class BookClubCommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'post', 'content', 'created_at', 'like_count', 'is_moderated')
    list_filter = ('is_moderated', 'created_at')
    search_fields = ('content', 'author__username', 'post__title')
    list_editable = ('is_moderated',)

@admin.register(RecentlyViewed)
class RecentlyViewedAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'viewed_at')
    search_fields = ('user__username', 'book__title')

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ('book', 'discount_percentage', 'start_date', 'end_date', 'is_active', 'is_currently_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('book__title',)
    list_editable = ('is_active',)

@admin.register(SellerRating)
class SellerRatingAdmin(admin.ModelAdmin):
    list_display = ('buyer', 'seller', 'user_book', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('buyer__username', 'seller__username', 'user_book__title')


@admin.register(PaymentEvent)
class PaymentEventAdmin(admin.ModelAdmin):
    list_display = ('event', 'received_at')
    readonly_fields = ('event', 'payload', 'received_at')
