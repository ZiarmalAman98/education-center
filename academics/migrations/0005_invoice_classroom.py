# Generated manually for class-level invoice reporting.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('academics', '0004_staffprofile_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='classroom',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='invoices',
                to='academics.classroom',
            ),
        ),
    ]
