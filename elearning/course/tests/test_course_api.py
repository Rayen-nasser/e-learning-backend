from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course
from course.serializers import CourseSerializer

from django.middleware.csrf import get_token

COURSE_URL = reverse('course:course-list')

def detail_url(course_id):
    """Return course detail URL."""
    return reverse('course:course-detail', args=[course_id])

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)

def create_course(user, **params):
    """Helper function to create a course."""
    defaults = {
        'title': 'Python Course',
        'description': 'A comprehensive Python course.',
        'category': 'Programming',
        'price': 50.00,
        'instructor': user
    }
    defaults.update(params)
    return Course.objects.create(**defaults)

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

    def test_unauthorized_user_cannot_create_course(self):
        """Test that unauthenticated users cannot create a course."""
        self.client.logout()  # Ensure the user is logged out
        course_data = {
            'title': 'Unauthorized Course',
            'description': 'Unauthorized course creation attempt.',
            'category': 'Test',
            'price': 10.00,
        }
        response = self.client.post(COURSE_URL, course_data)
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
        self.client.defaults['HTTP_X_CSRFTOKEN'] = 'dummy_csrf_token'
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

    def test_get_course_by_id(self):
        """Test retrieving a course by ID."""
        course = create_course(self.user)
        url = detail_url(course.id)
        response = self.client.get(url)
        serializer = CourseSerializer(course)
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
        response = self.client.post(COURSE_URL, course_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 1)
        created_course = Course.objects.first()
        self.assertEqual(created_course.title, course_data['title'])
        self.assertEqual(created_course.instructor, self.user)

    def test_instructor_can_create_course(self):
        """Test that an instructor can create a course."""
        self.user.role = 'Instructor'
        self.user.save()
        course_data = {
            'title': 'Instructor Course',
            'description': 'Description for instructor course.',
            'category': 'Programming',
            'price': 100.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_instructor_cannot_create_course(self):
        """Test that a non-instructor cannot create a course."""
        self.user.role = 'Student'
        self.user.save()
        course_data = {
            'title': 'Student Course',
            'description': 'Description for student course.',
            'category': 'Programming',
            'price': 100.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_creation_with_invalid_data(self):
        """Test creating a course with invalid data."""
        invalid_data = {
            'title': '',  # Missing title
            'description': 'No title provided.',
            'category': 'Invalid',
            'price': -10.00,  # Negative price
        }
        response = self.client.post(COURSE_URL, invalid_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)

    def test_edit_title_course(self):
        """Test updating a course."""
        course = create_course(self.user)
        updated_data = {
            'title': 'Updated Python Course',
        }
        url = detail_url(course.id)
        response = self.client.patch(url, updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_course = Course.objects.get(id=course.id)
        self.assertEqual(updated_course.title, updated_data['title'])

    def test_update_course(self):
        """Test updating a course."""
        course = create_course(self.user)
        updated_data = {
            'title': 'Updated Python Course',
            'description': 'An updated Python course.',
            'category': 'Updated Programming',
            'price': 70.00,
        }
        url = detail_url(course.id)
        response = self.client.put(url, updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_course = Course.objects.get(id=course.id)
        self.assertEqual(updated_course.title, updated_data['title'])
        self.assertEqual(updated_course.description, updated_data['description'])
        self.assertEqual(updated_course.category, updated_data['category'])
        self.assertEqual(updated_course.price, updated_data['price'])
        self.assertEqual(updated_course.instructor, self.user)

    def test_delete_course(self):
        """Test deleting a course."""
        course = create_course(self.user)
        url = detail_url(course.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Course.objects.count(), 0)

        # Ensure the course is deleted
        with self.assertRaises(Course.DoesNotExist):
            Course.objects.get(id=course.id)

    def test_course_description_sanitization(self):
        """Test that course descriptions do not allow XSS attacks."""
        malicious_description = '<script>alert("XSS")</script>'
        course_data = {
            'title': 'Secure Course',
            'description': malicious_description,
            'category': 'Test',
            'price': 30.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_course = Course.objects.first()
        self.assertNotIn('<script>', created_course.description)

    def test_sql_injection_in_course_creation(self):
        """Test that SQL injection does not affect course creation."""
        malicious_data = {
            'title': 'Test Course',
            'description': 'Test description',
            'category': 'Test',
            'price': 10.00,
            'instructor': '1 OR 1=1 --',  # SQL injection attempt
        }
        response = self.client.post(COURSE_URL, malicious_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)  # Ensure no course is created

    def test_rate_limiting(self):
        """Test that rate limiting prevents brute-force attacks."""
        # Try to hit the endpoint multiple times
        for _ in range(1000):
            response = self.client.post(COURSE_URL, {'title': 'Test', 'description': 'Rate limit test', 'category': 'Test', 'price': 10.00})

        # The response should eventually be rate-limited
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

