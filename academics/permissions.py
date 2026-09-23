from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import StaffProfile


def role_required(*roles):
    """Allow only superusers or active staff members in the named roles."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            allowed = StaffProfile.objects.filter(
                user=request.user,
                is_active=True,
                role__in=roles,
            ).exists()
            if not allowed:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
