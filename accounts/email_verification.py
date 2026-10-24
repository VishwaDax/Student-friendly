import secrets
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone


OTP_SESSION_KEY = "pending_email_verification_student_id"
OTP_LENGTH = 6
OTP_MAX_AGE = timedelta(minutes=10)
OTP_RESEND_INTERVAL = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 5


def issue_email_otp(student):
    now = timezone.now()
    if (
        student.email_otp_sent_at
        and now - student.email_otp_sent_at < OTP_RESEND_INTERVAL
    ):
        return False

    code = f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"
    student.email_otp_hash = make_password(code)
    student.email_otp_expires_at = now + OTP_MAX_AGE
    student.email_otp_sent_at = now
    student.email_otp_attempts = 0
    student.save(
        update_fields=[
            "email_otp_hash",
            "email_otp_expires_at",
            "email_otp_sent_at",
            "email_otp_attempts",
        ]
    )

    try:
        sent_count = send_mail(
            subject="Your StudyMate AI verification code",
            message=(
                f"Your StudyMate AI email verification code is: {code}\n\n"
                "Enter this six-digit code in the verification screen. "
                "It expires in 10 minutes. If you did not request this code, "
                "you can ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[student.email],
            fail_silently=False,
        )
        if sent_count != 1:
            raise RuntimeError("The verification code email was not sent.")
    except (OSError, smtplib.SMTPException, RuntimeError):
        student.email_otp_hash = ""
        student.email_otp_expires_at = None
        student.email_otp_sent_at = None
        student.email_otp_attempts = 0
        student.save(
            update_fields=[
                "email_otp_hash",
                "email_otp_expires_at",
                "email_otp_sent_at",
                "email_otp_attempts",
            ]
        )
        raise
    return True


def verify_email_otp(student, submitted_code):
    now = timezone.now()
    if student.email_verified:
        return "verified"
    if not student.email_otp_hash or not student.email_otp_expires_at:
        return "missing"
    if student.email_otp_attempts >= OTP_MAX_ATTEMPTS:
        return "locked"
    if student.email_otp_expires_at <= now:
        return "expired"

    if not check_password(submitted_code, student.email_otp_hash):
        student.email_otp_attempts += 1
        student.save(update_fields=["email_otp_attempts"])
        if student.email_otp_attempts >= OTP_MAX_ATTEMPTS:
            return "locked"
        return "invalid"

    student.email_verified = True
    student.is_active = True
    student.email_otp_hash = ""
    student.email_otp_expires_at = None
    student.email_otp_sent_at = None
    student.email_otp_attempts = 0
    student.save(
        update_fields=[
            "email_verified",
            "is_active",
            "email_otp_hash",
            "email_otp_expires_at",
            "email_otp_sent_at",
            "email_otp_attempts",
        ]
    )
    return "verified"
