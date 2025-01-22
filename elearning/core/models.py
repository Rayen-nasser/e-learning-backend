import datetime
from decimal import Decimal
import os
from uuid import uuid4
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db.models import Avg, Count
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.core.validators import MinValueValidator, MaxValueValidator
from jsonschema import ValidationError

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, username, password, **extra_fields)


def user_profile_upload_path(instance, filename):
    """Generate file path for new profile image"""
    extension = filename.split('.')[-1]
    filename = f"{uuid4()}.{extension}"
    return os.path.join("user_profiles/", filename)

def course_images_upload_path(instance, filename):
    """Generate file path for new profile image"""
    extension = filename.split('.')[-1]
    filename = f"{uuid4()}.{extension}"
    return os.path.join("course_images/", filename)

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('Student', 'Student'),
        ('Instructor', 'Instructor'),
        ('Admin', 'Admin'),
    ]

    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Student')
    profile_image = models.ImageField(
        upload_to=user_profile_upload_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True,
        help_text="Upload a profile image (optional)"
    )

    # Administrative and activity flags
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    # Override related_name for groups and permissions
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='custom_user_groups',
        blank=True,
        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='custom_user_permissions',
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    objects = CustomUserManager()

    def __str__(self):
        return self.email

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Level(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="courses")
    price = models.DecimalField(max_digits=8, decimal_places=2)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True, related_name="courses")
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses")
    image = models.ImageField(
        upload_to=course_images_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])],
        null=True,
        blank=True,
        help_text="Upload a course image (optional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def update_average_rating(self):
        # Cache average rating
        self.average_rating_cached = self.ratings.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
        self.save()

# Updated Rating Model
class Rating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ratings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='ratings')
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[
             MinValueValidator(Decimal('0.0')),
            MaxValueValidator(Decimal('5.0'))
        ],
        default=1.0
    )  # Supports ratings like 4.5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'course')  # Ensure a user rates a course only once

    def __str__(self):
        return f"{self.user.username} - {self.course.title}: {self.rating} stars"

    def clean(self):
        # Check if the user is enrolled in the course
        is_enrolled = Enrollment.objects.filter(student=self.user, course=self.course).exists()
        if not is_enrolled:
            raise ValidationError("User must be enrolled in the course to leave a rating.")

    def save(self, *args, **kwargs):
        self.clean()  # Call the validation check before saving
        super().save(*args, **kwargs)

# Enrollment Model
class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, related_name='enrollment', on_delete=models.CASCADE)
    date_enrolled = models.DateTimeField(auto_now_add=True)
    progress = models.FloatField(default=0.0)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student.username} - {self.course.title}"

# Signal to Update Student Count
@receiver(post_save, sender=Rating)
@receiver(post_delete, sender=Rating)
def update_course_average_rating(sender, instance, **kwargs):
    course = instance.course
    course.update_average_rating()


class Lesson(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


# Custom file path function to organize files by course and lesson
def lesson_file_path(instance, filename):
    # Organize by course and lesson title
    course_title = instance.lesson.course.title.replace(" ", "_")  # Replace spaces with underscores for file names
    lesson_title = instance.lesson.title.replace(" ", "_")

    # Use a unique identifier for the file to avoid name collisions
    unique_name = f"{uuid4()}_{filename}"

    # Return the path in the format: lesson_files/{course_title}/{lesson_title}/{unique_name}
    return os.path.join('lesson_files', course_title, lesson_title, unique_name)

class LessonFile(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=lesson_file_path, validators=[
        FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'mp4', 'jpg', 'jpeg', 'png', 'txt','zip'])
    ])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"File for {self.lesson.title}"

class Quiz(models.Model):
    title = models.CharField(max_length=255)
    lesson = models.ForeignKey('Lesson', on_delete=models.CASCADE, related_name='quizzes')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    time_limit = models.DurationField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Question(models.Model):
    QUESTION_TYPES = [
        ('multiple_choice', 'Multiple Choice'),  # User selects one correct option from multiple choices.
        ('true_false', 'True/False'),            # User decides if a statement is true or false.
        ('short_answer', 'Short Answer'),        # User provides a brief text answer.
        ('fill_in_the_blank', 'Fill in the Blank'), # User completes a sentence or statement with the correct word(s).
    ]

    quiz = models.ForeignKey('Quiz', on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    options = models.JSONField()
    correct_option = models.IntegerField()
    points = models.PositiveIntegerField(default=1)
    question_type = models.CharField(
        max_length=50,
        choices=QUESTION_TYPES,
        default='multiple_choice',
        help_text="Type of the question (e.g., Multiple Choice, True/False, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.question_text

class Submission(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    submission_date = models.DateTimeField(auto_now_add=True)
    score = models.PositiveIntegerField(default=0)
    answers = models.JSONField(default=list)

    def __str__(self):
        return f"{self.student.username}'s submission for {self.quiz.title}"