import os
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings


class Command(BaseCommand):
    """
    Snapshots every Category and FoodItem currently in the database into
    menu/fixtures/menu_data.json, so this data ships *inside* the project
    folder itself and travels with it when you zip the project.

    Run this AFTER you've finished adding all your real categories and food
    items (with images) through the admin dashboard, and BEFORE you zip the
    project to send to someone else.

    Usage:
        python manage.py export_menu_data
    """
    help = "Export all current categories & food items into menu/fixtures/menu_data.json"

    def handle(self, *args, **options):
        fixtures_dir = os.path.join(settings.BASE_DIR, 'menu', 'fixtures')
        os.makedirs(fixtures_dir, exist_ok=True)
        out_path = os.path.join(fixtures_dir, 'menu_data.json')

        with open(out_path, 'w', encoding='utf-8') as f:
            call_command('dumpdata', 'menu.Category', 'menu.FoodItem', indent=2, stdout=f)

        self.stdout.write(self.style.SUCCESS(f"Exported categories & food items to {out_path}"))
        self.stdout.write(
            "IMPORTANT: this fixture only stores the image *paths* (e.g. 'food/pizza.jpg'), "
            "not the image files. Double-check that the actual image files are present under "
            "media/category/ and media/food/ before zipping the project — those two folders "
            "plus this fixture file are what make everything portable."
        )
