from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import Sum
from datetime import timedelta


def add_months(value, months):
    """Return the matching day after `months`, safely handling short months."""
    target_month = value.month - 1 + months
    year = value.year + target_month // 12
    month = target_month % 12 + 1
    from calendar import monthrange
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


class Course(models.Model):
    name = models.CharField(max_length=150)
    level = models.CharField(max_length=80, blank=True)
    duration_months = models.PositiveSmallIntegerField(default=3)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self): return f'{self.name} {self.level}'.strip()


class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    specialty = models.CharField(max_length=150, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    photo = models.FileField(upload_to='teacher_photos/', blank=True, validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self): return self.full_name


class StaffProfile(models.Model):
    """A small, explicit role layer for people who use the centre system."""
    class Role(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super admin'
        MANAGER = 'manager', 'Manager'
        ACCOUNTANT = 'accountant', 'Accountant'
        RECEPTION = 'reception', 'Reception'
        TEACHER = 'teacher', 'Teacher'
        STUDENT = 'student', 'Student'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.RECEPTION)
    photo = models.FileField(
        upload_to='staff_photos/',
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text='Upload a JPG, PNG, or WebP profile photo.',
    )
    phone = models.CharField(max_length=30, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Staff profile'
        verbose_name_plural = 'Staff profiles'

    def __str__(self):
        return f'{self.user} ({self.get_role_display()})'


class ClassRoom(models.Model):
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name='classes')
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=120)
    schedule = models.CharField(max_length=200, help_text='e.g. Saturday–Wednesday, 3:00 PM')
    room = models.CharField(max_length=50, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    attendance_weekdays = models.CharField(
        max_length=20,
        default='5,6,0,1,2',
        help_text='Teaching days: 0=Mon, 1=Tue, …, 5=Sat, 6=Sun. Example Saturday–Wednesday: 5,6,0,1,2.',
    )
    is_active = models.BooleanField(default=True)

    class Meta: verbose_name = 'Class'; verbose_name_plural = 'Classes'

    def clean(self):
        if self.end_date and self.end_date < self.start_date:
            raise ValidationError({'end_date': 'The class end date cannot be before its start date.'})

    def save(self, *args, **kwargs):
        # A class always has a reportable end date unless a specific date is chosen.
        if not self.end_date and self.start_date and self.course_id:
            self.end_date = add_months(self.start_date, self.course.duration_months) - timedelta(days=1)
        super().save(*args, **kwargs)

    def __str__(self): return self.title


class Student(models.Model):
    student_code = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    father_name = models.CharField(max_length=150, blank=True)
    photo = models.FileField(upload_to='student_photos/', blank=True, validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    guardian_name = models.CharField(max_length=150, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    joined_at = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta: ordering = ['full_name']
    def __str__(self): return f'{self.student_code} — {self.full_name}'


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    classroom = models.ForeignKey(ClassRoom, on_delete=models.PROTECT, related_name='enrollments')
    enrolled_at = models.DateField(auto_now_add=True)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'classroom')

    def clean(self):
        if self.classroom_id and self.discount > self.classroom.course.monthly_fee:
            raise ValidationError({'discount': 'Discount cannot be greater than the monthly course fee.'})

    def __str__(self): return f'{self.student} / {self.classroom}'


class Attendance(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE)
    date = models.DateField()
    present = models.BooleanField(default=True)
    note = models.CharField(max_length=200, blank=True)

    class Meta: unique_together = ('enrollment', 'date')


class Invoice(models.Model):
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='invoices')
    # Keep the fee connected to its class.  This makes class-level fee reports
    # accurate when one student attends more than one class.
    classroom = models.ForeignKey(
        ClassRoom,
        on_delete=models.PROTECT,
        related_name='invoices',
        null=False,
        blank=False,
    )
    title = models.CharField(max_length=150, default='Monthly fee')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def paid_amount(self): return sum(payment.amount for payment in self.payments.all())
    @property
    def balance(self): return self.amount - self.paid_amount

    def clean(self):
        if self.classroom_id and self.student_id and not Enrollment.objects.filter(
            student_id=self.student_id,
            classroom_id=self.classroom_id,
        ).exists():
            raise ValidationError({'classroom': 'The selected student is not enrolled in this class.'})

    def __str__(self): return f'Invoice #{self.pk} - {self.student}'


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    paid_at = models.DateField()
    receipt_no = models.CharField(max_length=30, unique=True)
    note = models.CharField(max_length=200, blank=True)

    def clean(self):
        if not self.invoice_id or self.amount is None:
            return
        previously_paid = self.invoice.payments.exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or 0
        if previously_paid + self.amount > self.invoice.amount:
            raise ValidationError({'amount': 'Payment cannot be greater than the invoice balance.'})

    def __str__(self): return self.receipt_no


class Expense(models.Model):
    class Category(models.TextChoices):
        RENT = 'rent', 'Rent'
        SALARY = 'salary', 'Salary'
        UTILITIES = 'utilities', 'Utilities'
        SUPPLIES = 'supplies', 'Supplies'
        OTHER = 'other', 'Other'

    title = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    spent_at = models.DateField()
    note = models.CharField(max_length=250, blank=True)
    receipt_no = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ['-spent_at', '-pk']

    def __str__(self):
        return f'{self.receipt_no} — {self.title}'


class TeacherSalaryPayment(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.PROTECT, related_name='salary_payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    paid_at = models.DateField()
    receipt_no = models.CharField(max_length=30, unique=True)
    note = models.CharField(max_length=250, blank=True)

    class Meta:
        ordering = ['-paid_at', '-pk']

    def __str__(self):
        return f'{self.receipt_no} — {self.teacher}'


class Exam(models.Model):
    classroom = models.ForeignKey(ClassRoom, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    date = models.DateField()
    total_marks = models.PositiveIntegerField(default=100)
    def __str__(self): return self.title


class Result(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    marks = models.DecimalField(max_digits=6, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)
    class Meta: unique_together = ('exam', 'student')

    def clean(self):
        if self.exam_id and self.marks is not None:
            if self.marks < 0 or self.marks > self.exam.total_marks:
                raise ValidationError({'marks': f'Marks must be between 0 and {self.exam.total_marks}.'})
        if self.exam_id and self.student_id and not Enrollment.objects.filter(
            student_id=self.student_id,
            classroom_id=self.exam.classroom_id,
        ).exists():
            raise ValidationError({'student': 'This student is not enrolled in the exam class.'})

    @property
    def percentage(self):
        return round((self.marks / self.exam.total_marks) * 100, 2) if self.exam.total_marks else 0

    @property
    def grade(self):
        score = self.percentage
        if score >= 90: return 'A+'
        if score >= 80: return 'A'
        if score >= 70: return 'B'
        if score >= 60: return 'C'
        if score >= 50: return 'D'
        return 'F'

    @property
    def passed(self):
        return self.percentage >= 50


class Notification(models.Model):
    class Kind(models.TextChoices):
        ENROLLMENT = 'enrollment', 'Enrollment'
        PAYMENT = 'payment', 'Payment'
        ATTENDANCE = 'attendance', 'Attendance'
        EXAM = 'exam', 'Exam'
        SYSTEM = 'system', 'System'

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='mis_notifications')
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.SYSTEM)
    title = models.CharField(max_length=160)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
