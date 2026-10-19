from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import signup, dashboard, StudentLoginView

urlpatterns = [
    path("signup/", signup, name="signup"),
    path("login/", StudentLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("dashboard/", dashboard, name="dashboard"),
]