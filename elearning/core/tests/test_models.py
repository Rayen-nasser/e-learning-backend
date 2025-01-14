from django.test import TestCase
from django.contrib.auth import get_user_model
from core import models
from datetime import datetime, timedelta


class CustomUserManagerTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_create_user_with_valid_data(self):
        user = self.User.objects.create_user(
            email='user@example.com',
            username='testuser',
            password='password123',
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
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
            profile_image='http://example.com/media/uploads/user_profiles/testuser.jpg',
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
            time_limit=timedelta(hours=1, minutes=30),
            is_active=False,
        )

    def test_create_quiz(self):
        self.assertEqual(self.quiz.title, 'Test Quiz')
        self.assertEqual(self.quiz.description, 'This is a test quiz')
        self.assertEqual(self.quiz.lesson, self.lesson)
        self.assertEqual(self.quiz.time_limit, timedelta(hours=1, minutes=30))
        self.assertFalse(self.quiz.is_active)

    def test_create_question(self):
        question = models.Question.objects.create(
            question_text='This is a test question',
            quiz=self.quiz,
            question_type='multiple_choice',
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


class EnrollmentModelTest(TestCase):
    """Tests for the Enrollment model"""

    def setUp(self):
        # Create a user
        self.student = models.User.objects.create_user(
            username='teststudent',
            email='student@example.com',
            password='password123',
            role='Student'
        )

        self.instructor = models.User.objects.create_user(
            email='instructor@example.com',
            username='instructoruser',
            password='password123',
            role='Instructor'
        )

        # Create a course
        self.course = models.Course.objects.create(
            title='Sample Course',
            description='This is a sample course.',
            instructor=self.instructor,
            category='Sample Category',
            price=49.99
        )

        # Create a lesson
        self.lesson = models.Lesson.objects.create(
            title='Test Lesson',
            description='This is a test lesson',
            course=self.course,
        )

        # Create an enrollment
        self.enrollment = models.Enrollment.objects.create(
            student=self.student,
            course=self.course,
            progress=0.0,
            completed=False
        )

        # Create a quiz
        self.quiz = models.Quiz.objects.create(
            title='Sample Quiz',
            description='This is a sample quiz.',
            lesson=self.lesson,
            time_limit=timedelta(hours=1, minutes=30),
            is_active=True
        )

    def test_enrollment_creation(self):
        """Test that an Enrollment instance is created successfully"""
        self.assertEqual(self.enrollment.student, self.student)
        self.assertEqual(self.enrollment.course, self.course)
        self.assertEqual(self.enrollment.progress, 0.0)
        self.assertFalse(self.enrollment.completed)

    def test_progress_update(self):
        """Test updating the progress field"""
        self.enrollment.progress = 75.5
        self.enrollment.save()

        updated_enrollment = models.Enrollment.objects.get(id=self.enrollment.id)
        self.assertEqual(updated_enrollment.progress, 75.5)

    def test_mark_completed(self):
        """Test marking the enrollment as completed"""
        self.enrollment.completed = True
        self.enrollment.save()

        updated_enrollment = models.Enrollment.objects.get(id=self.enrollment.id)
        self.assertTrue(updated_enrollment.completed)

    def test_create_submission(self):
        submission = models.Submission.objects.create(
            quiz=self.quiz,
            student=self.student,
            score=85,
        )
        self.assertEqual(submission.quiz, self.quiz)
        self.assertEqual(submission.student, self.student)
        self.assertEqual(submission.score, 85)

