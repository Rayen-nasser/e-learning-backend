from rest_framework import viewsets, permissions, serializers, filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from core.models import Course, Lesson, LessonFile
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample, OpenApiTypes
from .serializers import LessonSerializer, LessonFileSerializer
from rest_framework.permissions import IsAuthenticated


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of lessons for a course. Optionally filter by course ID or search by title/description.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to retrieve lessons for."
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Search lessons by title or description."
            ),
        ],
        responses={200: LessonSerializer(many=True)},
        tags=["Lesson"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific lesson.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the lesson belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the lesson to retrieve."
            ),
        ],
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    create=extend_schema(
        description="Create a new lesson for a course. Only the course instructor can perform this action.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the new lesson will be added."
            ),
        ],
        request=LessonSerializer,
        responses={201: LessonSerializer},
        tags=["Lesson"],
    ),
    update=extend_schema(
        description="Update an existing lesson. Only the course instructor can perform this action.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the lesson belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the lesson to update."
            ),
        ],
        request=LessonSerializer,
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    partial_update=extend_schema(
        description="Partially update a lesson. Only the course instructor can perform this action.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the lesson belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the lesson to partially update."
            ),
        ],
        request=LessonSerializer,
        responses={200: LessonSerializer},
        tags=["Lesson"],
    ),
    destroy=extend_schema(
        description="Delete a lesson. Only the course instructor can perform this action.",
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the lesson belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the lesson to delete."
            ),
        ],
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

    def get_queryset(self):
        course_pk = self.kwargs.get('course_pk')
        if not course_pk:
            return Lesson.objects.none()
        return self.queryset.filter(course_id=course_pk)


    def perform_create(self, serializer):
        course_id = self.kwargs.get('course_pk')
        course = Course.objects.get(id=course_id)
        if course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to create a lesson for this course.")
        serializer.save()

    def perform_update(self, serializer):
        lesson = self.get_object()
        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to edit this lesson.")
        serializer.save()


    def perform_destroy(self, instance):
        if instance.course.instructor != self.request.user:
            raise PermissionDenied("You do not have permission to delete this lesson.")
        instance.delete()


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of lesson files. Only files for lessons owned by the authenticated user will be shown.",
        parameters=[
            OpenApiParameter(name='course_pk', type=int, location='path', description="The ID of the course to which the lesson belongs."),
            OpenApiParameter(name='lesson_pk', type=int, location='path', description="The ID of the lesson the file belongs to."),
        ],
        responses={200: LessonFileSerializer(many=True)},
        tags=["LessonFile"],
    ),
    retrieve=extend_schema(
        description="Retrieve details of a specific lesson file.",
        parameters=[
            OpenApiParameter(name='course_pk', type=int, location='path', description="The ID of the course to which the lesson belongs."),
            OpenApiParameter(name='lesson_pk', type=int, location='path', description="The ID of the lesson the file belongs to."),
        ],
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
    permission_classes = [IsAuthenticated]
    serializer_class = LessonFileSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        user = self.request.user
        lesson_pk = self.kwargs.get('lesson_pk')
        if lesson_pk:
            return LessonFile.objects.filter(lesson__id=lesson_pk, lesson__course__instructor=user)
        return LessonFile.objects.none()

    def perform_create(self, serializer):
        lesson_pk = self.kwargs.get('lesson_pk')
        try:
            lesson = Lesson.objects.get(id=lesson_pk)
        except Lesson.DoesNotExist:
            raise serializers.ValidationError("Lesson does not exist.")

        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to upload files for this lesson.")

        # Log for debugging purposes
        print(f"User: {self.request.user}, Lesson: {lesson}, Course: {lesson.course}")

        serializer.save(lesson=lesson)


    def perform_update(self, serializer):
        lesson_pk = self.kwargs.get('lesson_pk')
        try:
            lesson = Lesson.objects.get(id=lesson_pk)
        except Lesson.DoesNotExist:
            raise serializers.ValidationError("Lesson does not exist.")

        if lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to modify files for this lesson.")

        serializer.save(lesson=lesson)

    def perform_destroy(self, instance):
        if instance.lesson.course.instructor != self.request.user:
            raise PermissionDenied("You are not authorized to delete files for this lesson.")
        instance.delete()
