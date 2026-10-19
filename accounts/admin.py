
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Student


@admin.register(Student)
class StudentAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Student Information",
            {
                "fields": (
                    "age",
                    "standard",
                    "preferred_language",
                )
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "age",
        "standard",
        "preferred_language",
    )
