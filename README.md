# Food Ordering System (Django + MySQL)

A working MVP of a food ordering system: customers browse food, add to cart,
checkout, pay through a simulated payment gateway, and track orders. Admins
get a custom dashboard to manage categories, food items, orders, payments,
and basic reports.

**Important:** this project was written and code-reviewed carefully, but it
was **not executed against a live server in the environment it was built in**
(no internet access there to install Django/MySQL). Follow the steps below on
your own machine, where you have Python, pip, and MySQL installed, and it will
run as a normal Django project. If anything errors, it'll be a normal
first-run config issue (missing package, DB not created yet, etc.) — the
troubleshooting section at the bottom covers the common ones.

---

## 1. What's included (MVP scope)

- **Accounts**: register, login/logout, password reset via email, profile edit.
- **Menu**: categories, food items, search, category/price filters, food detail
  page with reviews and a wishlist.
- **Cart**: add/update/remove items, live subtotal/tax/delivery/total.
- **Checkout**: delivery details form → simulated payment page → success page.
- **Simulated payment gateway**: validates card fields, fake loading delay,
  generates a fake Transaction ID / Payment ID, stores the payment, marks the
  order paid.
- **Orders**: order history, order detail with a status timeline, cancel
  (before preparation), public order tracking by Order ID, PDF invoice
  download (ReportLab).
- **Payments**: PDF receipt download.
- **Emails**: registration, order status changes, payment confirmation (via
  console backend by default — real emails print to your terminal until you
  configure SMTP).
