from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

REGISTER_USER_URL = reverse('user:register')
LOGIN_USER_URL = reverse('user:login')

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """Test the users API (publicly accessible)."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_with_student_role_success(self):
        """Test creating a new user with 'Student' role."""
        payload = {
            'email': 'student@example.com',
            'password': 'studentpass123',
            'username': 'studentuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'Student'  # Assigning 'Student' role
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(user.role, 'Student')
        self.assertNotIn('password', res.data['user'])
        self.assertIn('tokens', res.data)

    def test_create_user_with_admin_role_success(self):
        """Test creating a new user with 'Admin' role."""
        payload = {
            'email': 'admin@example.com',
            'password': 'adminpass123',
            'username': 'adminuser',
            'first_name': 'Admin',
            'last_name': 'User',
            'role': 'Admin'  # Assigning 'Admin' role
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(user.role, 'Admin')  # Ensure the role is saved correctly
        self.assertNotIn('password', res.data['user'])
        self.assertIn('tokens', res.data)

    def test_create_user_with_Instructor_role_success(self):
        """Test creating a new user with 'Instructor' role."""
        payload = {
            'email': 'Instructor@example.com',
            'password': 'instructorPass123',
            'username': 'instructorUser',
            'first_name': 'instructor',
            'last_name': 'User',
            'role': 'Instructor'
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload['email'])
        self.assertTrue(user.check_password(payload['password']))
        self.assertEqual(user.role, 'Instructor')  # Ensure the role is saved correctly
        self.assertNotIn('password', res.data['user'])
        self.assertIn('tokens', res.data)

    def test_user_with_email_exit_error(self):
        """Test that creating a user with an existing email returns an error."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test that creating a user with a password that is too short returns an error."""
        payload = {
            'email': 'test@example.com',
            'password': 'test',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'Student'
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=payload['email']
        ).exists()
        self.assertFalse(user_exists)

    def test_login_user_success(self):
        """Test that a user can login successfully."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(LOGIN_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertIn('user', res.data)

    def test_login_user_failure(self):
        """Test that a user cannot login with incorrect credentials."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
            'username': 'testuser',
            'first_name': 'John',
            'last_name': 'Doe',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(LOGIN_USER_URL, {'email': 'test@example.com', 'password': 'wrongpass'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('tokens', res.data)

    def test_login_with_not_existing_user(self):
        """Test that a user cannot login with a non-existent user."""
        payload = {
            'email': 'test@example.com',
            'password': 'testpass123',
        }
        res = self.client.post(LOGIN_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
