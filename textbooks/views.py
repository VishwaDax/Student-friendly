from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from elasticsearch import Elasticsearch
from elasticsearch import ApiError
from elasticsearch import ConnectionError as ESConnectionError

from .forms import BookUploadForm
from .models import Book
from .services.pdf_processor import process_book


@login_required
def upload_book(request):
    if request.method == "POST":
        form = BookUploadForm(request.POST, request.FILES)

        if form.is_valid():
            book = form.save(commit=False)

            # Always assign ownership from the logged-in user.
            book.student = request.user
            book.status = "processing"
            book.save()

            try:
                count = process_book(book)

                book.status = "ready"
                book.save(update_fields=["status"])

                messages.success(
                    request,
                    f"Book processed successfully. "
                    f"{count} pages with text were saved."
                )
                return redirect("dashboard")

            except Exception:
                book.status = "failed"
                book.save(update_fields=["status"])

                messages.error(
                    request,
                    "Book processing failed. Check the terminal "
                    "for the technical error and try again."
                )
    else:
        form = BookUploadForm()

    return render(
        request,
        "textbooks/upload_book.html",
        {"form": form},
    )