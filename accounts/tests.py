import re
from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Student


class BrandingTests(TestCase):
    def test_login_page_uses_shared_brand_assets(self):
        response = self.client.get("/accounts/login/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "/static/accounts/images/studymate-mark.png",
        )
        self.assertContains(
            response,
            "/static/accounts/images/studymate-logo.png",
        )
        self.assertContains(response, 'class="site-footer"')
        self.assertContains(response, "Contact us")
        self.assertContains(
            response,
            "mailto:vishwavengadeshd@gmail.com",
        )


class StudentLoginTests(TestCase):
    def setUp(self):
        self.password = "Strong-test-password-1!"
        self.student = Student.objects.create_user(
            username="student-one",
            email="student@example.com",
            email_verified=True,
            password=self.password,
        )

    def test_login_page_identifies_username_or_email_field(self):
        response = self.client.get("/accounts/login/")

        self.assertContains(response, "Username or email")

    def test_login_with_username(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "student-one", "password": self.password},
        )

        self.assertRedirects(response, "/accounts/dashboard/")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.student.pk,
        )

    def test_login_with_email(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "student@example.com", "password": self.password},
        )

        self.assertRedirects(response, "/accounts/dashboard/")
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            self.student.pk,
        )

    def test_email_login_is_case_insensitive(self):
        response = self.client.post(
            "/accounts/login/",
            {"username": "STUDENT@EXAMPLE.COM", "password": self.password},
        )

        self.assertRedirects(response, "/accounts/dashboard/")

    def test_duplicate_email_does_not_select_an_arbitrary_account(self):
        Student.objects.create_user(
            username="student-two",
            email="student@example.com",
            password=self.password,
        )

        response = self.client.post(
            "/accounts/login/",
            {"username": "student@example.com", "password": self.password},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unverified_student_cannot_log_in_with_username_or_email(self):
        self.student.email_verified = False
        self.student.save(update_fields=["email_verified"])

        for identifier in ("student-one", "student@example.com"):
            response = self.client.post(
                "/accounts/login/",
                {"username": identifier, "password": self.password},
            )
            self.assertEqual(response.status_code, 200)
            self.assertNotIn("_auth_user_id", self.client.session)

    def test_unverified_existing_session_cannot_access_dashboard(self):
        self.student.email_verified = False
        self.student.save(update_fields=["email_verified"])
        self.client.force_login(self.student)

        response = self.client.get(reverse("dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationTests(TestCase):
    signup_data = {
        "username": "new-student",
        "email": "new-student@example.com",
        "age": "15",
        "standard": "class_10",
        "preferred_language": "english",
        "password1": "Strong-test-password-1!",
        "password2": "Strong-test-password-1!",
    }

    def test_signup_sends_verification_email_and_does_not_log_in(self):
        response = self.client.post("/accounts/signup/", self.signup_data)

        self.assertRedirects(response, reverse("verification_sent"))
        self.assertEqual(len(mail.outbox), 1)
        student = Student.objects.get(username="new-student")
        self.assertFalse(student.email_verified)
        self.assertFalse(student.is_active)
        self.assertNotIn("_auth_user_id", self.client.session)
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        self.assertEqual(len(code), 6)
        self.assertNotEqual(student.email_otp_hash, code)
        self.assertEqual(
            self.client.session["pending_email_verification_student_id"],
            student.pk,
        )

    def test_valid_otp_verifies_and_activates_student(self):
        student = Student.objects.create_user(
            username="pending-student",
            email="pending@example.com",
            is_active=False,
            email_verified=False,
            password="Strong-test-password-1!",
        )
        self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()

        response = self.client.post(
            reverse("verify_email_otp"),
            {"code": code},
        )

        student.refresh_from_db()
        self.assertTrue(student.email_verified)
        self.assertTrue(student.is_active)
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(student.email_otp_hash, "")
        self.assertIsNone(student.email_otp_expires_at)

    def test_invalid_otp_does_not_activate_account(self):
        student = Student.objects.create_user(
            username="pending-student",
            email="pending@example.com",
            is_active=False,
            email_verified=False,
            password="Strong-test-password-1!",
        )
        self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )
        sent_code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        wrong_code = "000000" if sent_code != "000000" else "000001"
        response = self.client.post(
            reverse("verify_email_otp"),
            {"code": wrong_code},
        )

        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.email_verified)
        self.assertFalse(student.is_active)
        self.assertEqual(student.email_otp_attempts, 1)

    def test_expired_otp_does_not_activate_account(self):
        student = Student.objects.create_user(
            username="pending-student",
            email="pending@example.com",
            is_active=False,
            email_verified=False,
            password="Strong-test-password-1!",
        )
        self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )
        student.refresh_from_db()
        student.email_otp_expires_at = timezone.now() - timedelta(seconds=1)
        student.save(update_fields=["email_otp_expires_at"])
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        response = self.client.post(
            reverse("verify_email_otp"),
            {"code": code},
        )

        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.email_verified)
        self.assertFalse(student.is_active)

    def test_too_many_wrong_codes_lock_otp(self):
        student = Student.objects.create_user(
            username="pending-student",
            email="pending@example.com",
            is_active=False,
            email_verified=False,
            password="Strong-test-password-1!",
        )
        self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        wrong_code = "000000" if code != "000000" else "000001"
        for _ in range(5):
            response = self.client.post(
                reverse("verify_email_otp"),
                {"code": wrong_code},
            )
        student.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(student.email_otp_attempts, 5)
        self.assertFalse(student.email_verified)
        self.assertContains(response, "Too many incorrect attempts")

    def test_resend_is_throttled_for_one_minute(self):
        student = Student.objects.create_user(
            username="pending-student",
            email="pending@example.com",
            is_active=False,
            email_verified=False,
            password="Strong-test-password-1!",
        )
        self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )
        student.refresh_from_db()
        original_hash = student.email_otp_hash

        response = self.client.post(
            "/accounts/request-verification/",
            {"email": student.email},
        )

        student.refresh_from_db()
        self.assertRedirects(response, reverse("verification_sent"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(student.email_otp_hash, original_hash)

    def test_verified_student_can_log_in(self):
        self.client.post(
            "/accounts/signup/",
            self.signup_data,
        )
        student = Student.objects.get(username="new-student")
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        self.client.post(reverse("verify_email_otp"), {"code": code})

        response = self.client.post(
            "/accounts/login/",
            {
                "username": student.email,
                "password": self.signup_data["password1"],
            },
        )

        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(
            int(self.client.session["_auth_user_id"]),
            student.pk,
        )

    def test_verification_request_response_does_not_disclose_account(self):
        response = self.client.post(
            "/accounts/request-verification/",
            {"email": "not-registered@example.com"},
        )

        self.assertRedirects(response, reverse("verification_sent"))
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(
            self.client.get(reverse("verification_sent")),
            "If an unverified account uses that address",
        )
