import csv
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.http import HttpResponse

from .decorators import staff_required
from .forms import CategoryForm, FoodItemForm
from menu.models import Category, FoodItem
from orders.models import Order, OrderItem, OrderStatusHistory
from orders.views import send_status_email
from payments.models import Payment
from accounts.models import UserProfile


# ---------------------------------------------------------------------------
# Helper: timezone-safe "start of day" boundaries.
#
# WHY: filtering with `created_at__date=today` asks MySQL to convert the
# stored UTC timestamp into local time using CONVERT_TZ(), which silently
# returns NULL (i.e. matches nothing) unless MySQL's timezone tables have
# been loaded on the server - something that is almost never done by
# default, especially on Windows installs. That NULL-matches-nothing
# behaviour is exactly why "Today's Sales" / "Monthly Sales" showed Rs. 0
# even though paid orders existed.
#
# THE FIX: instead of asking the database to extract a "date", we compute
# the local midnight boundary ourselves in Python (using Django's
# timezone.localtime, which always works) and then filter with a plain
# `created_at__gte` / `created_at__lt` range. Comparing two aware
# datetimes doesn't need any server-side timezone table at all - Django
# converts everything to UTC before it ever reaches MySQL.
# ---------------------------------------------------------------------------
def _day_start(dt):
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _local_now():
    return timezone.localtime(timezone.now())


# ---------------------------------------------------------------------------
# DASHBOARD HOME
# ---------------------------------------------------------------------------
@staff_required
def dashboard_home(request):
    now_local = _local_now()
    today_start = _day_start(now_local)
    today_end = today_start + timedelta(days=1)
    month_start = today_start.replace(day=1)

    orders = Order.objects.all()
    paid_orders = orders.filter(is_paid=True)

    context = {
        'total_users': User.objects.filter(is_staff=False).count(),
        'total_categories': Category.objects.count(),
        'total_food_items': FoodItem.objects.count(),
        'total_orders': orders.count(),
        'new_orders': orders.filter(status='placed').count(),
        'confirmed_orders': orders.filter(status='confirmed').count(),
        'preparing_orders': orders.filter(status='preparing').count(),
        'ready_orders': orders.filter(status='ready').count(),
        'out_for_delivery_orders': orders.filter(status='out_for_delivery').count(),
        'delivered_orders': orders.filter(status='delivered').count(),
        'cancelled_orders': orders.filter(status='cancelled').count(),
        'todays_sales': paid_orders.filter(
            created_at__gte=today_start, created_at__lt=today_end
        ).aggregate(s=Sum('total_amount'))['s'] or 0,
        'monthly_sales': paid_orders.filter(
            created_at__gte=month_start
        ).aggregate(s=Sum('total_amount'))['s'] or 0,
        'recent_orders': orders.order_by('-created_at')[:8],
    }
    return render(request, 'dashboard/home.html', context)


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------
@staff_required
def manage_users(request):
    users = User.objects.filter(is_staff=False).select_related('profile')
    query = request.GET.get('q', '').strip()
    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query))
    return render(request, 'dashboard/users.html', {'users': users, 'query': query})


@staff_required
def toggle_block_user(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_staff=False)
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.is_blocked = not profile.is_blocked
    profile.save()
    messages.success(request, f"{user.username} has been {'blocked' if profile.is_blocked else 'unblocked'}.")
    return redirect('dashboard:manage_users')


@staff_required
def delete_user(request, user_id):
    user = get_object_or_404(User, pk=user_id, is_staff=False)
    if request.method == 'POST':
        user.delete()
        messages.success(request, "User deleted.")
    return redirect('dashboard:manage_users')


# ---------------------------------------------------------------------------
# CATEGORY MANAGEMENT
# ---------------------------------------------------------------------------
@staff_required
def manage_categories(request):
    categories = Category.objects.all()
    return render(request, 'dashboard/categories.html', {'categories': categories})


@staff_required
def category_form_view(request, pk=None):
    category = get_object_or_404(Category, pk=pk) if pk else None
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, "Category saved.")
            return redirect('dashboard:manage_categories')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'dashboard/category_form.html', {'form': form, 'category': category})


@staff_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        category.delete()
        messages.success(request, "Category deleted.")
    return redirect('dashboard:manage_categories')


