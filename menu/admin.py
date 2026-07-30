from django.contrib import admin
from .models import Category, FoodItem, Review, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_available', 'is_featured', 'created_at')
    list_filter = ('category', 'is_available', 'is_featured')
    search_fields = ('name', 'description')
    list_editable = ('price', 'is_available', 'is_featured')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('food_item', 'user', 'rating', 'created_at')
    list_filter = ('rating',)


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('user', 'food_item', 'added_at')
