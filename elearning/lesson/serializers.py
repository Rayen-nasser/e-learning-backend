from rest_framework import serializers
from core.models import Course, Lesson, LessonFile

class LessonFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonFile
        fields = ['id', 'file', 'uploaded_at']

    def validate(self, data):
        request = self.context['request']
        lesson_pk = request.parser_context['kwargs'].get('lesson_pk')

        if lesson_pk:
            try:
                lesson = Lesson.objects.get(id=lesson_pk)
                data['lesson'] = lesson
            except Lesson.DoesNotExist:
                raise serializers.ValidationError("Lesson does not exist.")
        else:
            raise serializers.ValidationError("Lesson is required.")

        # Check if the user is authorized to upload files for this lesson
        if lesson.course.instructor != self.context['request'].user:
            raise serializers.ValidationError("You are not authorized to upload files for this lesson.")

        # Ensure the file is present
        if not data.get('file'):
            raise serializers.ValidationError("File is required.")

        return data


class LessonListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title']


class LessonSerializer(serializers.ModelSerializer):
    files = LessonFileSerializer(many=True, read_only=True)  # To include lesson files in the lesson data

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'course', 'files']
        extra_kwargs = {
            'course': {'required': False},  # Make course optional in the request
        }

    def validate(self, data):
        request = self.context['request']
        course_pk = request.parser_context['kwargs'].get('course_pk')

        # Ensure the course in URL is valid
        if course_pk:
            try:
                course = Course.objects.get(id=course_pk)
                data['course'] = course
            except Course.DoesNotExist:
                raise serializers.ValidationError("Course does not exist.")
        elif 'course' not in data:
            raise serializers.ValidationError("Course is required if not provided in the URL.")

        return data
