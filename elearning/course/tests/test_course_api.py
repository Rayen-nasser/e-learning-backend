from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course
from course.serializers import CourseSerializer

COURSE_URL = reverse('course:course-list')
CREATE_COURSE_URL = reverse('course:course-create')

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)

def create_course(instructor, **kwargs):
    """Helper function to create a new course."""
    defaults = {
        'title': 'Python Course',
        'description': 'This is a python course',
        'category': 'Programming',
        'price': 20.00
    }
    defaults.update(kwargs)

    return Course.objects.create(instructor=instructor, **defaults)

class PublicCourseApiTests(TestCase):
    """Test unauthenticated API requests."""
    def setUp(self):
        self.client = APIClient()
        self.instructor = create_user(
            username='instructor_user',
            first_name='Instructor',
            last_name='User',
            email='instructor@example.com',
            password='password123',
            role='Instructor'
        )
        create_course(self.instructor, title='Public Course 1')
        create_course(self.instructor, title='Public Course 2')

    def test_retrieve_courses(self):
        """Test retrieving courses without authentication."""
        response = self.client.get(COURSE_URL)
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_auth_required_for_create(self):
        """Test that authentication is required to create a course."""
        course_data = {
            'title': 'Unauthorized Course',
            'description': 'This should not be created.',
            'category': 'Test',
            'price': 10.00,
        }
        response = self.client.post(CREATE_COURSE_URL, course_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateCourseApiTests(TestCase):
    """Test authenticated API requests for courses."""
    def setUp(self):
        self.user = create_user(
            username='johnDevelopment',
            first_name='John',
            last_name='Doe',
            email='john@example.com',
            password='testpassword',
            role='Instructor'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_courses(self):
        """Test retrieving a list of courses for the authenticated user."""
        create_course(self.user)
        create_course(self.user, title='Another Course')

        response = self.client.get(COURSE_URL)
        courses = Course.objects.filter(instructor=self.user)
        serializer = CourseSerializer(courses, many=True)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_course(self):
        """Test creating a course."""
        course_data = {
            'title': 'New Python Course',
            'description': 'A brand-new Python course.',
            'category': 'Programming',
            'price': 50.00,
        }
        response = self.client.post(CREATE_COURSE_URL, course_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 1)
        created_course = Course.objects.first()
        self.assertEqual(created_course.title, course_data['title'])
        self.assertEqual(created_course.instructor, self.user)

    def test_different_role_cannot_create_course(self):
        """Test that users with a role other than 'Instructor' cannot create courses."""
        self.user.role = 'Student'
        self.user.save()

        course_data = {
            'title': 'Unauthorized Course',
            'description': 'This course should not be created.',
            'category': 'Unauthorized',
            'price': 30.00,
        }
        response = self.client.post(CREATE_COURSE_URL, course_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Course.objects.count(), 0)

    def test_course_creation_with_invalid_data(self):
        """Test creating a course with invalid data."""
        invalid_data = {
            'title': '',  # Missing title
            'description': 'No title provided.',
            'category': 'Invalid',
            'price': -10.00,  # Negative price
        }
        response = self.client.post(CREATE_COURSE_URL, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)
