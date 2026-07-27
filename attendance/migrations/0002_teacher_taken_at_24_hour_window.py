import datetime

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def populate_taken_at(apps, schema_editor):
    Attendance = apps.get_model('attendance', 'Attendance')
    current_timezone = timezone.get_current_timezone()

    for record in Attendance.objects.filter(taken_at__isnull=True):
        combined = datetime.datetime.combine(record.date, record.time)
        if timezone.is_naive(combined):
            combined = timezone.make_aware(combined, current_timezone)

        record.taken_at = combined
        record.save(update_fields=['taken_at'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('attendance', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='attendance',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='attendance',
            name='teacher',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='attendance_records',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='attendance',
            name='taken_at',
            field=models.DateTimeField(blank=True, editable=False, null=True),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='date',
            field=models.DateField(editable=False),
        ),
        migrations.AlterField(
            model_name='attendance',
            name='time',
            field=models.TimeField(editable=False),
        ),
        migrations.RunPython(populate_taken_at, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='attendance',
            name='taken_at',
            field=models.DateTimeField(default=timezone.now, editable=False),
        ),
        migrations.AddIndex(
            model_name='attendance',
            index=models.Index(fields=['teacher', 'student', 'taken_at'], name='attendance_teacher_20fd02_idx'),
        ),
        migrations.AddIndex(
            model_name='attendance',
            index=models.Index(fields=['teacher', 'taken_at'], name='attendance_teacher_af6643_idx'),
        ),
    ]
