from rest_framework import viewsets, permissions, serializers, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Lesson, LessonFile
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from .serializers import LessonSerializer, LessonFileSerializer


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of lessons for a course. Optionally filter by course ID or search by title/description.",
        parameters=[
            OpenApiParameter(name='course', type=int, description="Filter lessons by course ID."),
            OpenApiParameter(name='search', type=str, description="Search lessons by title or description."),
        ],
        responses={200: LessonSerializer(many=True)},
        tags=["Lesson"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific lesson.",
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    create=extend_schema(
        description="Create a new lesson for a course. Only the course instructor can perform this action.",
        request=LessonSerializer,
        responses={201: LessonSerializer},
        tags=["Lesson"],
    ),
    update=extend_schema(
        description="Update an existing lesson. Only the course instructor can perform this action.",
        request=LessonSerializer,
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    partial_update=extend_schema(
        description="Partially update a lesson. Only the course instructor can perform this action.",
        request=LessonSerializer,
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    destroy=extend_schema(
        description="Delete a lesson. Only the course instructor can perform this action.",
        responses={204: None},
        tags=["Lesson"],
    ),
)
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
        course = serializer.validated_data.get('course', serializer.instance.course)
        if course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to edit this lesson.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to delete this lesson.")
        instance.delete()


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of lesson files. Only files for lessons owned by the authenticated user will be shown.",
        responses={200: LessonFileSerializer(many=True)},
        tags=["LessonFile"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific lesson file.",
        responses={200: LessonFileSerializer},
        tags=["LessonFile"],
    ),
    create=extend_schema(
        description="Upload a new file to a lesson. Only the lesson owner can perform this action.",
        request=LessonFileSerializer,
        responses={201: LessonFileSerializer},
        tags=["LessonFile"],
    ),
    update=extend_schema(
        description="Update an existing lesson file. Only the lesson owner can perform this action.",
        request=LessonFileSerializer,
        responses={200: LessonFileSerializer},
        tags=["LessonFile"],
    ),
    partial_update=extend_schema(
        description="Partially update a lesson file. Only the lesson owner can perform this action.",
        request=LessonFileSerializer,
        responses={200: LessonFileSerializer},
        tags=["LessonFile"],
    ),
    destroy=extend_schema(
        description="Delete a lesson file. Only the lesson owner can perform this action.",
        responses={204: None},
        tags=["LessonFile"],
    ),
)
class LessonFileViewSet(viewsets.ModelViewSet):
    queryset = LessonFile.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LessonFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        return LessonFile.objects.filter(lesson__course__instructor=user)

    def perform_create(self, serializer):
        lesson = serializer.validated_data.get('lesson')
        if not lesson:
            raise serializers.ValidationError("Lesson is required.")
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to upload files for this lesson.")
        serializer.save()

    def perform_update(self, serializer):
        lesson = serializer.validated_data.get('lesson', serializer.instance.lesson)
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify files for this lesson.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to delete files for this lesson.")
        instance.delete()
