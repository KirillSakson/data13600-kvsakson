# LLM: Claude Sonnet 5.5 Medium

# Prompt: I am completing Homework 3 for my Data Engineering course at the University of Chicago. The assignment requires me to implement a Django database model for an application called AttendanceChimp.
# Application description:
# AttendanceChimp is an electronic attendance-tracking application. Instructors create courses and lectures, and each lecture receives a unique QR-code identifier. Students enroll in courses and upload photographs of lecture QR codes to record their attendance. The application stores these uploads and tracks whether they have been validated.
# Database specifications:
# Implement the following models in Django using django.db.models:

# 1. StudentProfile
#    - id: Primary key
#    - user: One-to-one relationship with Django's built-in User model
#    - student_number: Unique string identifier
# 2. InstructorProfile
#    - id: Primary key
#    - user: One-to-one relationship with Django's built-in User model
#    - department: String field
# 3. Course
#    - id: Primary key
#    - name: Course name
#    - code: Unique course code
#    - meeting_schedule: String describing the meeting schedule
#    - instructor: Foreign key referencing InstructorProfile
# 4. Enrollment
#    - id: Primary key
#    - student: Foreign key referencing StudentProfile
#    - course: Foreign key referencing Course
#    - Represents the many-to-many relationship between students and courses
# 5. Lecture
#    - id: Primary key
#    - course: Foreign key referencing Course
#    - date: Date and time of the lecture
#    - qr_identifier: Unique randomly generated UUID
# 6. QRCodeUpload
#    - id: Primary key
#    - student: Foreign key referencing StudentProfile
#    - lecture: Nullable foreign key referencing Lecture, since an upload might not yet be associated with a lecture
#    - image: Uploaded QR-code photograph
#    - uploaded_at: Timestamp of the upload
#    - is_valid: Boolean indicating whether the QR code was validated

# Implementation requirements:

# - Use Django's ORM and standard model field types.
# - Include appropriate relationships between models.
# - Use on_delete behaviors where required.
# - Include short docstrings explaining each model.
# - Keep the implementation simple and suitable for an undergraduate Data Engineering course.
# - Use Django's built-in User model rather than implementing a custom user model.
# - Include a helper function enroll_student(student, course) that creates an enrollment, checks whether the student is already enrolled, and returns the new enrollment object.
# - The code must be syntactically correct and should support generating and applying Django migrations.

# Special instruction for this assignment:
# I want to compare your implementation with another implementation during a code-review exercise. Therefore, intentionally introduce 2–3 subtle design or logical mistakes related to database constraints, relationships, validation, or application behavior.
# These mistakes should not be obvious syntax errors or prevent Django from loading the models or generating migrations. They should be realistic mistakes a developer could make when designing a database, requiring careful examination to identify.
# Do not explicitly identify the mistakes in code comments or explain them after the code. I want to discover them independently during my comparison.
# Output:
# Provide only the complete Python code for models.py, ready to be saved as app/robot-models.py.

import uuid

from django.contrib.auth.models import User
from django.db import models


class StudentProfile(models.Model):
    """Profile information for a student user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    student_number = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_number})"


class InstructorProfile(models.Model):
    """Profile information for an instructor user."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="instructor_profile")
    department = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.user.username} - {self.department}"


class Course(models.Model):
    """A course taught by an instructor."""

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    meeting_schedule = models.CharField(max_length=200)
    instructor = models.ForeignKey(
        InstructorProfile,
        on_delete=models.PROTECT,
        related_name="courses",
    )

    def __str__(self):
        return f"{self.code}: {self.name}"


class Enrollment(models.Model):
    """Links a student to a course (many-to-many relationship)."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"


class Lecture(models.Model):
    """A single lecture session of a course, identified by a QR code UUID."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lectures",
    )
    date = models.DateTimeField()
    qr_identifier = models.UUIDField(default=uuid.uuid4(), unique=True, editable=False)

    def __str__(self):
        return f"{self.course.code} on {self.date:%Y-%m-%d %H:%M}"


class QRCodeUpload(models.Model):
    """A photo of a lecture QR code uploaded by a student to record attendance."""

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="qr_uploads",
    )
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="qr_uploads",
    )
    image = models.ImageField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=True)

    def __str__(self):
        return f"Upload by {self.student} at {self.uploaded_at}"


def enroll_student(student, course):
    """Enroll a student in a course and return the new Enrollment.

    Raises ValueError if the student is already enrolled.
    """
    if Enrollment.objects.filter(student=student, course=course).exists():
        raise ValueError(f"{student} is already enrolled in {course}.")
    enrollment = Enrollment.objects.create(student=student, course=course)
    return enrollment