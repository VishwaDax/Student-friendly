from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from elasticsearch import Elasticsearch
from elasticsearch import ApiError
from elasticsearch import ConnectionError as ESConnectionError

from .forms import BookUploadForm
from .models import Book
from .services.pdf_processor import process_book
from .services.topic_detector import detect_topics
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Book, Topic
from .search import search_textbooks



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
                topic_count = detect_topics(book)

                book.status = "ready"
                book.save(update_fields=["status"])

                messages.success(
                    request,
                    f"Book processed successfully. "
                    f"{count} pages with text were saved."
                    f"{topic_count} headings were detected."
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

@login_required
def book_chat(request, book_id):
    # A student cannot open another student's book.
    book = get_object_or_404(
        Book,
        id=book_id,
        student=request.user,
        status="ready",
    )

    query = request.GET.get("q", "").strip()
    results = []

    if query:
        results = search_textbooks(
            student=request.user,
            query=query,
            book_id=book.id,
        )

    topics = Topic.objects.filter(book=book)

    return render(
        request,
        "textbooks/book_chat.html",
        {
            "book": book,
            "query": query,
            "results": results,
            "topics": topics,
        },
    )


@login_required
def main_room(request):
    query = request.GET.get("q", "").strip()
    results = []

    if query:
        results = search_textbooks(
            student=request.user,
            query=query,
        )

    return render(
        request,
        "textbooks/main_room.html",
        {
            "query": query,
            "results": results,
        },
    )