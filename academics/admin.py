from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import Prefetch
from django.urls import reverse
from django.utils.html import format_html

from .models import Attendance, ClassRoom, Course, Enrollment, Exam, Expense, Invoice, Notification, Payment, Result, StaffProfile, Student, Teacher, TeacherSalaryPayment
from .permissions import get_role


# Admin permissions are intentionally role-based. Django's admin still requires
# is_staff=True, while this layer prevents an active staff role from receiving
# business permissions it was not assigned.
ROLE_MODEL_PERMS = {
    StaffProfile.Role.MANAGER: {
        "Student": {"view", "add", "change", "delete"},
        "Teacher": {"view", "add", "change", "delete"},
        "Course": {"view", "add", "change", "delete"},
        "ClassRoom": {"view", "add", "change", "delete"},
        "Enrollment": {"view", "add", "change", "delete"},
        "Attendance": {"view", "add", "change", "delete"},
        "Invoice": {"view", "add", "change", "delete"},
        "Payment": {"view", "add", "change", "delete"},
        "Expense": {"view", "add", "change", "delete"},
        "TeacherSalaryPayment": {"view", "add", "change", "delete"},
        "Exam": {"view", "add", "change", "delete"},
        "Result": {"view", "add", "change", "delete"},
        "Notification": {"view", "add", "change", "delete"},
    },
    StaffProfile.Role.ACCOUNTANT: {
        "Student": {"view"},
        "Teacher": {"view"},
        "Course": {"view"},
        "ClassRoom": {"view"},
        "Enrollment": {"view"},
        "Attendance": {"view"},
        "Invoice": {"view", "add", "change"},
        "Payment": {"view", "add", "change"},
        "Expense": {"view", "add", "change"},
        "TeacherSalaryPayment": {"view", "add", "change"},
        "Exam": {"view"},
        "Result": {"view"},
        "Notification": {"view"},
    },
    StaffProfile.Role.RECEPTION: {
        "Student": {"view", "add", "change"},
        "Teacher": {"view"},
        "Course": {"view"},
        "ClassRoom": {"view"},
        "Enrollment": {"view", "add", "change"},
        "Attendance": {"view", "add", "change"},
        "Exam": {"view"},
        "Result": {"view"},
    },
}


class RoleBasedModelAdmin(admin.ModelAdmin):
    """Enforce the MIS role matrix at the Django admin boundary."""

    def _allowed(self, request, action):
        role = get_role(request.user)
        if role == StaffProfile.Role.SUPER_ADMIN:
            return True
        return action in ROLE_MODEL_PERMS.get(role, {}).get(self.model.__name__, set())

    def has_module_permission(self, request):
        return self._allowed(request, "view")

    def has_view_permission(self, request, obj=None):
        return self._allowed(request, "view")

    def has_add_permission(self, request):
        return self._allowed(request, "add")

    def has_change_permission(self, request, obj=None):
        return self._allowed(request, "change")

    def has_delete_permission(self, request, obj=None):
        return self._allowed(request, "delete")




def _enrollment_details(student):
    """Return active enrolments, or all enrolments when none are active."""
    enrollments = list(student.enrollments.all())
    return [item for item in enrollments if item.is_active] or enrollments


