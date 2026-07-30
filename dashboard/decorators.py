from django.contrib.auth.decorators import user_passes_test


def staff_required(view_func):
    """Only allow staff/admin users into the custom dashboard."""
    return user_passes_test(lambda u: u.is_active and u.is_staff, login_url='accounts:login')(view_func)