- **Custom admin dashboard** (`/dashboard/`, staff-only): stats matching your
  reference screenshot (total/new/confirmed/prepared/cancelled orders,
  registered users, today's/monthly sales), category CRUD, food item CRUD,
  order list + status updates, payment history, and a reports page (daily /
  weekly / monthly / yearly sales, food-wise, customer-wise) with CSV export.
- Django's built-in `/django-admin/` is also wired up as a secondary,
  full-featured admin (useful for quick data fixes).

**Deliberately left out of this MVP** (per your "core first" choice), but the
codebase is structured so each is a small addition later: PDF/Excel export in
the custom reports page (CSV is included), notifications table wired to a
bell icon, guest checkout, and a few of the "nice to have" extras from the
original spec (recently ordered, price filter is in but no slider UI, etc).
Ask and I can add any of these next.

---

## 2. Prerequisites

- Python 3.10+
- MySQL 8.x, running locally (or reachable) with a database created for this project
- pip

On Windows, `mysqlclient` sometimes needs the "Microsoft C++ Build Tools" or a
prebuilt wheel — if `pip install mysqlclient` fails, install it via:
`pip install mysqlclient` after installing MySQL Connector C, **or** simplest
fix: `pip install pymysql` and add these two lines to the very top of
`foodorder/__init__.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

## 3. Setup

```bash
# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the MySQL database (in MySQL Workbench / phpMyAdmin / mysql CLI)
CREATE DATABASE foodorder_db CHARACTER SET utf8mb4;

# 4. Configure environment variables
cp .env.example .env
# then edit .env with your real DB_USER / DB_PASSWORD, or just edit the
# defaults directly in foodorder/settings.py

# 5. Run migrations
python manage.py makemigrations
python manage.py migrate

# 6. Create an admin/staff account (this is what logs into /dashboard/)
python manage.py createsuperuser

# 7. (Optional) Seed some sample categories & food items matching the demo screenshots
python manage.py seed_demo_data

# 8. Run the dev server
python manage.py runserver
```

Then visit:
- **Customer site:** http://127.0.0.1:8000/
- **Custom admin dashboard:** http://127.0.0.1:8000/dashboard/ (log in with
  the superuser you created — it must have `is_staff=True`, which
  `createsuperuser` sets automatically)
- **Built-in Django admin:** http://127.0.0.1:8000/django-admin/

## 4. Trying the full flow

1. Register a customer account (or log in as your superuser — either works
   for shopping).
2. Browse the menu, add a few items to your cart.
3. Go to checkout, fill in delivery details.
4. On the payment page, enter **any** card number of 13–19 digits, any future
   expiry, any 3–4 digit CVV — it's a simulated gateway, so it will always
   validate the format then mark the payment successful.
5. You'll land on the success page with a fake Transaction ID / Payment ID,
   and can download the PDF receipt.
6. Go to `/dashboard/orders/` (as your staff user) and move the order through
   its statuses — this fires a status-update email (visible in your terminal
   with the console email backend).
7. Use "Track Order" on the public site with the Order ID to see the same
   status timeline without logging in.

## 5. Project layout

```
foodorder/          Django project settings/urls
accounts/            Auth, registration, profile, password reset
menu/                Category, FoodItem, Review, Wishlist + browse/search/detail views
cart/                Cart, CartItem
orders/              Order, OrderItem, checkout, tracking, cancel, invoice PDF
payments/            Simulated payment gateway, Payment model, receipt PDF
dashboard/           Staff-only custom admin panel (stats, CRUD, reports)
templates/           All HTML templates (Bootstrap 5)
static/css/style.css Shared styling
```

## 6. Making your categories, food items & images travel with the project

By default, adding categories and food items through `/dashboard/` saves them
into your **MySQL database** — which lives outside the project folder. If you
zip the folder and hand it to someone else, their fresh MySQL database starts
empty even though the images are sitting right there in `media/`. This
project ships with a fixture-based mechanism to fix that, so the person you
send it to doesn't need to re-create anything.

**How it works:** Django "fixtures" are JSON snapshots of database rows that
live inside the project folder itself. `menu/apps.py` is wired to
automatically load `menu/fixtures/menu_data.json` the very first time anyone
runs `python manage.py migrate` on an empty database — no extra command for
them to remember, and it will never overwrite data that's already there.

**Your workflow, once you've finished adding your real categories/food/images
through the dashboard:**

```bash
# 1. Snapshot everything currently in your database into the fixture file
python manage.py export_menu_data

# 2. Confirm the actual image files are present (not just referenced) here:
#      media/category/   -> category images
#      media/food/        -> food item images
#    These folders + the fixture file are what make it portable.

# 3. Zip the whole project folder as normal, including:
#      menu/fixtures/menu_data.json   (the data)
#      media/                          (the images)
```

**What the other person does — nothing extra.** They follow the normal setup
steps in Section 3 of this README. The moment they run
`python manage.py migrate`, your categories and food items appear
automatically, images and all. They never need to open `/dashboard/` or
re-upload anything unless they want to add more.

A starter fixture with sample data (matching the demo screenshots) is already
included so you can see this working immediately — running `export_menu_data`
after you add your own data simply overwrites it with your real catalogue.

> Re-running `export_menu_data` any time later re-snapshots the current
> database state, so keep re-running it whenever you add new items you want
> to ship with the project.

## 7. Extending this MVP

The doc you shared includes more than an MVP covers (notifications table UI,
recently-ordered widget, Excel export, restaurant contact form persistence,
etc). The models for most of these (`Notification`, `Contact`) exist as easy
next additions — happy to build any of them out next; just say which pieces
matter most to you.

## 8. Troubleshooting

- `django.db.utils.OperationalError: (1049, "Unknown database 'foodorder_db'")`
  → you skipped step 3; create the database first.
- `ModuleNotFoundError: No module named 'MySQLdb'` → `pip install mysqlclient`
  failed silently or wasn't run; see the Windows note above for the pymysql
  fallback.
- Images not showing after upload → make sure `Pillow` installed correctly
  and `MEDIA_URL`/`MEDIA_ROOT` are being served (they are, automatically, in
  `DEBUG=True`).
- Emails not appearing → the console backend prints them to the **terminal
  running `runserver`**, not the browser.
