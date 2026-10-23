"""
models.py — Data model for AttendanceChimp.

AttendanceChimp is an electronic class attendance tool.  Instructors create
courses and lectures; each lecture is assigned a random QR code.  Students
photograph the QR code and upload the image.  The system decodes the QR code,
matches it to a lecture, and records the attendance.

Entities
--------
- CourseProfile   : extends Django User → instructor-specific data
- StudentProfile  : extends Django User → student-specific data
- Course          : a course taught by one instructor
- Enrollment      : junction table linking students to courses
- Lecture         : a single class meeting (has a QR-code identifier)
- QRCodeUpload    : a student's uploaded QR-code photograph
"""

from django.db import models
from django.contrib.auth.models import User

import logging
import string
import random
import uuid

logger = logging.getLogger(__name__) # set up tracking, auditing, and debugging
                                                               # allows using logger.warning(), logger.error(), 
                                                               # logger.info(), etc. Better than print() for debuggin... 


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

class StudentProfile(models.Model):
    """Store information specific to a student.

    Every student profile is associated with exactly one Django User.
    A user can have at most one student profile, and the student number
    must be unique across all students.
    """

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_number = models.CharField(max_length=30, unique=True)

    def __str__(self):
        return self.user.username + " (" + self.student_number + ")"

class InstructorProfile(models.Model):
    """Store information specific to an instructor.

    Every instructor profile belongs to exactly one Django User.
    A user can have at most one instructor profile. The department
    may be left blank when this information is unavailable.
    """

    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.user.username

# ---------------------------------------------------------------------------
# Course
# ---------------------------------------------------------------------------

class Course(models.Model):
    """Describe one course, its instructor, and its meeting schedule.

    Each course has one instructor, but an instructor may teach several
    courses. The course code is unique. An instructor cannot be removed
    while courses still refer to their profile (PROTECT).
    """

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=30, unique=True)
    meeting_schedule = models.CharField(max_length=255)
    instructor = models.ForeignKey(InstructorProfile, on_delete=models.PROTECT)

    def __str__(self):
        return self.code + ": " + self.name

# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class Enrollment(models.Model):
    """Connect one student with one course.

    This table implements the many-to-many relationship between
    StudentProfile and Course. A student may take many courses, and a
    course may have many students, but the same pair cannot appear twice.
    """

    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "course"],
                name="unique_student_course_enrollment",
            )
        ]

    def __str__(self):
        return self.student.student_number + " - " + self.course.code

# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

class Lecture(models.Model):
    """Represent one lecture of a course.

    Each lecture belongs to exactly one course and has a date and time.
    Its QR identifier is a UUID generated when the lecture is created.
    Each identifier must be unique.
    """

    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    date = models.DateTimeField()
    qr_identifier = models.UUIDField(default=uuid.uuid4, unique=True)

    def __str__(self):
        return self.course.code + " lecture " + str(self.id)


# ---------------------------------------------------------------------------
# QR Code Upload
# ---------------------------------------------------------------------------

class QRCodeUpload(models.Model):
    """Store a photograph of a lecture QR code submitted by a student.

    The student reference is required. The lecture reference is optional
    because the image might not have been matched to a lecture yet.
    Upload time is recorded automatically. is_valid is False until
    the application validates the QR code.
    """

    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE)
    lecture = models.ForeignKey(
        Lecture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    image = models.ImageField(upload_to="qr_uploads/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=False)

    def __str__(self):
        return "QR upload " + str(self.id)

# ---------------------------------------------------------------------------
# Helper / API functions
# ---------------------------------------------------------------------------

def enroll_student(student, course):
    """Enroll an existing student in an existing course.

    Arguments:
        student: a StudentProfile instance.
        course: a Course instance.

    Checks whether the student is already enrolled and raises ValueError
    if so. Otherwise, creates and saves an Enrollment record, logs the
    operation, and returns the new Enrollment instance.
    """

    logger.info("Trying to enroll %s in %s", student.student_number, course.code)

    if Enrollment.objects.filter(student=student, course=course).count() > 0:
        raise ValueError("The student is already enrolled in this course")

    enrollment = Enrollment(student=student, course=course)
    enrollment.save()

    logger.info("Enrolled %s in %s", student.student_number, course.code)
    return enrollment