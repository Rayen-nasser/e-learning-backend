from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Course, Category, Enrollment, Rating
from course.serializers import CourseSerializer
import tempfile
from PIL import Image
import os

COURSE_URL = reverse('course:course-list')

def detail_url(course_id):
    """Return course detail URL."""
    return reverse('course:course-detail', args=[course_id])

def create_user(**params):
    """Helper function to create a new user."""
    defaults = {
        'email': 'test@example.com',
        'username': 'testuser',
        'password': 'testpass123',
        'role': 'Student'
    }
    defaults.update(params)
    return get_user_model().objects.create_user(**defaults)

def create_category(**params):
    """Helper function to create a category."""
    defaults = {
        'name': 'Programming',
        'description': 'Programming courses'
    }
    defaults.update(params)
    return Category.objects.create(**defaults)

def create_course(user, category, **params):
    """Helper function to create a course."""
    defaults = {
        'title': 'Python Course',
        'description': 'A comprehensive Python course.',
        'category': category,
        'price': 50.00,
        'instructor': user
    }
    defaults.update(params)
    return Course.objects.create(**defaults)

def create_enrollment(user, course, **params):
    """Helper function to create an enrollment."""
    defaults = {
        'student': user,
        'course': course
    }
    defaults.update(params)
    return Enrollment.objects.create(**defaults)

class PublicCourseApiTests(TestCase):
    """Test unauthenticated API requests."""
    def setUp(self):
        self.client = APIClient()
        self.category = create_category()
        self.instructor = create_user(
            username='instructor_user',
            email='instructor@example.com',
            password='password123',
            role='Instructor'
        )
        self.course = create_course(self.instructor, self.category, title='Public Course 1')
        create_course(self.instructor, self.category, title='Public Course 2')

    def test_retrieve_courses(self):
        """Test retrieving courses without authentication."""
        response = self.client.get(COURSE_URL)
        courses = Course.objects.all()
        serializer = CourseSerializer(courses, many=True)

        # Check if response is paginated (contains 'results' key)
        if 'results' in response.data:
            sorted_response_data = sorted(response.data['results'], key=lambda x: x['id'])
        else:
            sorted_response_data = sorted(response.data, key=lambda x: x['id'])

        # Compare the sorted data with the serializer data
        sorted_serializer_data = sorted(serializer.data, key=lambda x: x['id'])

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted_response_data, sorted_serializer_data)

    def test_unauthorized_user_cannot_create_course(self):
        """Test that unauthenticated users cannot create a course."""
        course_data = {
            'title': 'Unauthorized Course',
            'description': 'Unauthorized course creation attempt.',
            'category': self.category.id,
            'price': 10.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Course.objects.filter(title=course_data['title']).exists(), False)

    def test_avg_rating_course(self):
        """Test retrieving course ratings without authentication."""
        user = create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='Student'
        )
        create_enrollment(user=user, course=self.course)
        Rating.objects.create(
            rating=3,
            user=user,
            course=self.course,
            comment="compiled review"
        )
        other_user = create_user(
            username='other_user',
            email='other@example.com',
            password='testpass123',
            role='Student'
        )
        create_enrollment(user=other_user, course=self.course)
        Rating.objects.create(
            rating=5,
            user=other_user,
            course=self.course,
            comment="excellent course"
        )
        self.course.refresh_from_db()
        url = detail_url(course_id=self.course.id)
        res = self.client.get(url)

        # Assertions
        self.assertEqual(res.status_code, status.HTTP_200_OK)  # Verify successful response
        self.assertIn('average_rating', res.data)  # Check if 'average_rating' is in the response
        self.assertEqual(float(res.data['average_rating']), 4.0)  # Verify the average rating
        self.assertIn('ratings', res.data)  # Check if 'ratings' is in the response