# ---------------------------------------------------------------------------
# FOOD MENU MANAGEMENT
# ---------------------------------------------------------------------------
@staff_required
def manage_food(request):
    food_items = FoodItem.objects.select_related('category').all()
    return render(request, 'dashboard/food_items.html', {'food_items': food_items})


@staff_required
def food_form_view(request, pk=None):
    food_item = get_object_or_404(FoodItem, pk=pk) if pk else None
    if request.method == 'POST':
        form = FoodItemForm(request.POST, request.FILES, instance=food_item)
        if form.is_valid():
            form.save()
            messages.success(request, "Food item saved.")
            return redirect('dashboard:manage_food')
    else:
        form = FoodItemForm(instance=food_item)
    return render(request, 'dashboard/food_item_form.html', {'form': form, 'food_item': food_item})


@staff_required
def delete_food(request, pk):
    food_item = get_object_or_404(FoodItem, pk=pk)
    if request.method == 'POST':
        food_item.delete()
        messages.success(request, "Food item deleted.")
    return redirect('dashboard:manage_food')


# ---------------------------------------------------------------------------
# ORDER MANAGEMENT
# ---------------------------------------------------------------------------
@staff_required
def manage_orders(request):
    orders = Order.objects.select_related('user').all()

    order_id = request.GET.get('order_id', '').strip()
    customer = request.GET.get('customer', '').strip()
    email = request.GET.get('email', '').strip()
    date_str = request.GET.get('date', '').strip()

    if order_id:
        orders = orders.filter(order_number__icontains=order_id)
    if customer:
        orders = orders.filter(full_name__icontains=customer)
    if email:
        orders = orders.filter(email__icontains=email)
    if date_str:
        try:
            search_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
            day_start = timezone.make_aware(timezone.datetime.combine(search_date, timezone.datetime.min.time()))
            day_end = day_start + timedelta(days=1)
            orders = orders.filter(created_at__gte=day_start, created_at__lt=day_end)
        except ValueError:
            pass

    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'order_id': order_id, 'customer': customer, 'email': email, 'date_str': date_str,
    }
    return render(request, 'dashboard/orders.html', context)


@staff_required
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            OrderStatusHistory.objects.create(order=order, status=new_status)
            send_status_email(order)
            messages.success(request, f"Order #{order.order_number} status updated to {order.get_status_display()}.")
    return redirect('dashboard:manage_orders')


# ---------------------------------------------------------------------------
# PAYMENT MANAGEMENT
# ---------------------------------------------------------------------------
@staff_required
def manage_payments(request):
    payments = Payment.objects.select_related('order').all()
    status = request.GET.get('status')
    if status in ('success', 'failed'):
        payments = payments.filter(status=status)
    return render(request, 'dashboard/payments.html', {'payments': payments, 'status': status})


# ---------------------------------------------------------------------------
# REPORTS
# ---------------------------------------------------------------------------
@staff_required
def reports(request):
    now_local = _local_now()
    today_start = _day_start(now_local)

    ranges = {
        'daily': today_start,
        'weekly': today_start - timedelta(days=7),
        'monthly': today_start - timedelta(days=30),
        'yearly': today_start - timedelta(days=365),
    }
    paid_orders = Order.objects.filter(is_paid=True)
    sales_summary = {
        label: paid_orders.filter(created_at__gte=start).aggregate(total=Sum('total_amount'), count=Count('id'))
        for label, start in ranges.items()
    }

    food_wise = (OrderItem.objects.filter(order__is_paid=True).values('food_name')
                 .annotate(total_qty=Sum('quantity'), total_sales=Sum('price'))
                 .order_by('-total_qty')[:15])

    customer_wise = (Order.objects.filter(is_paid=True).values('full_name', 'email')
                      .annotate(order_count=Count('id'), total_spent=Sum('total_amount'))
                      .order_by('-total_spent')[:15])

    context = {'sales_summary': sales_summary, 'food_wise': food_wise, 'customer_wise': customer_wise}
    return render(request, 'dashboard/reports.html', context)


@staff_required
def export_orders_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="orders_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Order Number', 'Customer', 'Email', 'Status', 'Total', 'Paid', 'Date'])
    for o in Order.objects.all():
        writer.writerow([o.order_number, o.full_name, o.email, o.get_status_display(), o.total_amount, o.is_paid, o.created_at])
    return response
