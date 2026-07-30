import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail

from orders.models import Order, OrderStatusHistory
from cart.models import Cart
from .forms import PaymentForm
from .models import Payment


@login_required
def pay(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if order.is_paid:
        return redirect('payments:success', order_id=order.id)
    if order.status == 'cancelled':
        messages.error(request, "This order has been cancelled and can no longer be paid for.")
        return redirect('orders:order_history')

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            card_number = form.cleaned_data['card_number']

            # --- SIMULATED PAYMENT GATEWAY ---
            # This is a demonstration only. No real payment processing occurs.
            # We mark it successful automatically (occasionally you could randomize
            # failures for demo purposes by uncommenting the line below).
            payment_success = True
            # payment_success = random.random() > 0.05  # ~95% success rate demo

            payment = Payment.objects.create(
                order=order,
                cardholder_name=form.cleaned_data['cardholder_name'],
                card_last4=card_number[-4:],
                amount=order.total_amount,
                status='success' if payment_success else 'failed',
            )

            if payment_success:
                order.is_paid = True
                order.status = 'placed'
                order.save()
                OrderStatusHistory.objects.get_or_create(order=order, status='placed')

                # Clear the cart now that checkout is complete
                cart = Cart.objects.filter(user=request.user).first()
                if cart:
                    cart.items.all().delete()

                _send_confirmation_emails(order, payment)
                return redirect('payments:success', order_id=order.id)
            else:
                messages.error(request, "Payment failed. Please check your card details and try again.")
                return redirect('payments:pay', order_id=order.id)
    else:
        form = PaymentForm(initial={'cardholder_name': order.full_name})

    return render(request, 'payments/pay.html', {'order': order, 'form': form})


def _send_confirmation_emails(order, payment):
    try:
        send_mail(
            subject=f"Payment Successful - Order #{order.order_number}",
            message=(
                f"Hi {order.full_name},\n\n"
                f"Your payment of Rs. {payment.amount} was successful.\n"
                f"Transaction ID: {payment.transaction_id}\n"
                f"Payment ID: {payment.payment_id}\n"
                f"Order #{order.order_number} has been placed and is being processed.\n\n"
                f"Thank you for ordering with Food Ordering System!"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.email],
            fail_silently=True,
        )
    except Exception:
        pass


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user, is_paid=True)
    payment = get_object_or_404(Payment, order=order)
    return render(request, 'payments/success.html', {'order': order, 'payment': payment})


@login_required
def download_receipt(request, order_id):
    """Generate a fake payment receipt PDF using ReportLab."""
    from django.http import HttpResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet

    order = get_object_or_404(Order, pk=order_id, user=request.user, is_paid=True)
    payment = get_object_or_404(Payment, order=order)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment.payment_id}.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4, title=f"Receipt {payment.payment_id}")
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("Food Ordering System", styles['Title']),
        Paragraph("Payment Receipt", styles['Heading2']),
        Spacer(1, 6 * mm),
        Paragraph(f"Receipt / Payment ID: {payment.payment_id}", styles['Normal']),
        Paragraph(f"Transaction ID: {payment.transaction_id}", styles['Normal']),
        Paragraph(f"Order Number: {order.order_number}", styles['Normal']),
        Paragraph(f"Customer: {order.full_name} ({order.email})", styles['Normal']),
        Paragraph(f"Payment Date: {payment.created_at.strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']),
        Paragraph(f"Payment Method: {payment.method} ending in {payment.card_last4}", styles['Normal']),
        Spacer(1, 6 * mm),
    ]

    data = [["Item", "Qty", "Price", "Total"]]
    for item in order.items.all():
        data.append([item.food_name, str(item.quantity), f"Rs. {item.price}", f"Rs. {item.line_total}"])
    data.append(["", "", "Total Paid", f"Rs. {payment.amount}"])

    table = Table(data, colWidths=[70 * mm, 20 * mm, 40 * mm, 40 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 8 * mm))
    elements.append(Paragraph(f"Payment Status: {payment.get_status_display().upper()}", styles['Heading3']))
    elements.append(Paragraph("Thank you for your order!", styles['Italic']))

    doc.build(elements)
    return response
