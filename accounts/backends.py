from django.contrib.auth.backends import ModelBackend


class VerifiedEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        user = super().authenticate(
            request,
            username=username,
            password=password,
            **kwargs,
        )
        if user is None or not user.email_verified:
            return None
        return user

    def get_user(self, user_id):
        user = super().get_user(user_id)
        if user is None or not user.email_verified:
            return None
        return user
