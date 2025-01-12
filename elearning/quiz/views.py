from rest_framework.exceptions import PermissionDenied
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from core.models import Lesson, Question, Quiz, Submission
from .serializers import QuestionSerializer, QuizSerializer, SubmissionSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets, mixins, permissions
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

class BasePermissionMixin:
    """Mixin to handle permission checks for instructors."""

    def check_instructor_permission(self, obj):
        """Check if the current user is the instructor of the lesson associated with the object."""
        lesson = obj.lesson if isinstance(obj, Quiz) else obj.quiz.lesson
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied(f"You do not have permission to update this {obj.__class__.__name__.lower()}.")


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of quizzes for the specified lesson.",
        summary="List Quizzes",
        tags=["Quiz"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific quiz.",
        summary="Retrieve Quiz",
        tags=["Quiz"],
    ),
    create=extend_schema(
        description="Create a new quiz for the specified lesson.",
        summary="Create Quiz",
        request=QuizSerializer,
        tags=["Quiz"],
    ),
    update=extend_schema(
        description="Update details of an existing quiz.",
        summary="Update Quiz",
        request=QuizSerializer,
        tags=["Quiz"],
    ),
    partial_update=extend_schema(
        description="Partially update details of an existing quiz.",
        summary="Partial Update Quiz",
        request=QuizSerializer,
        tags=["Quiz"],
    ),
    destroy=extend_schema(
        description="Delete a specific quiz.",
        summary="Delete Quiz",
        tags=["Quiz"],
    ),
)
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

        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to create a quiz for this lesson.")

        serializer.save(lesson_id=lesson_id)

    def update(self, request, *args, **kwargs):
        """Override update method to check if the user is the instructor."""
        quiz = self.get_object()
        self.check_instructor_permission(quiz)
        return super().update(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of questions for the specified quiz.",
        summary="List Questions",
        tags=["Questions"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific question.",
        summary="Retrieve Question",
        tags=["Questions"],
    ),
    create=extend_schema(
        description="Create a new question for the specified quiz.",
        summary="Create Question",
        request=QuestionSerializer,
        tags=["Questions"],
    ),
    update=extend_schema(
        description="Update details of an existing question.",
        summary="Update Question",
        request=QuestionSerializer,
        tags=["Questions"],
    ),
    partial_update=extend_schema(
        description="Partially update details of an existing question.",
        summary="Partial Update Question",
        request=QuestionSerializer,
        tags=["Questions"],
    ),
    destroy=extend_schema(
        description="Delete a specific question.",
        summary="Delete Question",
        tags=["Questions"],
    ),
)
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

        self.check_instructor_permission(quiz)
        serializer.save(quiz_id=quiz_id)

    def update(self, request, *args, **kwargs):
        """Override update method to check if the user is the instructor."""
        question = self.get_object()
        self.check_instructor_permission(question)
        return super().update(request, *args, **kwargs)


class IsStudentUser(permissions.BasePermission):
    """
    Custom permission to only allow students to submit quizzes.
    """
    def has_permission(self, request, view):
        return request.user.role == 'Student'

class SubmissionViewSet(mixins.CreateModelMixin,
                       mixins.ListModelMixin,
                       mixins.RetrieveModelMixin,
                       viewsets.GenericViewSet):
    """
    ViewSet for handling quiz submissions.
    Allows create, list, and retrieve operations only.
    """
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudentUser]

    def get_queryset(self):
        quiz_pk = self.kwargs.get('quiz_pk')
        if self.request.user.role == 'Student':
            return Submission.objects.filter(
                quiz_id=quiz_pk,
                student=self.request.user
            )
        return Submission.objects.filter(quiz_id=quiz_pk)

    def validate_answers_and_calculate_score(self, quiz, answers):
        """
        Validate answers and calculate the score for the quiz submission.
        Returns a tuple of (score, error_message).
        """
        if not answers or not isinstance(answers, list):
            return 0, "Answers must be provided as a list"

        # Get all questions for the quiz
        quiz_questions = {q.id: q for q in quiz.questions.all()}

        # Validate that all questions are answered
        answered_question_ids = {answer.get('question') for answer in answers}
        if answered_question_ids != set(quiz_questions.keys()):
            return 0, "All questions must be answered"

        # Validate each answer and calculate score
        total_score = 0
        seen_questions = set()

        for answer in answers:
            question_id = answer.get('question')
            selected_option = answer.get('selected_option')

            # Check for duplicate answers
            if question_id in seen_questions:
                return 0, f"Duplicate answers found for question: {question_id}"
            seen_questions.add(question_id)

            # Validate question exists and belongs to quiz
            question = quiz_questions.get(question_id)
            if not question:
                return 0, f"Invalid question ID: {question_id}"

            # Validate selected option
            if not isinstance(selected_option, int) or str(selected_option) not in question.options:
                return 0, f"Invalid option selected for question {question_id}"

            # Calculate score for correct answers
            if selected_option == question.correct_option:
                total_score += question.points

        return total_score, None

    def create(self, request, *args, **kwargs):
        """
        Create a new submission with validated answers and calculated score.
        """
        quiz = get_object_or_404(Quiz, pk=self.kwargs.get('quiz_pk'))

        # Check if quiz is active
        if not quiz.is_active:
            return Response(
                {"error": "This quiz is no longer active"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if student has already submitted
        if Submission.objects.filter(quiz=quiz, student=request.user).exists():
            return Response(
                {"error": "You have already submitted this quiz"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate answers and calculate score
        answers = request.data.get('answers', [])
        score, error_message = self.validate_answers_and_calculate_score(quiz, answers)

        if error_message:
            return Response(
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create submission with calculated score
        data = {
            'answers': answers,
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer, quiz=quiz, score=score)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer, quiz, score):
        serializer.save(
            student=self.request.user,
            quiz=quiz,
            score=score
        )