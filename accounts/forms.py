
from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Student


class StudentRegistrationForm(UserCreationForm):
    class Meta:
        model = Student
        fields = [
            "username",
            "email",
            "age",
            "standard",
            "preferred_language",
        ]

    def clean_age(self):
        age = self.cleaned_data.get("age")

        if age is not None and not 3 <= age <= 100:
            raise forms.ValidationError(
                "Enter a valid age."
            )

        return age
