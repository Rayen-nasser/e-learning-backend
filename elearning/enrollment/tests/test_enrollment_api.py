from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from core.models import Category, Course, Enrollment
from decimal import Decimal

User = get_user_model()

class EnrollmentAPITests(APITestCase):
    def setUp(self):
        # Create test users
        self.student = User.objects.create_user(
            email='student@test.com',
            username='student',
            password='testpass123',
            role='Student'
        )
        self.instructor = User.objects.create_user(
            email='instructor@test.com',
            username='instructor',
            password='testpass123',
            role='Instructor'
        )

        # Create a test category
        self.category = Category.objects.create(
            name='Test Category',
            description='Test Category Description'
        )

        # Create a test course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            category=self.category,
            price=Decimal('99.99'),
            instructor=self.instructor
        )

        # Create a test enrollment
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course,
            progress=0.0,
            completed=False
        )

        # Set up the API client
        self.client = APIClient()

    def test_list_enrollments_student(self):
        """Test that students can only see their own enrollments"""
        self.client.force_authenticate(user=self.student)
        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['student'], self.student.id)

    def test_list_enrollments_instructor(self):
        """Test that instructors can see enrollments for their courses"""
        self.client.force_authenticate(user=self.instructor)
        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_enrollment_success(self):
        """Test successful enrollment creation"""
        # Create a new student
        new_student = User.objects.create_user(
            email='newstudent@test.com',
            username='newstudent',
            password='testpass123',
            role='Student'
        )
        self.client.force_authenticate(user=new_student)

        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        data = {'course': self.course.id}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['enrollment']['student'], new_student.id)
        self.assertEqual(response.data['message'], 'Enrolled successfully!')

    def test_create_enrollment_duplicate(self):
        """Test attempting to enroll in the same course twice"""
        self.client.force_authenticate(user=self.student)

        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        data = {'course': self.course.id}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Already enrolled.')

    def test_create_enrollment_instructor_own_course(self):
        """Test that instructors cannot enroll in their own courses"""
        self.client.force_authenticate(user=self.instructor)

        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        data = {'course': self.course.id}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Instructors cannot enroll in their own courses.')

    def test_update_enrollment_progress(self):
        """Test updating enrollment progress"""
        self.client.force_authenticate(user=self.student)

        url = reverse('course:courses-enrollments-detail',
                     kwargs={'course_pk': self.course.id, 'pk': self.enrollment.id})
        data = {'progress': 50.0}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['progress'], 50.0)

    def test_update_enrollment_unauthorized(self):
        """Test that a student cannot update another student's enrollment"""
        other_student = User.objects.create_user(
            email='other@test.com',
            username='other',
            password='testpass123',
            role='Student'
        )
        self.client.force_authenticate(user=other_student)

        url = reverse('course:courses-enrollments-detail',
                     kwargs={'course_pk': self.course.id, 'pk': self.enrollment.id})
        data = {'progress': 50.0}
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_enrollment(self):
        """Test successful enrollment deletion"""
        self.client.force_authenticate(user=self.student)

        url = reverse('course:courses-enrollments-detail',
                     kwargs={'course_pk': self.course.id, 'pk': self.enrollment.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Enrollment.objects.filter(id=self.enrollment.id).exists())

    def test_delete_enrollment_unauthorized(self):
        """Test that a student cannot delete another student's enrollment"""
        other_student = User.objects.create_user(
            email='other@test.com',
            username='other',
            password='testpass123',
            role='Student'
        )
        self.client.force_authenticate(user=other_student)

        url = reverse('course:courses-enrollments-detail',
                     kwargs={'course_pk': self.course.id, 'pk': self.enrollment.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Enrollment.objects.filter(id=self.enrollment.id).exists())

    def test_unauthenticated_access(self):
        """Test that unauthenticated users cannot access enrollment endpoints"""
        # Try to list enrollments
        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Try to create enrollment
        response = self.client.post(url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Try to update enrollment
        url = reverse('course:courses-enrollments-detail',
                     kwargs={'course_pk': self.course.id, 'pk': self.enrollment.id})
        response = self.client.patch(url, {'progress': 50.0})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_enrollments_student_multiple_courses(self):
        """Test that students can only see enrollments for courses they're enrolled in"""
        # Create additional courses
        course2 = Course.objects.create(
            title='Test Course 2',
            description='Test Description 2',
            category=self.category,
            price=Decimal('99.99'),
            instructor=self.instructor
        )

        course3 = Course.objects.create(
            title='Test Course 3',
            description='Test Description 3',
            category=self.category,
            price=Decimal('99.99'),
            instructor=self.instructor
        )

        # Create additional enrollment for the student
        Enrollment.objects.create(
            student=self.student,
            course=course2,
            progress=0.0,
            completed=False
        )

        self.client.force_authenticate(user=self.student)

        # Test first course
        url1 = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        response1 = self.client.get(url1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.data), 1)
        self.assertEqual(response1.data[0]['student'], self.student.id)
        self.assertEqual(response1.data[0]['course'], self.course.id)

        # Test second course
        url2 = reverse('course:courses-enrollments-list', kwargs={'course_pk': course2.id})
        response2 = self.client.get(url2)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data), 1)
        self.assertEqual(response2.data[0]['student'], self.student.id)
        self.assertEqual(response2.data[0]['course'], course2.id)

        # Test third course (not enrolled)
        url3 = reverse('course:courses-enrollments-list', kwargs={'course_pk': course3.id})
        response3 = self.client.get(url3)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response3.data), 0)

    def test_list_enrollments_instructor_multiple_courses(self):
        """Test that instructors can only see enrollments for courses they teach"""
        # Create another instructor
        other_instructor = User.objects.create_user(
            email='other.instructor@test.com',
            username='other_instructor',
            password='testpass123',
            role='Instructor'
        )

        # Create another category
        other_category = Category.objects.create(
            name='Other Test Category',
            description='Other Test Category Description'
        )

        # Create a course for the other instructor
        other_course = Course.objects.create(
            title='Other Course',
            description='Other Description',
            category=other_category,
            price=Decimal('99.99'),
            instructor=other_instructor
        )

        # Create enrollment in other instructor's course
        other_enrollment = Enrollment.objects.create(
            student=self.student,
            course=other_course,
            progress=0.0,
            completed=False
        )

        self.client.force_authenticate(user=self.instructor)

        # Test own course
        url1 = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        response1 = self.client.get(url1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response1.data), 1)

        # Test other instructor's course
        url2 = reverse('course:courses-enrollments-list', kwargs={'course_pk': other_course.id})
        response2 = self.client.get(url2)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response2.data), 0)

    def test_student_cannot_view_nonexistent_course(self):
        """Test that students cannot view enrollments for non-existent courses"""
        self.client.force_authenticate(user=self.student)
        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_student_multiple_enrollments_same_course(self):
        """Test that a student cannot have multiple enrollments in the same course"""
        self.client.force_authenticate(user=self.student)

        # Try to create a second enrollment in the same course
        url = reverse('course:courses-enrollments-list', kwargs={'course_pk': self.course.id})
        data = {'course': self.course.id}

        # First enrollment already exists from setUp
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Already enrolled.')

        # Verify only one enrollment exists
        enrollments = Enrollment.objects.filter(student=self.student, course=self.course)
        self.assertEqual(enrollments.count(), 1)