from calendar import monthrange
from datetime import timedelta

from django.db import migrations, models


def add_months(value, months):
    target_month = value.month - 1 + months
    year = value.year + target_month // 12
    month = target_month % 12 + 1
    return value.replace(year=year, month=month, day=min(value.day, monthrange(year, month)[1]))


def populate_existing_data(apps, schema_editor):
    ClassRoom = apps.get_model('academics', 'ClassRoom')
    Enrollment = apps.get_model('academics', 'Enrollment')
    Invoice = apps.get_model('academics', 'Invoice')
    for classroom in ClassRoom.objects.select_related('course').filter(end_date__isnull=True):
        classroom.end_date = add_months(classroom.start_date, classroom.course.duration_months) - timedelta(days=1)
        classroom.save(update_fields=['end_date'])
    for invoice in Invoice.objects.filter(classroom__isnull=True):
        enrollment = Enrollment.objects.filter(student_id=invoice.student_id, is_active=True).order_by('pk').first()
        if enrollment is None:
            enrollment = Enrollment.objects.filter(student_id=invoice.student_id).order_by('pk').first()
        if enrollment:
            invoice.classroom_id = enrollment.classroom_id
            invoice.save(update_fields=['classroom'])


class Migration(migrations.Migration):
    dependencies = [('academics', '0005_invoice_classroom')]
    operations = [
        migrations.AddField(
            model_name='classroom', name='attendance_weekdays',
            field=models.CharField(default='5,6,0,1,2', help_text='Teaching days: 0=Mon, 1=Tue, …, 5=Sat, 6=Sun. Example Saturday–Wednesday: 5,6,0,1,2.', max_length=20),
        ),
        migrations.RunPython(populate_existing_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='invoice', name='classroom',
            field=models.ForeignKey(on_delete=models.PROTECT, related_name='invoices', to='academics.classroom'),
        ),
    ]
