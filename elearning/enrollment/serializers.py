from rest_framework import serializers
from core.models import Enrollment, Course

class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for Enrollment model"""
    course_title = serializers.CharField(source='course.title', read_only=True)
    student_name = serializers.CharField(source='student.username', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'course', 'course_title', 'date_enrolled', 'progress', 'completed']
        read_only_fields = ['date_enrolled']
