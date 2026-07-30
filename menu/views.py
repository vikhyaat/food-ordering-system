from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Category, FoodItem, Review, Wishlist


def home(request):
    categories = Category.objects.filter(is_active=True)
    featured = FoodItem.objects.filter(is_available=True, is_featured=True)[:6]

    food_list = FoodItem.objects.filter(is_available=True).select_related('category')

    query = request.GET.get('q', '').strip()
    if query:
        food_list = food_list.filter(name__icontains=query)

    paginator = Paginator(food_list, 9)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'categories': categories,
        'featured': featured,
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'menu/home.html', context)


def menu_list(request):
    """Full menu, filterable by category and price."""
    food_list = FoodItem.objects.filter(is_available=True).select_related('category')
    categories = Category.objects.filter(is_active=True)

    category_id = request.GET.get('category')
    if category_id:
        food_list = food_list.filter(category_id=category_id)

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        food_list = food_list.filter(price__gte=min_price)
    if max_price:
        food_list = food_list.filter(price__lte=max_price)

    query = request.GET.get('q', '').strip()
    if query:
        food_list = food_list.filter(Q(name__icontains=query) | Q(description__icontains=query))

    paginator = Paginator(food_list, 9)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'categories': categories,
        'page_obj': page_obj,
        'selected_category': category_id,
        'query': query,
    }
    return render(request, 'menu/menu_list.html', context)


def food_detail(request, pk):
    food_item = get_object_or_404(FoodItem, pk=pk)
    reviews = food_item.reviews.select_related('user')
    is_wishlisted = False
    if request.user.is_authenticated:
        is_wishlisted = Wishlist.objects.filter(user=request.user, food_item=food_item).exists()

    if request.method == 'POST' and request.user.is_authenticated:
        rating = request.POST.get('rating', 5)
        comment = request.POST.get('comment', '')
        Review.objects.create(food_item=food_item, user=request.user, rating=rating, comment=comment)
        messages.success(request, "Thanks for your review!")
        return redirect('menu:food_detail', pk=pk)

    related = FoodItem.objects.filter(category=food_item.category, is_available=True).exclude(pk=pk)[:4]

    context = {
        'food_item': food_item,
        'reviews': reviews,
        'is_wishlisted': is_wishlisted,
        'related': related,
    }
    return render(request, 'menu/food_detail.html', context)


@login_required
def toggle_wishlist(request, pk):
    food_item = get_object_or_404(FoodItem, pk=pk)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, food_item=food_item)
    if not created:
        wishlist_item.delete()
        messages.info(request, f"Removed {food_item.name} from your favourites.")
    else:
        messages.success(request, f"Added {food_item.name} to your favourites.")
    return redirect(request.META.get('HTTP_REFERER', 'menu:home'))


@login_required
def wishlist_view(request):
    items = Wishlist.objects.filter(user=request.user).select_related('food_item')
    return render(request, 'menu/wishlist.html', {'items': items})