class PrivateCourseApiTests(TestCase):
    """Test authenticated API requests for courses."""
    def setUp(self):
        self.client = APIClient()
        self.category = create_category()
        self.user = create_user(
            username='johnDevelopment',
            email='john@example.com',
            password='testpassword',
            role='Instructor'
        )
        self.client.force_authenticate(user=self.user)

        # Create temporary image for testing
        self.image_file = self._create_temp_image()

    def _create_temp_image(self):
        """Helper function to create a temporary image file."""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_image:
            image = Image.new('RGB', (10, 10))
            image.save(temp_image, format='JPEG')
            return temp_image.name

    def tearDown(self):
        """Clean up after tests."""
        os.unlink(self.image_file)

    def test_retrieve_courses(self):
        """Test retrieving a list of courses for the authenticated user."""
        # Create two courses associated with the authenticated user and category
        create_course(self.user, self.category)
        create_course(self.user, self.category, title='Another Course')

        # Send a GET request to the COURSE_URL
        response = self.client.get(COURSE_URL)

        # Filter courses that belong to the authenticated user
        courses = Course.objects.filter(instructor=self.user)

        # Serialize the courses data
        serializer = CourseSerializer(courses, many=True)

        # Assert the response status is 200 OK
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if response is paginated (contains 'results' key)
        if 'results' in response.data:
            sorted_response_data = sorted(response.data['results'], key=lambda x: x['id'])
        else:
            sorted_response_data = sorted(response.data, key=lambda x: x['id'])

        # Sort the serialized course data
        sorted_serializer_data = sorted(serializer.data, key=lambda x: x['id'])

        # Compare the sorted response data with the serialized data
        self.assertEqual(sorted_response_data, sorted_serializer_data)


    def test_get_course_by_id(self):
        """Test retrieving a course by ID."""
        course = create_course(self.user, self.category)
        url = detail_url(course.id)
        response = self.client.get(url)
        serializer = CourseSerializer(course)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, serializer.data)

    def test_create_course_with_image(self):
        """Test creating a course with an image."""
        with open(self.image_file, 'rb') as image_file:
            course_data = {
                'title': 'New Python Course',
                'description': 'A brand-new Python course.',
                'category': self.category.id,
                'price': 50.00,
                'image': image_file
            }
            response = self.client.post(COURSE_URL, course_data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(id=response.data['id'])
        self.assertTrue(course.image)
        self.assertEqual(course.title, course_data['title'])
        self.assertEqual(course.instructor, self.user)

    def test_instructor_can_create_course(self):
        """Test that an instructor can create a course."""
        course_data = {
            'title': 'Instructor Course',
            'description': 'Description for instructor course.',
            'category': self.category.id,
            'price': 100.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(id=response.data['id'])
        self.assertEqual(course.title, course_data['title'])

    def test_non_instructor_cannot_create_course(self):
        """Test that a non-instructor cannot create a course."""
        self.user.role = 'Student'
        self.user.save()
        course_data = {
            'title': 'Student Course',
            'description': 'Description for student course.',
            'category': self.category.id,
            'price': 100.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Course.objects.filter(title=course_data['title']).exists())

    def test_course_creation_with_invalid_data(self):
        """Test creating a course with invalid data."""
        invalid_data = {
            'title': '',  # Missing title
            'description': 'No title provided.',
            'category': self.category.id,
            'price': -10.00,  # Negative price
        }
        response = self.client.post(COURSE_URL, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Course.objects.count(), 0)

    def test_partial_update_course(self):
        """Test partial update of a course using PATCH."""
        course = create_course(self.user, self.category)
        updated_data = {
            'title': 'Updated Python Course',
        }
        url = detail_url(course.id)
        response = self.client.patch(url, updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course.refresh_from_db()
        self.assertEqual(course.title, updated_data['title'])

    def test_full_update_course(self):
        """Test full update of a course using PUT."""
        course = create_course(self.user, self.category)
        updated_data = {
            'title': 'Updated Python Course',
            'description': 'An updated Python course.',
            'category': self.category.id,
            'price': 70.00,
        }
        url = detail_url(course.id)
        response = self.client.put(url, updated_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course.refresh_from_db()
        self.assertEqual(course.title, updated_data['title'])
        self.assertEqual(course.description, updated_data['description'])
        self.assertEqual(course.price, updated_data['price'])

    def test_delete_course(self):
        """Test deleting a course."""
        course = create_course(self.user, self.category)
        url = detail_url(course.id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(id=course.id).exists())

    def test_course_description_sanitization(self):
        """Test that course descriptions do not allow XSS attacks."""
        malicious_description = '<script>alert("XSS")</script>'
        course_data = {
            'title': 'Secure Course',
            'description': malicious_description,
            'category': self.category.id,
            'price': 30.00,
        }
        response = self.client.post(COURSE_URL, course_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        course = Course.objects.get(id=response.data['id'])
        self.assertNotIn('<script>', course.description)

    def test_rate_limiting(self):
        """Test that rate limiting prevents brute-force attacks."""
        course_data = {
            'title': 'Test Course',
            'description': 'Rate limit test',
            'category': self.category.id,
            'price': 10.00,
        }

        # Make requests up to the rate limit
        for _ in range(60):  # Rate limit is set to 5/m
            response = self.client.post(COURSE_URL, course_data)

        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)