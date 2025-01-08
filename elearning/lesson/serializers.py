from rest_framework import serializers
from core.models import Lesson, LessonFile

class LessonFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonFile
        fields = ['lesson', 'file']

    def validate(self, data):
        if not data.get('lesson'):
            raise serializers.ValidationError("Lesson is required")
        if not data.get('file'):
            raise serializers.ValidationError("File is required")
        return data

class LessonSerializer(serializers.ModelSerializer):
    files = LessonFileSerializer(many=True, read_only=True)  # To include lesson files in the lesson data

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'course', 'files']
