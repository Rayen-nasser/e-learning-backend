from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models


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
            )
        self.assertEqual(str(context.exception), "The Email field must be set")

    def test_create_superuser_invalid_flags(self):
        with self.assertRaises(ValueError):
            self.User.objects.create_superuser(
                email='admin@example.com',
                username='adminuser',
                password='adminpassword123',
                is_staff=False
            )
        with self.assertRaises(ValueError):
            self.User.objects.create_superuser(
                email='admin@example.com',
                username='adminuser',
                password='adminpassword123',
                is_superuser=False
            )


class CourseAndLessonTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.instructor = self.User.objects.create_user(
            email='instructor@example.com',
            username='instructoruser',
            password='password123',
            first_name='Instructor',
            last_name='User',
            role='Instructor'
        )
        self.course = models.Course.objects.create(
            title='Test Course',
            description='This is a test course',
            instructor=self.instructor,
            price='10.00',
            category="Test Category"
        )
        self.lesson = models.Lesson.objects.create(
            title='Test Lesson',
            description='This is a test lesson',
            course=self.course,
        )

    def test_create_course(self):
        self.assertEqual(self.course.title, 'Test Course')

    def test_create_lesson(self):
        self.assertEqual(self.lesson.title, 'Test Lesson')

    def test_create_lesson_file(self):
        lesson_file = models.LessonFile.objects.create(
            lesson=self.lesson,
            file='lesson_files/test_file.pdf'
        )
        self.assertEqual(lesson_file.lesson, self.lesson)
        self.assertEqual(lesson_file.file, 'lesson_files/test_file.pdf')


class QuizAndQuestionTests(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.instructor = self.User.objects.create_user(
            email='instructor@example.com',
            username='instructoruser',
            password='password123',
            role='Instructor'
        )
        self.course = models.Course.objects.create(
            title='Test Course',
            description='This is a test course',
            instructor=self.instructor,
            price='10.00',
            category="Test Category"
        )
        self.lesson = models.Lesson.objects.create(
            title='Test Lesson',
            description='This is a test lesson',
            course=self.course,
        )
        self.quiz = models.Quiz.objects.create(
            title='Test Quiz',
            description='This is a test quiz',
            lesson=self.lesson,
            time_limit=30,
            is_active=False,
        )

    def test_create_quiz(self):
        self.assertEqual(self.quiz.title, 'Test Quiz')
        self.assertEqual(self.quiz.description, 'This is a test quiz')
        self.assertEqual(self.quiz.lesson, self.lesson)
        self.assertEqual(self.quiz.time_limit, 30)
        self.assertFalse(self.quiz.is_active)

    def test_create_question(self):
        question = models.Question.objects.create(
            question_text='This is a test question',
            quiz=self.quiz,
            type='multiple_choice',
            options={
                'option1': 'True',
                'option2': 'False',
                'option3': 'False',
                'option4': 'True'
            },
            correct_option=1,
            points=3,
        )
        self.assertEqual(question.question_text, 'This is a test question')
        self.assertEqual(question.correct_option, 1)
        self.assertEqual(question.points, 3)
