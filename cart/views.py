from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.conf import settings
from menu.models import FoodItem
from .models import Cart, CartItem


def _get_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    return cart


@login_required
@require_POST
def add_to_cart(request, pk):
    food_item = get_object_or_404(FoodItem, pk=pk, is_available=True)
    quantity = int(request.POST.get('quantity', 1) or 1)
    cart = _get_cart(request)
    item, created = CartItem.objects.get_or_create(cart=cart, food_item=food_item, defaults={'quantity': quantity})
    if not created:
        item.quantity += quantity
        item.save()
    messages.success(request, f"Added {food_item.name} to your cart.")
    return redirect(request.POST.get('next') or 'cart:view_cart')


@login_required
def view_cart(request):
    cart = _get_cart(request)
    items = cart.items.select_related('food_item')
    subtotal = cart.subtotal
    tax = round(subtotal * settings.TAX_PERCENT / 100, 2) if subtotal else 0
    delivery = settings.DELIVERY_CHARGE if subtotal else 0
    total = subtotal + tax + delivery
    context = {
        'items': items,
        'subtotal': subtotal,
        'tax': tax,
        'delivery': delivery,
        'total': total,
    }
    return render(request, 'cart/cart.html', context)


@login_required
@require_POST
def update_quantity(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    action = request.POST.get('action')
    if action == 'increase':
        item.quantity += 1
        item.save()
    elif action == 'decrease':
        item.quantity -= 1
        if item.quantity <= 0:
            item.delete()
        else:
            item.save()
    return redirect('cart:view_cart')


@login_required
@require_POST
def remove_item(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, cart__user=request.user)
    item.delete()
    messages.info(request, "Item removed from cart.")
    return redirect('cart:view_cart')
