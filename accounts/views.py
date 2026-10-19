
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect

from textbooks.models import Book
from .forms import StudentRegistrationForm


def signup(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            student = form.save()
            login(request, student)
            return redirect("dashboard")
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form},
    )


class StudentLoginView(LoginView):
    template_name = "accounts/login.html"


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
