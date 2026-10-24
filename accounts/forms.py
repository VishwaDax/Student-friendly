
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Student


class EmailVerificationRequestForm(forms.Form):
    email = forms.EmailField(
        label="Email address",
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "placeholder": "Enter your account email",
            }
        ),
    )


class EmailOTPForm(forms.Form):
    code = forms.RegexField(
        regex=r"^\d{6}$",
        label="6-digit verification code",
        error_messages={"invalid": "Enter the 6-digit code from your email."},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "one-time-code",
                "inputmode": "numeric",
                "pattern": r"\d{6}",
                "maxlength": "6",
                "placeholder": "000000",
            }
        ),
    )


class StudentAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(
            attrs={
                "autofocus": True,
                "autocomplete": "username",
                "placeholder": "Enter your username or email",
            }
        ),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username")
        self.email_unverified = False
        if identifier:
            user_model = get_user_model()
            username_field = user_model.USERNAME_FIELD
            users = user_model._default_manager

            # Prefer an exact username match before interpreting the value
            # as an email address.
            if not users.filter(**{username_field: identifier}).exists():
                email_usernames = list(
                    users.filter(email__iexact=identifier)
                    .values_list(username_field, flat=True)[:2]
                )
                if len(email_usernames) == 1:
                    self.cleaned_data["username"] = email_usernames[0]

        cleaned_data = super().clean()
        authenticated_user = self.get_user()
        if (
            authenticated_user is not None
            and not authenticated_user.email_verified
        ):
            self.email_unverified = True
            raise forms.ValidationError(
                "Verify your email address before logging in."
            )
        return cleaned_data


class StudentRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = Student
        fields = [
            "username",
            "email",
            "age",
            "standard",
            "preferred_language",
        ]

    def clean_email(self):
        email = self.cleaned_data.get("email")

        if Student.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A student with this email already exists."
            )

        return email.strip()

    def clean_age(self):
        age = self.cleaned_data.get("age")

        if age is not None and not 3 <= age <= 100:
            raise forms.ValidationError(
                "Enter a valid age."
            )

        return age
