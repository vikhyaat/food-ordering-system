import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate


def load_initial_menu_data(sender, **kwargs):
    """
    Runs automatically every time `python manage.py migrate` finishes.

    If menu/fixtures/menu_data.json exists AND the Category table is
    currently empty, it loads that fixture straight in. This is what makes
    the project "plug and play" for anyone you hand the zip to: they run
    the normal setup commands, and your categories/food items just appear
    - no manual re-entry, no extra command to remember.

    It deliberately does nothing if Category already has rows, so it will
    never overwrite or duplicate data on later migrations.
    """
    from django.conf import settings
    from django.core.management import call_command
    from django.db.utils import OperationalError, ProgrammingError

    fixture_path = os.path.join(settings.BASE_DIR, 'menu', 'fixtures', 'menu_data.json')
    if not os.path.exists(fixture_path):
        return

    try:
        from .models import Category
        if Category.objects.exists():
            return
    except (OperationalError, ProgrammingError):
        # Tables don't exist yet on this particular migrate pass - skip safely.
        return

    call_command('loaddata', fixture_path, verbosity=0)
    print("[menu] Loaded categories & food items from menu/fixtures/menu_data.json")


class MenuConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'menu'

    def ready(self):
        post_migrate.connect(load_initial_menu_data, sender=self)
