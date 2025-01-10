from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from core.models import Lesson, Question, Quiz
from .serializers import QuestionSerializer, QuizSerializer

class BasePermissionMixin:
    """Mixin to handle permission checks for instructors."""

    def check_instructor_permission(self, obj):
        """Check if the current user is the instructor of the lesson associated with the object."""
        lesson = obj.lesson if isinstance(obj, Quiz) else obj.quiz.lesson
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied(f"You do not have permission to update this {obj.__class__.__name__.lower()}.")

class QuizViewSet(BasePermissionMixin, viewsets.ModelViewSet):
    """Manage quizzes in the database."""
    serializer_class = QuizSerializer
    queryset = Quiz.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve quizzes for the specific lesson."""
        lesson_id = self.kwargs.get('lesson_pk')
        return self.queryset.filter(lesson_id=lesson_id)

    def perform_create(self, serializer):
        """Create a new quiz."""
        lesson_id = self.kwargs.get('lesson_pk')
        lesson = get_object_or_404(Lesson, id=lesson_id)

        # Check if the user is the instructor of the lesson
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to create a quiz for this lesson.")

        serializer.save(lesson_id=lesson_id)

    def update(self, request, *args, **kwargs):
        """Override update method to check if the user is the instructor."""
        quiz = self.get_object()
        self.check_instructor_permission(quiz)
        return super().update(request, *args, **kwargs)

class QuestionViewSet(BasePermissionMixin, viewsets.ModelViewSet):
    """Manage questions in the database."""
    serializer_class = QuestionSerializer
    queryset = Question.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Retrieve questions for the specific quiz."""
        quiz_id = self.kwargs.get('quiz_pk')
        return self.queryset.filter(quiz_id=quiz_id)

    def perform_create(self, serializer):
        """Create a new question."""
        quiz_id = self.kwargs.get('quiz_pk')
        quiz = get_object_or_404(Quiz, id=quiz_id)

        # Check if the user is the instructor of the quiz's lesson
        self.check_instructor_permission(quiz)
        serializer.save(quiz_id=quiz_id)

    def update(self, request, *args, **kwargs):
        """Override update method to check if the user is the instructor."""
        question = self.get_object()
        self.check_instructor_permission(question)
        return super().update(request, *args, **kwargs)
