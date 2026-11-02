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

from .models import (InstructorProfile, StudentProfile)
#                      , Course, Enrollment,
#                      Lecture, QRCodeUpload, is_instructor, is_student,
#                      getUploadsForCourse)

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



# ---------------------------------------------------------------------------
# HW6  — getUploads
# ---------------------------------------------------------------------------



