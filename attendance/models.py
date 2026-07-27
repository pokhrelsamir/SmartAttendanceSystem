from django.db import models
from django.conf import settings
from django.utils import timezone
from students.models import Student

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records'
    )
    taken_at = models.DateTimeField(default=timezone.now, editable=False)
    date = models.DateField(editable=False)
    time = models.TimeField(editable=False)

    class Meta:
        indexes = [
            models.Index(fields=['teacher', 'student', 'taken_at'], name='attendance_teacher_20fd02_idx'),
            models.Index(fields=['teacher', 'taken_at'], name='attendance_teacher_af6643_idx'),
        ]

    def save(self, *args, **kwargs):
        local_taken_at = timezone.localtime(self.taken_at)
        self.date = local_taken_at.date()
        self.time = local_taken_at.time()
        super().save(*args, **kwargs)

    def __str__(self):
        teacher_name = self.teacher.get_username() if self.teacher else 'Unknown teacher'
        return f"{self.student.name} - {teacher_name} - {self.date}"
