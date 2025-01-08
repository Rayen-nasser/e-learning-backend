from rest_framework import viewsets, permissions, serializers, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Lesson, LessonFile
from .serializers import LessonSerializer, LessonFileSerializer

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LessonSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['course']
    search_fields = ['title', 'description']

    def perform_create(self, serializer):
        course = serializer.validated_data['course']
        if course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to create a lesson for this course.")
        serializer.save()

    def perform_update(self, serializer):
        # For PATCH requests, get course from instance if not in validated_data
        course = serializer.validated_data.get('course', serializer.instance.course)
        if course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to edit this lesson.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to delete this lesson.")
        instance.delete()

    def get_queryset(self):
        """
        Optionally restricts the returned lessons to a given course,
        by filtering against a `course` query parameter in the URL.
        """
        queryset = super().get_queryset()
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(course=course)
        # Ensure consistent ordering of lessons (you can order by 'id' or another field)
        return queryset.order_by('id')  # Order by 'id' to ensure consistent result ordering


class LessonFileViewSet(viewsets.ModelViewSet):
    queryset = LessonFile.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LessonFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """
        Restrict the queryset to only the lesson files of lessons owned by the authenticated user.
        """
        user = self.request.user
        return LessonFile.objects.filter(lesson__course__instructor=user)

    def perform_create(self, serializer):
        """
        Check if the user owns the lesson's course before allowing file creation.
        """
        lesson = serializer.validated_data.get('lesson')

        if not lesson:
            raise serializers.ValidationError("Lesson is required.")

        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to upload files for this lesson.")

        serializer.save()

    def perform_update(self, serializer):
        """
        Check if the user owns the lesson's course before allowing file updates.
        """
        lesson = serializer.validated_data.get('lesson', serializer.instance.lesson)

        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify files for this lesson.")

        serializer.save() 

    def perform_destroy(self, instance):
        """
        Check if the user owns the lesson's course before allowing file deletion.
        """
        if instance.lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to delete files for this lesson.")
        instance.delete()
