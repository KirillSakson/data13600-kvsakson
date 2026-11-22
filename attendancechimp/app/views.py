"""
views.py — HTTP request handlers for AttendanceChimp.

Each view corresponds to one URL endpoint.  Views receive an HTTP request,
interact with the database via models.py, and return an HTTP response.
"""

from django.shortcuts import render, redirect
from django.http import (HttpResponse, HttpResponseForbidden,
                         HttpResponseBadRequest, JsonResponse, HttpResponseNotAllowed)
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from datetime import datetime
import zoneinfo
import json
import io

from .models import (InstructorProfile, StudentProfile, Course, Lecture, QRCodeUpload, getUploadsForCourse, decodeQR)
#                      Enrollment, is_instructor, is_student, getUploadsForCourse

CDT = zoneinfo.ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# HW2  — index, time, sum
# ---------------------------------------------------------------------------

def index(request):
    """Render the home page (index.html)."""
    
    current_time = datetime.now(zoneinfo.ZoneInfo("America/Chicago")).strftime("%H:%M")
    context = {
        "current_time": current_time,
        "user": request.user
    }
    return render(request, 'app/index.html', context)

def time_view(request):
    chicago_time = datetime.now(CDT)
    formatted_time = chicago_time.strftime("%H:%M")
    return HttpResponse(formatted_time, content_type="text/plain")

def sum_view(request):
    try:
        # getting request parameters and converting them
        n1 = float(request.GET["n1"])
        n2 = float(request.GET["n2"])
        
        res = n1 + n2
        
        if res.is_integer():
            res = int(res)
        
        return HttpResponse(f"<p>{res}</p>", content_type="text/html")
    except (KeyError, ValueError):
        return JsonResponse({"error": "Provide valid n1 and n2 parameters, please"}, status=400)

# ---------------------------------------------------------------------------
# HW4  — user creation
# ---------------------------------------------------------------------------

from django.views.decorators.http import require_POST
from django.db import transaction


def new(request):
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    return render(request, "app/new.html")

@csrf_exempt
@require_POST
def createUser(request):
    """Create a new user and their student or instructor profile."""

    # read submitted form data
    user_name = request.POST.get("user_name", "").strip()
    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    is_student = request.POST.get("is_student", "")

    # check that all required fields are present
    if not user_name or not email or not password or not is_student:
        return HttpResponseBadRequest("Missing required fields.")
    if is_student not in ("0", "1"):
        return HttpResponseBadRequest("Invalid user role.")
    
    # check whether the email is already registered
    if User.objects.filter(email=email).exists():
        return HttpResponseBadRequest("Email already registered.")

    # prevent duplicate usernames
    if User.objects.filter(username=user_name).exists():
        return HttpResponseBadRequest("Username already exists.")

    # create user and appropriate profile
    with transaction.atomic():
        user = User.objects.create_user(
            username=user_name,
            email=email,
            password=password
        )

        if is_student == "1":
            StudentProfile.objects.create(
                user=user,
                student_number="STU" + str(user.id)
            )
        else:
            InstructorProfile.objects.create(
                user=user,
                department=""
            )

    # log in the newly created user
    login(request, user)

    # return a successful response
    return HttpResponse("User created successfully.", status=200)

# ---------------------------------------------------------------------------
# HW5  — courses, lectures, QR uploads, dump
# ---------------------------------------------------------------------------
import uuid
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET


@login_required
def new_course(request):
    return render(request, "app/new_course.html")


@login_required
def new_lecture(request):
    courses = Course.objects.all()

    context = {
        "courses": courses,
    }

    return render(request, "app/new_lecture.html", context)


@login_required
def new_qr_upload(request):
    return render(request, "app/new_qr_upload.html")


