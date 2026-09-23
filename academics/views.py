import csv
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Attendance, Expense, Invoice, Notification, Payment, Result, Student
from .models import ClassRoom, Course, Enrollment, Exam, StaffProfile, Teacher
from .permissions import role_required, teacher_can_access_exam, teacher_can_access_student

@role_required(
    StaffProfile.Role.MANAGER,
    StaffProfile.Role.ACCOUNTANT,
    StaffProfile.Role.RECEPTION,
    StaffProfile.Role.TEACHER,
)
def dashboard(request):
    profile, _ = StaffProfile.objects.get_or_create(
        user=request.user,
        defaults={
            'role': StaffProfile.Role.MANAGER if request.user.is_superuser else StaffProfile.Role.RECEPTION,
        },
    )
    invoices = Invoice.objects.all()
    collected = sum((i.paid_amount for i in invoices), start=0)
    context = {
        'student_count': Student.objects.filter(is_active=True).count(),
        'enrollment_count': Enrollment.objects.filter(is_active=True).count(),
        'teacher_count': Teacher.objects.count(),
        'course_count': Course.objects.filter(is_active=True).count(),
        'class_count': ClassRoom.objects.filter(is_active=True).count(),
        'invoice_count': invoices.count(),
        'collected': collected,
        'outstanding': sum((i.balance for i in invoices), start=0),
        'due_invoice_count': sum(1 for invoice in invoices if invoice.balance > 0),
        'attendance_today': Attendance.objects.filter(date=timezone.localdate()).count(),
        'recent_students': Student.objects.order_by('-joined_at', '-pk')[:8],
        'recent_invoices': invoices.order_by('-created_at')[:8],
        'user_profile': profile,
    }
    return render(request, 'academics/dashboard_en.html' if request.session.get('language') == 'en' else 'academics/dashboard.html', context)


