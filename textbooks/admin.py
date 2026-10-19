from django.contrib import admin
from .models import Book, BookChunk

admin.site.register(Book)
admin.site.register(BookChunk)