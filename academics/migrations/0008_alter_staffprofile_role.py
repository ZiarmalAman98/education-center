from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('academics', '0007_professional_mis_features')]

    operations = [
        migrations.AlterField(
            model_name='staffprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super admin'), ('manager', 'Manager'),
                    ('accountant', 'Accountant'), ('reception', 'Reception'),
                    ('teacher', 'Teacher'), ('student', 'Student'),
                ],
                default='reception', max_length=20,
            ),
        ),
    ]
