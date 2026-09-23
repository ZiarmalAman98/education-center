from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import StaffProfile


def get_staff_profile(user):
    """Return the active StaffProfile for a user, or None."""
    if not user.is_authenticated:
        return None
    return StaffProfile.objects.filter(user=user, is_active=True).first()


def get_role(user):
    """Return the user's active role."""
    if user.is_superuser:
        return StaffProfile.Role.SUPER_ADMIN
    profile = get_staff_profile(user)
    return profile.role if profile else None


def has_role(user, *roles):
    """Check an authenticated user's active StaffProfile role."""
    if user.is_superuser:
        return True
    role = get_role(user)
    return role in roles


def role_required(*roles):
    """Allow only superusers or active staff members in the named roles."""
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not has_role(request.user, *roles):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def teacher_can_access_student(user, student):
    """Teachers may access only students enrolled in one of their classes."""
    if user.is_superuser:
        return True
    if not has_role(user, StaffProfile.Role.TEACHER):
        return False
    return student.enrollments.filter(
        classroom__teacher__user=user,
        is_active=True,
    ).exists()


def teacher_can_access_exam(user, exam):
    """Teachers may access only exams belonging to their assigned classes."""
    if user.is_superuser:
        return True
    if not has_role(user, StaffProfile.Role.TEACHER):
        return False
    return exam.classroom.teacher_id == getattr(
        getattr(user, "teacher", None), "pk", None
    )