@csrf_exempt
@require_POST
def createCourse(request):
    # check that the logged in user belongs to instructor table
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    instructor = InstructorProfile.objects.filter(user=request.user).first()

    if instructor is None:
        return HttpResponse("Unauthorized", status=401)

    # get data from the form
    course_name = request.POST.get("course-name", "").strip()
    course_code = (
        request.POST.get("course-code")
        or request.POST.get("course")
        or request.POST.get("course-number")
        or course_name
    ).strip()
    start_time = request.POST.get("start-time", "")
    end_time = request.POST.get("end-time", "")

    # get selected weekdays
    days = {
        "day-mon": "Mon",
        "day-tue": "Tue",
        "day-wed": "Wed",
        "day-thu": "Thu",
        "day-fri": "Fri",
    }

    selected_days = []

    for field, day in days.items():
        if field in request.POST:
            selected_days.append(day)

    # validate the form data
    if not course_name or not start_time or not end_time or not selected_days:
        return HttpResponseBadRequest("Missing required fields.")

    if Course.objects.filter(name=course_name).exists():
        return HttpResponseBadRequest("Course already exists.")

    # prepare the course fields
    meeting_schedule = f"{', '.join(selected_days)} {start_time}-{end_time}"

    # check uniqueness of the code, case insensitive
    if Course.objects.filter(course__iexact=course_code).exists():
        return HttpResponseBadRequest("Course code already exists!")
    
    # check start and end times
    try:
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
    except ValueError:
        return HttpResponseBadRequest("Invalid time format.")

    if start_time_obj >= end_time_obj:
        return HttpResponseBadRequest("End time must be after start time.")

    # save the course to the database
    Course.objects.create(
        name=course_name,
        course=course_code,
        meeting_schedule=meeting_schedule,
        instructor=instructor,

        start_time=start_time_obj,
        end_time=end_time_obj,

        day_mon="day-mon" in request.POST,
        day_tue="day-tue" in request.POST,
        day_wed="day-wed" in request.POST,
        day_thu="day-thu" in request.POST,
        day_fri="day-fri" in request.POST,
    )

    return HttpResponse("Course created successfully.", status=200)


@csrf_exempt
@require_POST
def createLecture(request):
    # check that the logged in user belongs to instructor table
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Unauthorized", status=401)

    # get the selected course name and qrdata
    course_name = request.POST.get("choice", "").strip()
    qrdata = request.POST.get("qrdata")

    if not course_name:
        return HttpResponseBadRequest("Missing course name!")

    # find the selected course
    course = Course.objects.filter(name=course_name).first()

    if course is None:
        return HttpResponseBadRequest("Course does not exist!")
    
    # prepare lecture information
    lecture_data = {
        "course": course,
        "date": datetime.now(CDT).date()
    }
    
    # use explicitly provided QR data if available
    if qrdata:
        lecture_data["qr_identifier"] = qrdata

    # create a lecture associated with this course
    Lecture.objects.create(**lecture_data)

    return HttpResponse("Lecture created successfully.", status=200)


@csrf_exempt
@require_POST
def createQRCodeUpload(request):
    # check that the logged in user belongs to student table
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    student = StudentProfile.objects.filter(user=request.user).first()

    if student is None:
        return HttpResponse("Unauthorized", status=401)

    # get the uploaded image
    image = request.FILES.get("imageUpload")

    if image is None:
        return HttpResponseBadRequest("No image uploaded!")
    
    # decode the QR code
    qr_data = decodeQR(image)
    
    # find the lecture matching the decoded identifier
    lecture = None

    if qr_data is not None:
        lecture = Lecture.objects.filter(qr_identifier=qr_data).first()

    # save the upload, even if the QR code is invalid
    QRCodeUpload.objects.create(
        student=student,
        image=image,
        lecture=lecture
    )
    
    # invalid QR code or no matching lecture
    if lecture is None:
        return JsonResponse({"error": "Invalid QR code"}, status=400)

    # valid QR code
    return JsonResponse({"status": "ok"}, status=200)


@require_GET
def dumpUploads(request):
    # check that the logged in user belongs to instructor table
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Unauthorized", status=401)

    # retrieve all QR code uploads from db
    uploads = QRCodeUpload.objects.all()

    # prepare the JSON data
    data = []

    for upload in uploads:
        data.append({
            "username": upload.student.user.username,
            "upload_time": upload.uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse(data, safe=False)

# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------

from django.utils import timezone


@require_GET
def getUploads(request):
    # only instructors can access this endpoint
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    if not InstructorProfile.objects.filter(user=request.user).exists():
        return HttpResponse("Unauthorized", status=401)

    # get the course number from the URL
    course = request.GET.get("course", "").strip()

    if not course:
        return JsonResponse(
            {"error": "Missing course parameter"},
            status=400
        )

    # retrieve valid uploads for the course
    uploads = getUploadsForCourse(course)

    # convert uploads to JSON-compatible dictionaries
    data = []

    for upload in uploads:
        local_time = timezone.localtime(
            upload.uploaded_at,
            CDT
        )

        data.append({
            "username": upload.student.user.username,
            "upload_time": local_time.strftime("%Y-%m-%d %H:%M:%S")
        })

    return JsonResponse(data, safe=False)
