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


class SubmissionAnswerSerializer(serializers.Serializer):
    question = serializers.IntegerField()
    selected_option = serializers.IntegerField()

class SubmissionSerializer(serializers.ModelSerializer):
    answers = SubmissionAnswerSerializer(many=True)

    class Meta:
        model = Submission
        fields = ['id', 'quiz', 'student', 'score', 'answers', 'submission_date']
        read_only_fields = ['id', 'submission_date', 'score', 'student', 'quiz']

    def validate_answers(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Answers must be provided as a list")
        return value