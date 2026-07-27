from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='students/')
    embedding = models.JSONField(null=True, blank=True)  # stores the face embedding as a list of numbers
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_id} - {self.name}"