from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from academics.models import (
    Attendance,
    ClassRoom,
    Course,
    Enrollment,
    Invoice,
    Payment,
    Student,
    Teacher,
)


class Command(BaseCommand):
    help = 'Create safe, repeatable sample data for the Education Center MIS.'

    def handle(self, *args, **options):
        today = timezone.localdate()
        course_data = [
            ('English Language', 'Beginner', 4, '2500.00'),
            ('Computer Basics', 'Beginner', 3, '3000.00'),
            ('Advanced English', 'Intermediate', 4, '3000.00'),
            ('Mathematics', 'Grade 9–12', 5, '2200.00'),
        ]
        courses = {}
        for name, level, duration, fee in course_data:
            course, _ = Course.objects.get_or_create(
                name=name,
                level=level,
                defaults={
                    'duration_months': duration,
                    'monthly_fee': Decimal(fee),
                    'description': f'Sample {name} course for MIS reports.',
                    'is_active': True,
                },
            )
            courses[name] = course

        teachers = {}
        for name, phone, specialty, salary in [
            ('Ahmad Wali', '0701000001', 'English', '18000.00'),
            ('Fatima Rahimi', '0701000002', 'Computer Studies', '20000.00'),
            ('Noor Ahmad', '0701000003', 'Mathematics', '19000.00'),
        ]:
            teacher, _ = Teacher.objects.get_or_create(
                full_name=name,
                defaults={'phone': phone, 'specialty': specialty, 'salary': Decimal(salary)},
            )
            teachers[name] = teacher

        classroom_data = [
            ('SEED-ENG-A', 'English A - Morning', 'English Language', 'Ahmad Wali', 'Saturday–Wednesday, 8:00 AM', 'Room 1'),
            ('SEED-COMP-A', 'Computer A - Afternoon', 'Computer Basics', 'Fatima Rahimi', 'Saturday–Wednesday, 2:00 PM', 'Lab 1'),
            ('SEED-ADV-A', 'Advanced English A', 'Advanced English', 'Ahmad Wali', 'Saturday–Wednesday, 10:00 AM', 'Room 2'),
            ('SEED-MATH-A', 'Mathematics A - Evening', 'Mathematics', 'Noor Ahmad', 'Saturday–Wednesday, 4:00 PM', 'Room 3'),
        ]
        classrooms = {}
        for code, title, course_name, teacher_name, schedule, room in classroom_data:
            classroom, _ = ClassRoom.objects.get_or_create(
                title=title,
                defaults={
                    'course': courses[course_name],
                    'teacher': teachers[teacher_name],
                    'schedule': schedule,
                    'room': room,
                    'start_date': today - timedelta(days=45),
                    'is_active': True,
                },
            )
            classrooms[code] = classroom

        names = [
            ('Amina Ahmadi', 'Karim Ahmadi'), ('Bilal Safi', 'Hamid Safi'),
            ('Laila Noori', 'Sami Noori'), ('Omar Rahman', 'Farid Rahman'),
            ('Zahra Mohammadi', 'Jamal Mohammadi'), ('Yusuf Khan', 'Rashid Khan'),
            ('Maryam Azizi', 'Habib Azizi'), ('Samiullah Wardak', 'Nabi Wardak'),
            ('Roya Sadat', 'Naser Sadat'), ('Farzana Amini', 'Latif Amini'),
            ('Hassan Qasimi', 'Amin Qasimi'), ('Mahsa Hakimi', 'Wali Hakimi'),
        ]
        class_codes = list(classrooms)
        enrollments = []
        for index, (name, father_name) in enumerate(names, start=1):
            student, created = Student.objects.get_or_create(
                student_code=f'SEED-{index:03d}',
                defaults={
                    'full_name': name,
                    'father_name': father_name,
                    'phone': f'0702{index:06d}',
                    'guardian_phone': f'0703{index:06d}',
                    'address': 'Kabul, Afghanistan',
                    'is_active': True,
                },
            )
            if created:
                Student.objects.filter(pk=student.pk).update(joined_at=today - timedelta(days=index * 2))
            classroom = classrooms[class_codes[(index - 1) % len(class_codes)]]
            enrollment, _ = Enrollment.objects.get_or_create(student=student, classroom=classroom)
            enrollments.append(enrollment)

            fee = classroom.course.monthly_fee
            invoice, _ = Invoice.objects.get_or_create(
                student=student,
                classroom=classroom,
                title=f'{classroom.course.name} monthly fee',
                due_date=today - timedelta(days=(index % 8) + 1),
                defaults={'amount': fee},
            )
            paid = fee if index % 3 == 0 else fee - Decimal('700.00') if index % 3 == 1 else Decimal('0.00')
            if paid:
                Payment.objects.get_or_create(
                    receipt_no=f'SEED-R-{index:03d}',
                    defaults={
                        'invoice': invoice,
                        'amount': paid,
                        'paid_at': today - timedelta(days=index % 6),
                        'note': 'Sample payment',
                    },
                )

        for day_offset in range(0, min(today.day, 10)):
            attendance_date = today - timedelta(days=day_offset)
            for index, enrollment in enumerate(enrollments):
                Attendance.objects.get_or_create(
                    enrollment=enrollment,
                    date=attendance_date,
                    defaults={'present': (index + day_offset) % 7 != 0},
                )

        self.stdout.write(self.style.SUCCESS(
            'Sample MIS data is ready: 4 courses, 4 classes, 12 students, invoices, payments and attendance.'
        ))