@admin.register(Student)
class StudentAdmin(RoleBasedModelAdmin):
    list_display = (
        'student_code', 'full_name', 'father_name', 'phone', 'guardian_phone',
        'classes', 'courses', 'teachers', 'class_start_dates', 'class_times',
        'monthly_fees', 'class_end_dates', 'attendance_summary', 'last_attendance', 'total_fee',
        'paid_fee', 'remaining_fee', 'is_active', 'joined_at',
        'open_profile',
    )
    list_filter = ('is_active', 'enrollments__classroom__course', 'enrollments__classroom__teacher')
    search_fields = (
        'student_code', 'full_name', 'father_name', 'phone', 'guardian_phone', 'address',
        'enrollments__classroom__title', 'enrollments__classroom__course__name',
        'enrollments__classroom__teacher__full_name', 'enrollments__classroom__schedule',
        '=enrollments__classroom__course__monthly_fee',
    )
    ordering = ('-joined_at', '-pk')
    actions = None
    list_per_page = 25
    fields = (
        ('student_code', 'full_name'), 'photo', ('father_name', 'guardian_name'), ('phone', 'guardian_phone'),
        'email', 'address', 'is_active',
    )

    def get_queryset(self, request):
        enrollment_queryset = Enrollment.objects.select_related(
            'classroom__course', 'classroom__teacher'
        ).prefetch_related('attendance_set')
        invoice_queryset = Invoice.objects.prefetch_related('payments')
        return super().get_queryset(request).prefetch_related(
            Prefetch('enrollments', queryset=enrollment_queryset),
            Prefetch('invoices', queryset=invoice_queryset),
        )

    def get_search_results(self, request, queryset, search_term):
        queryset, _ = super().get_search_results(request, queryset, search_term)
        return queryset, True

    @admin.display(description='Class')
    def classes(self, student):
        return ', '.join(item.classroom.title for item in _enrollment_details(student)) or '—'

    @admin.display(description='Course')
    def courses(self, student):
        return ', '.join(item.classroom.course.name for item in _enrollment_details(student)) or '—'

    @admin.display(description='Teacher')
    def teachers(self, student):
        return ', '.join(
            item.classroom.teacher.full_name if item.classroom.teacher else '—'
            for item in _enrollment_details(student)
        ) or '—'

    @admin.display(description='Class start')
    def class_start_dates(self, student):
        return ', '.join(item.classroom.start_date.strftime('%Y-%m-%d') for item in _enrollment_details(student)) or '—'

    @admin.display(description='Time')
    def class_times(self, student):
        return ', '.join(item.classroom.schedule for item in _enrollment_details(student)) or '—'

    @admin.display(description='Monthly fee')
    def monthly_fees(self, student):
        return ', '.join(str(item.classroom.course.monthly_fee) for item in _enrollment_details(student)) or '—'

    @admin.display(description='Class end')
    def class_end_dates(self, student):
        dates = []
        for item in _enrollment_details(student):
            dates.append(item.classroom.end_date.strftime('%Y-%m-%d') if item.classroom.end_date else 'In progress')
        return ', '.join(dates) or '—'

    @admin.display(description='Attendance')
    def attendance_summary(self, student):
        records = [record for item in _enrollment_details(student) for record in item.attendance_set.all()]
        if not records:
            return '—'
        present = sum(record.present for record in records)
        return f'{present}/{len(records)} ({round(present / len(records) * 100)}%)'

    @admin.display(description='Last attendance')
    def last_attendance(self, student):
        records = [record for item in _enrollment_details(student) for record in item.attendance_set.all()]
        return max((record.date for record in records), default=None) or '—'

    def _invoice_totals(self, student):
        invoices = list(student.invoices.all())
        total = sum((invoice.amount for invoice in invoices), start=0)
        paid = sum((payment.amount for invoice in invoices for payment in invoice.payments.all()), start=0)
        return total, paid

    @admin.display(description='Total fee')
    def total_fee(self, student):
        return self._invoice_totals(student)[0]

    @admin.display(description='Paid fee')
    def paid_fee(self, student):
        return self._invoice_totals(student)[1]

    @admin.display(description='Remaining fee')
    def remaining_fee(self, student):
        total, paid = self._invoice_totals(student)
        return total - paid

    @admin.display(description='Profile')
    def open_profile(self, student):
        return format_html('<a href="{}" target="_blank">Open profile</a>', reverse('student_profile', args=[student.pk]))


@admin.register(Teacher)
class TeacherAdmin(RoleBasedModelAdmin):
    list_display = ('full_name', 'phone', 'email', 'specialty', 'salary', 'assigned_classes')
    search_fields = ('full_name', 'phone', 'specialty', 'classroom__title', 'classroom__course__name', 'classroom__schedule')
    list_filter = ('specialty',)
    fields = ('user', 'full_name', 'photo', 'phone', 'email', 'address', 'specialty', 'salary')

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('classroom_set__course')

    @admin.display(description='Classes / time')
    def assigned_classes(self, teacher):
        return ', '.join(f'{item.title} ({item.schedule})' for item in teacher.classroom_set.all()) or '—'


@admin.register(Course)
class CourseAdmin(RoleBasedModelAdmin):
    list_display = ('name', 'level', 'duration_months', 'monthly_fee', 'is_active')
    list_filter = ('is_active', 'level')
    search_fields = ('name', 'level', 'description', '=monthly_fee')


@admin.register(ClassRoom)
class ClassRoomAdmin(RoleBasedModelAdmin):
    list_display = ('title', 'course', 'teacher', 'room', 'schedule', 'start_date', 'end_date', 'attendance_weekdays', 'is_active')
    list_filter = ('is_active', 'course', 'teacher', 'start_date')
    search_fields = ('title', 'room', 'schedule', 'course__name', 'teacher__full_name')
    list_select_related = ('course', 'teacher')


