from django.test import TestCase
from django.contrib.auth import get_user_model

class CustomUserManagerTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_create_user_with_valid_data(self):
        user = self.User.objects.create_user(
            email='user@example.com',
            username='testuser',
            password='password123',
            first_name='John',
            last_name='Doe',
            role='Student'
        )
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('password123'))
        self.assertEqual(user.role, 'Student')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_email(self):
        with self.assertRaises(ValueError) as context:
            self.User.objects.create_user(
                email=None,
                username='testuser',
                password='password123',
                first_name='John',
                last_name='Doe'
            )
        self.assertEqual(str(context.exception), "The Email field must be set")

    def test_create_user_without_role(self):
        user = self.User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='password123'
        )
        self.assertEqual(user.role, 'Student')  # Default role

    def test_create_superuser_without_is_staff(self):
        with self.assertRaises(ValueError) as context:
            self.User.objects.create_superuser(
                email='admin@example.com',
                username='adminuser',
                password='adminpassword123',
                is_staff=False
            )
        self.assertEqual(
            str(context.exception),
            "Superuser must have is_staff=True."
        )

    def test_create_superuser_without_is_superuser(self):
        with self.assertRaises(ValueError) as context:
            self.User.objects.create_superuser(
                email='admin@example.com',
                username='adminuser',
                password='adminpassword123',
                is_superuser=False
            )
        self.assertEqual(
            str(context.exception),
            "Superuser must have is_superuser=True."
        )