@role_required(StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT)
def reports(request):
    """Management information page: finance, classes, and monthly attendance."""
    today = timezone.localdate()
    requested_month = request.GET.get('month', '')
    try:
        year, month = (int(part) for part in requested_month.split('-', 1))
        month_start = date(year, month, 1)
    except (TypeError, ValueError):
        month_start = date(today.year, today.month, 1)
    month_end = date(month_start.year, month_start.month, monthrange(month_start.year, month_start.month)[1])
    money = Decimal('0.00')

    selected_class = request.GET.get('classroom', '')
    student_query = request.GET.get('student', '').strip()
    active_classes = ClassRoom.objects.filter(is_active=True).select_related('course', 'teacher').order_by('title')
    active_enrollments = Enrollment.objects.filter(is_active=True, classroom__is_active=True).select_related(
        'student', 'classroom__course'
    )
    if selected_class.isdigit():
        active_enrollments = active_enrollments.filter(classroom_id=selected_class)
    else:
        selected_class = ''
    if student_query:
        active_enrollments = active_enrollments.filter(
            Q(student__full_name__icontains=student_query) | Q(student__student_code__icontains=student_query)
        )
    month_payments = Payment.objects.filter(paid_at__range=(month_start, month_end))
    if selected_class:
        month_payments = month_payments.filter(invoice__classroom_id=selected_class)
    if student_query:
        month_payments = month_payments.filter(
            Q(invoice__student__full_name__icontains=student_query) | Q(invoice__student__student_code__icontains=student_query)
        )
    month_collected = month_payments.aggregate(total=Coalesce(Sum('amount'), money))['total']
    month_expenses = Expense.objects.filter(spent_at__range=(month_start, month_end)).aggregate(
        total=Coalesce(Sum('amount'), money)
    )['total']

    course_overview = Course.objects.filter(is_active=True).annotate(
        active_students=Count(
            'classes__enrollments',
            filter=Q(classes__enrollments__is_active=True),
            distinct=True,
        )
    ).order_by('-active_students', 'name')[:8]
    invoices_query = Invoice.objects.filter(due_date__range=(month_start, month_end)).select_related(
        'student', 'classroom'
    ).prefetch_related('payments')
    if selected_class:
        invoices_query = invoices_query.filter(classroom_id=selected_class)
    if student_query:
        invoices_query = invoices_query.filter(
            Q(student__full_name__icontains=student_query) | Q(student__student_code__icontains=student_query)
        )
    invoices = list(invoices_query.order_by('-due_date', '-pk'))
    month_invoiced = sum((invoice.amount for invoice in invoices), start=money)
    outstanding_invoices, paid_invoices, partially_paid_invoices = [], [], []
    class_totals = {}
    for invoice in invoices:
        invoice.report_class = invoice.classroom
        invoice.report_class_name = invoice.classroom.title
        balance = invoice.balance
        if balance == 0:
            paid_invoices.append(invoice)
        else:
            outstanding_invoices.append(invoice)
            if invoice.paid_amount:
                partially_paid_invoices.append(invoice)
        if invoice.classroom_id:
            summary = class_totals.setdefault(invoice.classroom_id, {
                'classroom': invoice.report_class, 'invoiced': money, 'paid': money,
                'outstanding': money, 'invoice_count': 0,
            })
            summary['invoiced'] += invoice.amount
            summary['paid'] += invoice.paid_amount
            summary['outstanding'] += balance
            summary['invoice_count'] += 1

    class_overview = []
    report_classes = active_classes.filter(pk=selected_class) if selected_class else active_classes
    for classroom in report_classes.order_by('end_date', 'title'):
        summary = class_totals.get(classroom.pk, {
            'classroom': classroom, 'invoiced': money, 'paid': money,
            'outstanding': money, 'invoice_count': 0,
        })
        if classroom.end_date:
            summary['days_remaining'] = (classroom.end_date - today).days
        else:
            summary['days_remaining'] = None
        class_overview.append(summary)

    attendance_lookup = {
        (item.enrollment_id, item.date): item
        for item in Attendance.objects.filter(
            enrollment__in=active_enrollments, date__range=(month_start, month_end)
        )
    }
    attendance_records = []
    cursor = month_start
    enrollment_list = list(active_enrollments.order_by('classroom__title', 'student__full_name'))
    while cursor <= month_end:
        for enrollment in enrollment_list:
            weekdays = {int(day) for day in enrollment.classroom.attendance_weekdays.split(',') if day.strip().isdigit()}
            if cursor < enrollment.classroom.start_date or cursor.weekday() not in weekdays:
                continue
            record = attendance_lookup.get((enrollment.pk, cursor))
            attendance_records.append({
                'date': cursor, 'enrollment': enrollment, 'present': record.present if record else None,
                'note': record.note if record else '',
            })
        cursor += timedelta(days=1)
    attendance_records.sort(key=lambda item: (item['date'], item['enrollment'].classroom.title, item['enrollment'].student.full_name), reverse=True)
    attendance_total = len(attendance_records)
    attendance_present = sum(item['present'] is True for item in attendance_records)
    attendance_unrecorded = sum(item['present'] is None for item in attendance_records)
    attendance_rate = round((attendance_present / attendance_total) * 100) if attendance_total else 0
    context = {
        'today': today,
        'month_label': month_start.strftime('%B %Y'),
        'selected_month': month_start.strftime('%Y-%m'),
        'month_collected': month_collected,
        'month_invoiced': month_invoiced,
        'month_balance': sum((invoice.balance for invoice in invoices), start=money),
        'month_expenses': month_expenses,
        'month_net': month_collected - month_expenses,
        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_rate': attendance_rate,
        'attendance_unrecorded': attendance_unrecorded,
        'new_students': Student.objects.filter(joined_at__range=(month_start, month_end)).count(),
        'course_overview': course_overview,
        'outstanding_invoices': outstanding_invoices,
        'paid_invoices': paid_invoices,
        'partially_paid_invoices': partially_paid_invoices,
        'class_overview': class_overview,
        'attendance_records': attendance_records,
        'classes': active_classes,
        'selected_class': selected_class,
        'student_query': student_query,
    }
    return render(request, 'academics/reports_en.html' if request.session.get('language') == 'en' else 'academics/reports.html', context)


