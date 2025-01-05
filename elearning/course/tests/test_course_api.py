from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from models.core.models import (
    User,
    Course
)
from .serializers import (
    CourseSerializer
)

COURSE_URL = reverse('course:create')

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)

def create_course(user, **kwargs):
    """Helper function to create a new course."""
    defaults = {
        'title':'Python Course',
        'description':'This is a python course',
        'category':'Programming',
        'price':20.00
    }
    defaults.update(kwargs)

    course = Course.objects.create(
        user=user, **defaults
    )
    return course

class PublicCourse(TestCase):
    """Test unauthenticated API requests."""
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test that authentication is required."""
        res = self.client.post(COURSE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateCourseApiTests(TestCase):
    """Test the private course API."""
    def setUp(self):
        self.user = User.objects.create_user(
            username='johnDevelopment',
            first_name='john',
            last_name='john',
            email='john@example.com',
            password='testpassword',
            role='Instructor'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_courses(self):
        """Test retrieving a list of courses."""
        create_course(self.user)
        create_course(self.user, title='Course Title 2')

        res = self.client.get(COURSE_URL)
        courses = Course.objects.all().filter(user=self.user)
        serializer = CourseSerializer(courses, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_course(self):
        course = {
            'title':'Python Course',
            'description':'This is a python course',
            'instructor':self.user,
            'category':'Programming',
            'price':20.00
        }
        response = self.client.post(COURSE_URL, course)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_different_role_cannot_create_course(self):
        """Test that a user with a different role cannot create a course"""
        self.user = {
            **self.user,
            'role':'Student'
        }
        course = {
            'title':'Python Course',
            'description':'This is a python course',
            'instructor':self.user,
            'category':'Programming',
            'price':20.00
        }
        response = self.client.post(COURSE_URL, course)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN
        )
