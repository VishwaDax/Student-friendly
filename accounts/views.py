
import logging
import smtplib

from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages

from textbooks.models import Book
from .email_verification import (
    OTP_SESSION_KEY,
    issue_email_otp,
    verify_email_otp as check_email_otp,
)
from .forms import (
    EmailOTPForm,
    EmailVerificationRequestForm,
    StudentAuthenticationForm,
    StudentRegistrationForm,
)
from .models import Student


logger = logging.getLogger(__name__)


def signup(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            student = form.save(commit=False)
            student.is_active = False
            student.email_verified = False
            student.save()
            form.save_m2m()
            request.session[OTP_SESSION_KEY] = student.pk
            try:
                issue_email_otp(student)
            except (OSError, smtplib.SMTPException, RuntimeError):
                logger.exception(
                    "Could not send verification code for student %s",
                    student.pk,
                )
                messages.error(
                    request,
                    "Your account was created, but we couldn't send the "
                    "verification code. Request another code to continue.",
                )
                return redirect("request_email_verification")
            return redirect("verification_sent")
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form},
    )


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = StudentAuthenticationForm


def verification_sent(request):
    return render(request, "accounts/verification_sent.html")


def request_email_verification(request):
    if request.method == "POST":
        form = EmailVerificationRequestForm(request.POST)
    else:
        form = EmailVerificationRequestForm()

    if request.method == "POST" and form.is_valid():
        matching_students = list(
            Student.objects.filter(
                email__iexact=form.cleaned_data["email"],
                email_verified=False,
            ).order_by("pk")[:2]
        )
        if len(matching_students) == 1:
            student = matching_students[0]
            request.session[OTP_SESSION_KEY] = student.pk
            try:
                sent = issue_email_otp(student)
            except (OSError, smtplib.SMTPException, RuntimeError):
                logger.exception(
                    "Could not send verification code for student %s",
                    student.pk,
                )
                messages.error(
                    request,
                    "We couldn't send a verification code right now. "
                    "Please try again later.",
                )
                return redirect("request_email_verification")
            if not sent:
                messages.info(
                    request,
                    "A code was sent recently. Please wait one minute "
                    "before requesting another.",
                )

        messages.success(
            request,
            "If an unverified account uses that address, a verification "
            "code is available. Check your inbox; a recently sent code "
            "may still be active.",
        )
        return redirect("verification_sent")

    return render(
        request,
        "accounts/request_verification.html",
        {"form": form},
    )


def verify_email_otp(request):
    student_id = request.session.get(OTP_SESSION_KEY)
    if not student_id:
        return redirect("verification_sent")

    student = get_object_or_404(Student, pk=student_id)
    if student.email_verified:
        request.session.pop(OTP_SESSION_KEY, None)
        return redirect("login")

    form = EmailOTPForm(request.POST or None)
    verification_message = None
    if request.method == "POST" and form.is_valid():
        result = check_email_otp(student, form.cleaned_data["code"])
        if result == "verified":
            request.session.pop(OTP_SESSION_KEY, None)
            messages.success(
                request,
                "Your email is verified. You can now log in.",
            )
            return redirect("login")
        if result == "expired":
            verification_message = (
                "That code has expired. Request a new verification code."
            )
        elif result == "locked":
            verification_message = (
                "Too many incorrect attempts. Request a new verification code."
            )
        elif result == "missing":
            verification_message = (
                "No active verification code was found. Request a new one."
            )
        else:
            verification_message = "That code is incorrect. Please try again."

    return render(
        request,
        "accounts/verify_otp.html",
        {
            "form": form,
            "email": student.email,
            "verification_message": verification_message,
        },
    )


@login_required
def dashboard(request):
    books = Book.objects.filter(
        student=request.user
    ).order_by("-uploaded_at")

    return render(
        request,
        "accounts/dashboard.html",
        {"books": books},
    )
