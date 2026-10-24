from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import (
    StudentLoginView,
    dashboard,
    request_email_verification,
    signup,
    verification_sent,
    verify_email_otp,
)

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("login/", StudentLoginView.as_view(), name="login"),
    path("verify-email/", verify_email_otp, name="verify_email_otp"),
    path(
        "verification-sent/",
        verification_sent,
        name="verification_sent",
    ),
    path(
        "request-verification/",
        request_email_verification,
        name="request_email_verification",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
]