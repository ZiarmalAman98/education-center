"""Create lightweight in-system notifications for important MIS events."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Attendance, Enrollment, Exam, Notification, Payment


@receiver(post_save, sender=Enrollment)
def enrollment_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            kind=Notification.Kind.ENROLLMENT,
            title='New enrollment',
            message=f'{instance.student.full_name} enrolled in {instance.classroom.title}.',
        )


@receiver(post_save, sender=Payment)
def payment_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            kind=Notification.Kind.PAYMENT,
            title='Payment received',
            message=f'{instance.amount} received from {instance.invoice.student.full_name} (receipt {instance.receipt_no}).',
        )


@receiver(post_save, sender=Exam)
def exam_notification(sender, instance, created, **kwargs):
    if created:
        Notification.objects.create(
            kind=Notification.Kind.EXAM,
            title='New exam scheduled',
            message=f'{instance.title} is scheduled for {instance.date:%Y-%m-%d} in {instance.classroom.title}.',
        )


@receiver(post_save, sender=Attendance)
def absence_notification(sender, instance, created, **kwargs):
    if created and not instance.present:
        Notification.objects.create(
            kind=Notification.Kind.ATTENDANCE,
            title='Student marked absent',
            message=f'{instance.enrollment.student.full_name} was marked absent on {instance.date:%Y-%m-%d}.',
        )
