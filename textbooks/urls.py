from django.urls import path
from .views import upload_book

urlpatterns = [
    path("upload/", upload_book, name="upload_book"),
]