@role_required(StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT)
def attendance_csv(request):
    """Download recorded monthly attendance as a spreadsheet-friendly CSV file."""
    requested_month = request.GET.get('month', '')
    try:
        year, month = (int(part) for part in requested_month.split('-', 1))
        month_start = date(year, month, 1)
    except (TypeError, ValueError):
        today = timezone.localdate()
        month_start = date(today.year, today.month, 1)
    month_end = date(month_start.year, month_start.month, monthrange(month_start.year, month_start.month)[1])
    rows = Attendance.objects.filter(date__range=(month_start, month_end)).select_related(
        'enrollment__student', 'enrollment__classroom'
    ).order_by('date', 'enrollment__classroom__title', 'enrollment__student__full_name')
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="attendance-{month_start:%Y-%m}.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['Date', 'Student', 'Class', 'Status', 'Note'])
    for row in rows:
        writer.writerow([row.date, row.enrollment.student.full_name, row.enrollment.classroom.title, 'Present' if row.present else 'Absent', row.note])
    return response


@role_required(
    StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT,
    StaffProfile.Role.RECEPTION, StaffProfile.Role.TEACHER,
)
def student_profile(request, pk):
    """A complete, print-friendly student overview."""
    student = get_object_or_404(Student, pk=pk)
    if request.user.is_authenticated and not request.user.is_superuser:
        profile = StaffProfile.objects.filter(user=request.user, is_active=True).first()
        if profile and profile.role == StaffProfile.Role.TEACHER and not teacher_can_access_student(request.user, student):
            raise PermissionDenied
    enrollments = student.enrollments.select_related('classroom__course', 'classroom__teacher').prefetch_related('attendance_set')
    invoices = student.invoices.select_related('classroom').prefetch_related('payments').order_by('-due_date', '-pk')
    attendance = Attendance.objects.filter(enrollment__student=student).select_related('enrollment__classroom').order_by('-date')
    attendance_total = attendance.count()
    attendance_present = attendance.filter(present=True).count()
    context = {
        'student': student,
        'enrollments': enrollments,
        'invoices': invoices,
        'attendance_records': attendance[:30],
        'attendance_total': attendance_total,
        'attendance_present': attendance_present,
        'attendance_rate': round(attendance_present / attendance_total * 100) if attendance_total else 0,
        'total_invoiced': sum((invoice.amount for invoice in invoices), start=Decimal('0.00')),
        'total_paid': sum((invoice.paid_amount for invoice in invoices), start=Decimal('0.00')),
    }
    context['total_due'] = context['total_invoiced'] - context['total_paid']
    return render(request, 'academics/student_profile.html', context)


@role_required(StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT, StaffProfile.Role.RECEPTION)
def payment_receipt(request, pk):
    payment = get_object_or_404(Payment.objects.select_related('invoice__student', 'invoice__classroom'), pk=pk)
    return render(request, 'academics/payment_receipt.html', {'payment': payment})


@role_required(
    StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT,
    StaffProfile.Role.RECEPTION, StaffProfile.Role.TEACHER,
)
def result_sheet(request, exam_id):
    exam = get_object_or_404(Exam.objects.select_related('classroom__course', 'classroom__teacher'), pk=exam_id)
    if request.user.is_authenticated and not request.user.is_superuser:
        profile = StaffProfile.objects.filter(user=request.user, is_active=True).first()
        if profile and profile.role == StaffProfile.Role.TEACHER and not teacher_can_access_exam(request.user, exam):
            raise PermissionDenied
    results = Result.objects.filter(exam=exam).select_related('student').order_by('-marks', 'student__full_name')
    return render(request, 'academics/result_sheet.html', {'exam': exam, 'results': results})


@role_required(StaffProfile.Role.MANAGER, StaffProfile.Role.ACCOUNTANT)
def notification_list(request):
    notifications = Notification.objects.filter(Q(recipient=request.user) | Q(recipient__isnull=True))
    if request.method == 'POST':
        notifications.filter(is_read=False).update(is_read=True)
    return render(request, 'academics/notifications.html', {'notifications': notifications})
