# Generated manually for the professional MIS feature set.
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('academics', '0006_class_dates_and_invoice_classes'),
    ]

    operations = [
        migrations.AddField(model_name='student', name='email', field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name='student', name='guardian_name', field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name='student', name='photo', field=models.FileField(blank=True, upload_to='student_photos/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])),
        migrations.AddField(model_name='teacher', name='address', field=models.TextField(blank=True)),
        migrations.AddField(model_name='teacher', name='email', field=models.EmailField(blank=True, max_length=254)),
        migrations.AddField(model_name='teacher', name='photo', field=models.FileField(blank=True, upload_to='teacher_photos/', validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])])),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=150)),
                ('category', models.CharField(choices=[('rent', 'Rent'), ('salary', 'Salary'), ('utilities', 'Utilities'), ('supplies', 'Supplies'), ('other', 'Other')], default='other', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('spent_at', models.DateField()),
                ('note', models.CharField(blank=True, max_length=250)),
                ('receipt_no', models.CharField(max_length=30, unique=True)),
            ],
            options={'ordering': ['-spent_at', '-pk']},
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('enrollment', 'Enrollment'), ('payment', 'Payment'), ('attendance', 'Attendance'), ('exam', 'Exam'), ('system', 'System')], default='system', max_length=20)),
                ('title', models.CharField(max_length=160)),
                ('message', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('recipient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='mis_notifications', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='TeacherSalaryPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0.01)])),
                ('paid_at', models.DateField()),
                ('receipt_no', models.CharField(max_length=30, unique=True)),
                ('note', models.CharField(blank=True, max_length=250)),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='salary_payments', to='academics.teacher')),
            ],
            options={'ordering': ['-paid_at', '-pk']},
        ),
    ]
