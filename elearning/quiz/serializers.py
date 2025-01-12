from rest_framework import serializers
from core.models import Quiz, Question, Submission


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'options', 'correct_option', 'points', 'question_type']

    def validate_options(self, value):
        """Ensure that options are a dictionary."""
        if not isinstance(value, dict):
            raise serializers.ValidationError('Options must be a dictionary.')
        return value

class QuizSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'title', 'lesson', 'description', 'is_active', 'time_limit', 'created_at', 'updated_at', 'questions']
        read_only_fields = ['id', 'created_at', 'updated_at']


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['id', 'quiz', 'student', 'score', 'submission_date']

    def validate(self, data):
        # Check if the student has already submitted this quiz
        if Submission.objects.filter(quiz=data['quiz'], student=data['student']).exists():
            raise serializers.ValidationError("You have already submitted this quiz.")
        return data