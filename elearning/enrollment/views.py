from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from core.models import Enrollment, Course
from .serializers import EnrollmentSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiTypes


@extend_schema_view(
    list=extend_schema(
        summary="List enrollments for a course",
        description=(
            "Retrieve a list of enrollments for the specified course. "
            "Filters results based on the user's role (Instructor or Student)."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course for which enrollments are listed."
            ),
        ],
        responses={200: EnrollmentSerializer(many=True)},
        tags=["Enrollment"],
    ),
    create=extend_schema(
        summary="Enroll a student in a course",
        description=(
            "Enroll a student in the specified course. Students cannot enroll in their own courses. "
            "This action is restricted to students only."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course in which to enroll the student."
            ),
        ],
        request=EnrollmentSerializer,
        responses={201: EnrollmentSerializer},
        tags=["Enrollment"],
    ),
    update=extend_schema(
        summary="Update enrollment progress or completion status",
        description=(
            "Update the progress or completion status of the specified enrollment. "
            "Only the student can update their own enrollment."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the enrollment belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the enrollment to update."
            ),
        ],
        request=EnrollmentSerializer,
        responses={200: EnrollmentSerializer},
        tags=["Enrollment"],
    ),
    destroy=extend_schema(
        summary="Delete an enrollment",
        description=(
            "Delete the specified enrollment. Only the student can delete their own enrollment."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the enrollment belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the enrollment to delete."
            ),
        ],
        responses={204: None},
        tags=["Enrollment"],
    ),
    retrieve=extend_schema(
        summary="Retrieve an enrollment",
        description=(
            "Retrieve details of an enrollment for the specified course. "
            "Filters results based on the user's role (Instructor or Student)."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the enrollment belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the enrollment to retrieve."
            ),
        ],
        responses={200: EnrollmentSerializer},
        tags=["Enrollment"],
    ),
    partial_update=extend_schema(
        summary="Partially update enrollment progress or completion status",
        description=(
            "Partially update the progress or completion status of the specified enrollment. "
            "Only the student can update their own enrollment."
        ),
        parameters=[
            OpenApiParameter(
                name='course_pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the course to which the enrollment belongs."
            ),
            OpenApiParameter(
                name='pk',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description="Primary key of the enrollment to partially update."
            ),
        ],
        request=EnrollmentSerializer,
        responses={200: EnrollmentSerializer},
        tags=["Enrollment"],
    ),
)
class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing enrollments"""
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]

    def get_course(self):
        """Helper method to get and validate course existence"""
        return get_object_or_404(Course, id=self.kwargs.get('course_pk'))

    def get_queryset(self):
        """Get base queryset filtered by course"""
        course = self.get_course()
        return Enrollment.objects.filter(course=course)

    def check_enrollment_permission(self, enrollment):
        """Check if user has permission to access the enrollment"""
        user = self.request.user
        if user.role == 'Instructor' and enrollment.course.instructor == user:
            return True
        if enrollment.student == user:
            return True
        return False

    def get_object(self):
        """Get enrollment object and check permissions"""
        enrollment = super().get_object()
        if not self.check_enrollment_permission(enrollment):
            self.permission_denied(
                self.request,
                message='You do not have permission to access this enrollment.'
            )
        return enrollment

    def list(self, request, *args, **kwargs):
        """Filter queryset based on user role for list view"""
        queryset = self.get_queryset()
        if request.user.role == 'Instructor':
            queryset = queryset.filter(course__instructor=request.user)
        else:
            queryset = queryset.filter(student=request.user)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """Enroll a student in a course"""
        course = self.get_course()

        if course.instructor == request.user:
            return Response(
                {'error': 'Instructors cannot enroll in their own courses.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'progress': 0.0, 'completed': False}
        )

        message = 'Enrolled successfully!' if created else 'Already enrolled.'
        serializer = self.get_serializer(enrollment)
        return Response(
            {'message': message, 'enrollment': serializer.data},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        """Update progress or completion status"""
        instance = self.get_object()  # This will handle permission check

        if instance.student != request.user:
            return Response(
                {'error': 'You cannot update another student\'s enrollment.'},
                status=status.HTTP_403_FORBIDDEN
            )

        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Delete an enrollment"""
        instance = self.get_object()  # This will handle permission check

        if instance.student != request.user:
            return Response(
                {'error': 'You cannot delete another student\'s enrollment.'},
                status=status.HTTP_403_FORBIDDEN
            )

        instance.delete()
        return Response(
            {'message': 'Enrollment deleted successfully.'},
            status=status.HTTP_204_NO_CONTENT
        )