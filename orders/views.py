from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from cart.models import Cart
from .models import Order, OrderItem, OrderStatusHistory
from .forms import CheckoutForm


@login_required
def checkout(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('food_item')
    if not items:
        messages.warning(request, "Your cart is empty. Add some food before checking out!")
        return redirect('menu:menu_list')

    subtotal = cart.subtotal
    tax = round(subtotal * settings.TAX_PERCENT / 100, 2)
    delivery = settings.DELIVERY_CHARGE
    total = subtotal + tax + delivery

    initial = {
        'full_name': request.user.get_full_name() or request.user.username,
        'email': request.user.email,
    }
    profile = getattr(request.user, 'profile', None)
    if profile:
        initial.update({'phone': profile.phone, 'address': profile.address, 'city': profile.city,
                         'state': profile.state, 'pincode': profile.pincode})

    if request.method == 'POST':
        form = CheckoutForm(request.POST, initial=initial)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.user = request.user
                order.subtotal = subtotal
                order.tax = tax
                order.delivery_charge = delivery
                order.total_amount = total
                order.save()

                for item in items:
                    OrderItem.objects.create(
                        order=order,
                        food_item=item.food_item,
                        food_name=item.food_item.name,
                        price=item.food_item.price,
                        quantity=item.quantity,
                    )
                OrderStatusHistory.objects.create(order=order, status='placed')
                # NOTE: cart is intentionally left intact until payment succeeds,
                # it is cleared in payments.views.process_payment
            return redirect('payments:pay', order_id=order.id)
    else:
        form = CheckoutForm(initial=initial)

    context = {'form': form, 'items': items, 'subtotal': subtotal, 'tax': tax, 'delivery': delivery, 'total': total}
    return render(request, 'orders/checkout.html', context)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'orders/order_history.html', {'orders': orders})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


def track_order(request):
    order = None
    searched = False
    if request.GET.get('order_number'):
        searched = True
        order_number = request.GET['order_number'].strip()
        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            messages.error(request, "No order found with that Order ID.")
    return render(request, 'orders/track_order.html', {'order': order, 'searched': searched})


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if request.method == 'POST' and order.can_cancel():
        order.status = 'cancelled'
        order.save()
        OrderStatusHistory.objects.create(order=order, status='cancelled')
        send_status_email(order)
        messages.success(request, f"Order #{order.order_number} has been cancelled.")
    else:
        messages.error(request, "This order can no longer be cancelled.")
    return redirect('orders:order_detail', order_id=order.id)


@login_required
def download_invoice(request, order_id):
    """Generate a simple invoice PDF for an order using ReportLab."""
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    order = get_object_or_404(Order, pk=order_id, user=request.user)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="invoice_{order.order_number}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, title=f"Invoice {order.order_number}")
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Food Ordering System", styles['Title']),
        Paragraph(f"Invoice for Order #{order.order_number}", styles['Heading2']),
        Spacer(1, 6 * mm),
        Paragraph(f"Customer: {order.full_name} ({order.email})", styles['Normal']),
        Paragraph(f"Delivery Address: {order.address}, {order.city}, {order.state} - {order.pincode}", styles['Normal']),
        Paragraph(f"Order Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}", styles['Normal']),
        Spacer(1, 6 * mm),
    ]

    data = [["Item", "Qty", "Price", "Total"]]
    for item in order.items.all():
        data.append([item.food_name, str(item.quantity), f"Rs. {item.price}", f"Rs. {item.line_total}"])
    data.append(["", "", "Subtotal", f"Rs. {order.subtotal}"])
    data.append(["", "", "Tax", f"Rs. {order.tax}"])
    data.append(["", "", "Delivery", f"Rs. {order.delivery_charge}"])
    data.append(["", "", "Total", f"Rs. {order.total_amount}"])

    table = Table(data, colWidths=[70 * mm, 20 * mm, 40 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc3545')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph("Thank you for ordering with us!", styles['Italic']))

    doc.build(elements)
    return response


def send_status_email(order):
    try:
        send_mail(
            subject=f"Order #{order.order_number} - Status Update",
            message=(
                f"Hi {order.full_name},\n\n"
                f"Your order #{order.order_number} status is now: {order.get_status_display()}.\n\n"
                f"Thank you for ordering with us!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )
    except Exception:
        pass
