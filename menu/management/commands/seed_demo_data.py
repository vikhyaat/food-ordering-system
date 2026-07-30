from django.core.management.base import BaseCommand
from menu.models import Category, FoodItem


class Command(BaseCommand):
    help = "Populate the database with sample categories and food items for demo/testing."

    def handle(self, *args, **options):
        data = {
            "Pizza": [
                ("Corn Pizza", 180, True),
                ("Veg Extravaganza Pizza", 450, False),
            ],
            "South Indian": [
                ("Dosa", 85, False),
                ("Idli", 75, False),
                ("Vada", 60, False),
            ],
            "North Indian": [
                ("Chana Masala", 120, True),
                ("Rajma Masala", 125, False),
                ("Chole Bhature", 120, False),
                ("Aloo Paratha", 85, False),
            ],
        }

        for cat_name, items in data.items():
            category, _ = Category.objects.get_or_create(name=cat_name)
            for name, price, featured in items:
                FoodItem.objects.get_or_create(
                    category=category,
                    name=name,
                    defaults={
                        "price": price,
                        "description": f"Delicious {name}, freshly prepared and ready to order.",
                        "is_available": True,
                        "is_featured": featured,
                    },
                )

        self.stdout.write(self.style.SUCCESS("Demo categories and food items created successfully."))
