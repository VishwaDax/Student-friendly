from django.urls import path
from .views import upload_book, book_chat, delete_book, main_room

urlpatterns = [
     path("upload/", upload_book, name="upload_book"),
    path("main-room/", main_room, name="main_room"),
    path(
        "book/<int:book_id>/delete/",
        delete_book,
        name="delete_book",
    ),
    path(
        "book/<int:book_id>/chat/",
        book_chat,
        name="book_chat",
    ),
]