@admin.register(Enrollment)
class EnrollmentAdmin(RoleBasedModelAdmin):
    list_display = ('student', 'classroom', 'course', 'teacher', 'class_start', 'schedule', 'discount', 'enrolled_at', 'is_active')
    list_filter = ('is_active', 'classroom__course', 'classroom__teacher')
    search_fields = (
        'student__student_code', 'student__full_name', 'student__father_name',
        'classroom__title', 'classroom__course__name', 'classroom__teacher__full_name', 'classroom__schedule',
    )
    list_select_related = ('student', 'classroom__course', 'classroom__teacher')

    @admin.display(description='Course')
    def course(self, enrollment):
        return enrollment.classroom.course

    @admin.display(description='Teacher')
    def teacher(self, enrollment):
        return enrollment.classroom.teacher or '—'

    @admin.display(description='Class start', ordering='classroom__start_date')
    def class_start(self, enrollment):
        return enrollment.classroom.start_date

    @admin.display(description='Time')
    def schedule(self, enrollment):
        return enrollment.classroom.schedule


@admin.register(Attendance)
class AttendanceAdmin(RoleBasedModelAdmin):
    list_display = ('enrollment', 'date', 'present', 'note')
    list_filter = ('present', 'date')
    search_fields = ('enrollment__student__full_name', 'enrollment__student__student_code', 'enrollment__classroom__title')


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(RoleBasedModelAdmin):
    list_display = ('id', 'student', 'classroom', 'title', 'amount', 'due_date', 'balance')
    list_filter = ('classroom', 'due_date',)
    search_fields = ('student__student_code', 'student__full_name', 'student__father_name', 'classroom__title', 'title')
    list_select_related = ('student', 'classroom')
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(RoleBasedModelAdmin):
    list_display = ('receipt_no', 'invoice', 'amount', 'paid_at', 'print_receipt')
    list_filter = ('paid_at', 'invoice__classroom')
    search_fields = ('receipt_no', 'invoice__student__full_name', 'invoice__student__student_code', 'note')
    list_select_related = ('invoice__student', 'invoice__classroom')

    @admin.display(description='Receipt')
    def print_receipt(self, payment):
        return format_html('<a href="{}" target="_blank">Print receipt</a>', reverse('payment_receipt', args=[payment.pk]))


@admin.register(Expense)
class ExpenseAdmin(RoleBasedModelAdmin):
    list_display = ('receipt_no', 'title', 'category', 'amount', 'spent_at')
    list_filter = ('category', 'spent_at')
    search_fields = ('receipt_no', 'title', 'note')
    ordering = ('-spent_at', '-pk')


@admin.register(TeacherSalaryPayment)
class TeacherSalaryPaymentAdmin(RoleBasedModelAdmin):
    list_display = ('receipt_no', 'teacher', 'amount', 'paid_at')
    list_filter = ('paid_at', 'teacher')
    search_fields = ('receipt_no', 'teacher__full_name', 'note')


@admin.register(Notification)
class NotificationAdmin(RoleBasedModelAdmin):
    list_display = ('title', 'kind', 'recipient', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    readonly_fields = ('created_at',)


@admin.register(Result)
class ResultAdmin(RoleBasedModelAdmin):
    list_display = ('exam', 'student', 'marks', 'percentage_value', 'grade_value', 'pass_status')
    list_filter = ('exam',)
    search_fields = ('student__student_code', 'student__full_name', 'exam__title')
    list_select_related = ('exam', 'student')

    @admin.display(description='Percentage')
    def percentage_value(self, result):
        return f'{result.percentage}%'

    @admin.display(description='Grade')
    def grade_value(self, result):
        return result.grade

    @admin.display(boolean=True, description='Passed')
    def pass_status(self, result):
        return result.passed


@admin.register(StaffProfile)
class StaffProfileAdmin(RoleBasedModelAdmin):
    list_display = ('user', 'role', 'phone', 'has_photo', 'is_active')
    list_filter = ('role', 'is_active')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')
    fields = ('user', 'role', 'photo', 'phone', 'is_active')

    @admin.display(boolean=True, description='Photo')
    def has_photo(self, profile):
        return bool(profile.photo)


class StaffProfileInline(admin.StackedInline):
    model = StaffProfile
    extra = 1
    max_num = 1
    can_delete = False
    fields = ('role', 'photo', 'phone', 'is_active')
    verbose_name = 'Staff profile photo and role'
    verbose_name_plural = 'Staff profile photo and role'


class EducationCenterUserAdmin(UserAdmin):
    inlines = (StaffProfileInline,)

    def _superuser_only(self, request):
        return request.user.is_superuser

    def has_module_permission(self, request):
        return self._superuser_only(request)

    def has_view_permission(self, request, obj=None):
        return self._superuser_only(request)

    def has_add_permission(self, request):
        return self._superuser_only(request)

    def has_change_permission(self, request, obj=None):
        return self._superuser_only(request)

    def has_delete_permission(self, request, obj=None):
        return self._superuser_only(request)


User = get_user_model()
admin.site.unregister(User)
admin.site.register(User, EducationCenterUserAdmin)


admin.site.register(Exam, RoleBasedModelAdmin)
