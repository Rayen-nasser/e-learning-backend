from rest_framework import serializers
from core.models import Course

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'category', 'price', 'instructor', 'created_at', 'updated_at']
        read_only_fields = ['instructor', 'created_at', 'updated_at']
