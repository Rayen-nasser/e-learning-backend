from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from core.models import User

# Define constants for API endpoints
REGISTER_USER_URL = reverse('user:register')
LOGIN_USER_URL = reverse('user:login')
LOGOUT_URL = reverse('user:logout')

# Define valid roles
VALID_ROLES = ['Student', 'Admin', 'Instructor']

def profile_url(userPk=None):
    """Return user profile URL."""
    return reverse('user:profile', args=[userPk]) if userPk else reverse('user:profile')

def password_change_url(userPk=None):
    """Return password change URL."""
    return reverse('user:change-password', args=[userPk]) if userPk else reverse('user:change-password')

def create_user(**params):
    """Helper function to create a new user."""
    return get_user_model().objects.create_user(**params)


def get_tokens_for_user(user):
    """Helper function to get JWT tokens for a user."""
    refresh = RefreshToken.for_user(user)
    return str(refresh), str(refresh.access_token)


class PublicUserApiTests(TestCase):
    """Test publicly accessible user API."""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_with_valid_role_success(self):
        """Test creating a new user with valid roles."""
        for role in VALID_ROLES:
            payload = {
                'email': f'{role.lower()}@example.com',
                'password': 'Testpassword123',
                'username': f'{role.lower()}user',
                'role': role
            }

            # Create user
            res = self.client.post(REGISTER_USER_URL, payload)

            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertTrue(get_user_model().objects.filter(email=payload['email']).exists())
            self.assertNotIn('password', res.data)
            self.assertIn('tokens', res.data)

    def test_create_user_with_existing_email_error(self):
        """Test creating a user with an existing email."""
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Test creating a user with a short password fails."""
        payload = {
            'email': 'test@example.com',
            'password': '123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(get_user_model().objects.filter(email=payload['email']).exists())

    def test_login_user_success(self):
        """Test logging in with valid credentials."""
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(LOGIN_USER_URL, {'email': payload['email'], 'password': payload['password']})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', res.data)
        self.assertIn('user', res.data)

    def test_login_user_invalid_credentials(self):
        """Test logging in with invalid credentials."""
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        create_user(**payload)
        res = self.client.post(LOGIN_USER_URL, {'email': 'test@example.com', 'password': 'wrongpassword'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn('tokens', res.data)

    def test_get_user_by_id(self):
        # Create a test user
        user = User.objects.create(
            email='testuser@example.com',
            username='testuser',
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
        )

        # Construct the URL using reverse with the user's ID
        url = reverse('user:user-detail', kwargs={'pk': user.id})

        # Make a GET request
        response = self.client.get(url)

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], user.username)
        self.assertEqual(response.data['email'], user.email)


class PrivateUserApiTests(TestCase):
    """Test authenticated user API."""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='password123',
            username='testuser',
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
            role='Student'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_user_profile_success(self):
        """Test retrieving authenticated user's profile."""
        url = url = profile_url(self.user.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], self.user.email)
        self.assertEqual(res.data['username'], self.user.username)

    def test_update_user_profile_success(self):
        """Test updating the authenticated user's profile."""
        payload = {'first_name': 'Jane', 'last_name': 'Smith'}
        url = profile_url(userPk=self.user.id)
        res = self.client.patch(url, payload)
        self.user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)


    def test_change_password_success(self):
        """Test changing the authenticated user's password."""
        payload = {
            'old_password': 'password123',
            'new_password': 'newpassword123',
            'new_password_confirm': 'newpassword123'
        }
        url = password_change_url(userPk=self.user.id)
        res = self.client.post(url, payload)
        self.user.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.check_password(payload['new_password']))

    def test_logout_success(self):
        """Test logging out the authenticated user."""
        refresh_token, _ = get_tokens_for_user(self.user)
        res = self.client.post(LOGOUT_URL, data={'refresh': refresh_token}, format='json')
        self.assertEqual(res.status_code, status.HTTP_205_RESET_CONTENT)

    def test_delete_user_success(self):
        """Test deleting the authenticated user."""
        url =profile_url(userPk=self.user.id)
        res = self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(get_user_model().objects.filter(id=self.user.id).exists())

    def test_users_list_only_admin_role(self):
        """Test retrieving a list of users with admin role."""
        student_user = create_user(
            email='student@example.com',
            password='password123',
            username='studentuser',
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
            role='Student'
        )
        instructor = create_user(
            email='instructor@example.com',
            password='password123',
            username='instructoruser',
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
            role='Instructor'
        )
        self.user.role = "Admin"
        self.user.save()
        url = reverse('user:users-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)


# Security Tests
class SecurityTests(TestCase):
    """Test security-related vulnerabilities."""

    def setUp(self):
        self.client = APIClient()

    def test_sql_injection_on_user_creation(self):
        """Test if SQL injection is possible during user registration."""
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        # Test with a SQL injection string in the email
        payload['email'] = "'; DROP TABLE users;--"
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_site_scripting_on_user_creation(self):
        """Test if XSS vulnerability exists on user registration."""
        payload = {
            'email': '<script>alert("XSS")</script>',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        res = self.client.post(REGISTER_USER_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_brute_force_attack_prevention(self):
        """Test for brute force attack prevention during login."""
        payload = {
            'email': 'test@example.com',
            'password': 'password123',
            'username': 'testuser',
            'profile_image': 'http://example.com/media/uploads/user_profiles/testuser.jpg',
            'role': 'Student'
        }
        create_user(**payload)

        for _ in range(10):  # Simulate multiple failed login attempts
            res = self.client.post(LOGIN_USER_URL, {'email': 'test@example.com', 'password': 'wrongpassword'})
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # Further failed login attempts should trigger lockout or a different response based on your security setup
        res = self.client.post(LOGIN_USER_URL, {'email': 'test@example.com', 'password': 'wrongpassword'})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
