from rest_framework import serializers
from datetime import timedelta
from django.utils import timezone
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    expires_at = serializers.SerializerMethodField()

    class Meta:
        model = Attendance
        fields = [
            'id',
            'student_id',
            'student_name',
            'teacher_name',
            'date',
            'time',
            'taken_at',
            'expires_at',
        ]

    def get_teacher_name(self, obj):
        if not obj.teacher:
            return 'Unknown teacher'
        return obj.teacher.get_full_name() or obj.teacher.get_username()

    def get_expires_at(self, obj):
        return timezone.localtime(obj.taken_at + timedelta(hours=24)).isoformat()
