from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied, Throttled
from core.models import Course
from .serializers import CourseSerializer
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
import re
import bleach
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample


def sanitize_course_description(description):
    """
    Sanitize course description to allow only safe HTML tags.
    """
    allowed_tags = ['b', 'i', 'u', 'a', 'p', 'br']
    return bleach.clean(description, tags=allowed_tags, strip=True)

def validate_sql_injection(value):
    """
    Validate the value for SQL injection attempts.
    """
    sql_patterns = r".*[;'].*|.*--.*|.*drop.*|.*select.*|.*union.*"
    if re.match(sql_patterns, value.lower()):
        raise serializers.ValidationError("Invalid characters in value")
    return value


@extend_schema_view(
    list=extend_schema(
        description="Retrieve a list of all available courses.",
        parameters=[
            OpenApiParameter(name='search', type=str, description="Search for courses by title."),
        ],
        responses={200: CourseSerializer(many=True)},
        examples=[
            OpenApiExample(
                "Sample Course List",
                value=[
                    {
                        "id": 1,
                        "title": "Python for Beginners",
                        "description": "A comprehensive course for Python programming.",
                        "instructor": "John Doe"
                    },
                    {
                        "id": 2,
                        "title": "Advanced Django",
                        "description": "Master Django with real-world projects.",
                        "instructor": "Jane Smith"
                    }
                ],
            )
        ],
        tags=["Course"],  # Tags applied here
    ),
    retrieve=extend_schema(
        description="Retrieve detailed information about a specific course.",
        responses={200: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    create=extend_schema(
        description="Create a new course. Only instructors are allowed to create courses.",
        request=CourseSerializer,
        responses={201: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    update=extend_schema(
        description="Update an existing course. Only the instructor who created the course can update it.",
        request=CourseSerializer,
        responses={200: CourseSerializer},
        tags=["Course"],  # Tags applied here
    ),
    partial_update=extend_schema(
        description="Partially update an existing course. Only the instructor who created the course can update it.",
        request=CourseSerializer,
        responses={200: CourseSerializer},
        tags=["Course"],
    ),
    destroy=extend_schema(
        description="Delete a course. Only the instructor who created the course can delete it.",
        responses={204: None},
        tags=["Course"],  # Tags applied here
    ),
)
@method_decorator(ratelimit(key='ip', rate='5/m', method='ALL'), name='dispatch')
class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, creating, updating, and deleting courses.
    """
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def handle_no_permission(self):
        if getattr(self, 'ratelimit_reached', False):
            raise Throttled()
        return super().handle_no_permission()

    def get_permissions(self):
        """
        Return appropriate permissions based on the action.
        """
        if self.action == 'list':
            return [AllowAny()]  # Allow everyone to list courses
        if self.action in ['create', 'update', 'destroy']:
            return [IsAuthenticated()]  # Require authentication for other actions
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Perform the save operation for creating a course.
        Only instructors can create courses.
        """
        user = self.request.user
        if getattr(user, 'role', None) != 'Instructor':
            raise PermissionDenied("Only instructors can create courses.")

        # Validate the instructor and title for SQL injection
        instructor = self.request.data.get('instructor', '')
        title = self.request.data.get('title', '')

        validate_sql_injection(instructor)  # Validate instructor field
        validate_sql_injection(title)       # Validate title field

        # Sanitize course description before saving
        description = self.request.data.get('description', '')
        sanitized_description = sanitize_course_description(description)

        # Save the course with the sanitized description and instructor
        serializer.save(description=sanitized_description, instructor=user)
