from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from django.core.exceptions import ValidationError

from .models import Attendance, ClassRoom, Course, Enrollment, Invoice, Payment, Result, StaffProfile, Student


class MisReportsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('manager', password='safe-password')
        StaffProfile.objects.create(user=self.user, role=StaffProfile.Role.MANAGER)
        self.client.force_login(self.user)
        today = timezone.localdate()
        student = Student.objects.create(student_code='ST-001', full_name='Test Student', phone='0700000000')
        course = Course.objects.create(name='English', monthly_fee=Decimal('1000.00'))
        classroom = ClassRoom.objects.create(course=course, title='English A', schedule='Morning', start_date=today)
        enrollment = Enrollment.objects.create(student=student, classroom=classroom)
        Attendance.objects.create(enrollment=enrollment, date=today, present=True)
        invoice = Invoice.objects.create(
            student=student, classroom=classroom, amount=Decimal('1000.00'),
            due_date=today - timedelta(days=1),
        )
        Payment.objects.create(invoice=invoice, amount=Decimal('400.00'), paid_at=today, receipt_no='R-001')

    def test_reports_page_shows_management_metrics(self):
        response = self.client.get(reverse('mis_reports'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MIS راپورونه')
        self.assertContains(response, '60')

    def test_reports_show_fee_class_and_full_month_attendance(self):
        response = self.client.get(reverse('mis_reports'), {'month': timezone.localdate().strftime('%Y-%m')})

        self.assertContains(response, 'English A')
        self.assertContains(response, 'Test Student')
        self.assertContains(response, 'حاضر')

    def test_dashboard_is_a_standalone_mis_workspace(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'MIS MANAGEMENT SYSTEM')
        self.assertNotContains(response, 'class="topbar"', html=False)
        self.assertNotContains(response, '<footer>', html=False)

    def test_reports_are_restricted_to_manager_and_accountant_roles(self):
        user = get_user_model().objects.create_user('teacher', password='safe-password')
        StaffProfile.objects.create(user=user, role=StaffProfile.Role.TEACHER)
        self.client.force_login(user)

        response = self.client.get(reverse('mis_reports'))

        self.assertEqual(response.status_code, 403)


class AcademicValidationTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(student_code='ST-VALID', full_name='Valid Student', phone='0700000000')
        self.course = Course.objects.create(name='Validation Course', monthly_fee=Decimal('1000.00'))
        self.classroom = ClassRoom.objects.create(
            course=self.course,
            title='Validation Class',
            schedule='Morning',
            start_date=timezone.localdate(),
        )
        self.enrollment = Enrollment.objects.create(student=self.student, classroom=self.classroom)

    def test_class_end_date_must_not_precede_start_date(self):
        self.classroom.end_date = self.classroom.start_date - timedelta(days=1)

        with self.assertRaises(ValidationError):
            self.classroom.full_clean()

    def test_payment_cannot_exceed_invoice_balance(self):
        invoice = Invoice.objects.create(student=self.student, classroom=self.classroom, amount=Decimal('1000.00'), due_date=timezone.localdate())
        payment = Payment(invoice=invoice, amount=Decimal('1000.01'), paid_at=timezone.localdate(), receipt_no='VALID-001')

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_result_must_match_class_enrollment_and_mark_limit(self):
        from .models import Exam
        exam = Exam.objects.create(classroom=self.classroom, title='Validation Exam', date=timezone.localdate(), total_marks=100)
        result = Result(exam=exam, student=self.student, marks=Decimal('101.00'))

        with self.assertRaises(ValidationError):
            result.full_clean()


class AdminFormLayoutTests(TestCase):
    def test_student_form_does_not_render_admin_navigation(self):
        user = get_user_model().objects.create_superuser(
            username='admin', email='admin@example.com', password='safe-password'
        )
        self.client.force_login(user)

        response = self.client.get('/admin/academics/student/add/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id_student_code')
        self.assertNotContains(response, 'id="nav-sidebar"', html=False)

    def test_student_list_does_not_render_admin_navigation(self):
        user = get_user_model().objects.create_superuser(
            username='list-admin', email='list-admin@example.com', password='safe-password'
        )
        self.client.force_login(user)

        response = self.client.get('/admin/academics/student/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select student to change')
        self.assertNotContains(response, 'id="nav-sidebar"', html=False)
        self.assertNotContains(response, 'Delete selected students')
