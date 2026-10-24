import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render

from conversations.models import ChatMessage, ChatSession
from .forms import BookUploadForm
from .models import Book, Topic
from .services.local_search import hybrid_search
from .services.llm_service import (
    generate_textbook_answer,
    has_sufficient_evidence,
)
from .services.pdf_processor import process_book
from .services.topic_detector import detect_topics


logger = logging.getLogger(__name__)
NO_EVIDENCE_ANSWER = (
    "I couldn't find enough supporting information in your uploaded "
    "textbook(s) to answer that question."
)


def _invalid_question_answer(message):
    return {
        "status": "invalid_question",
        "answer": message,
        "sources": [],
    }


def _chat_session_for(student, scope, book, question):
    sessions = ChatSession.objects.filter(
        student=student,
        scope=scope,
        book=book,
    ).order_by("-created_at")
    session = sessions.first()
    if session is None:
        session = ChatSession.objects.create(
            student=student,
            scope=scope,
            book=book,
            title=question[:200],
        )
    return session


def _answer_question(request, scope, book, question):
    from django.conf import settings

    if len(question) > settings.TEXTBOOK_MAX_QUESTION_CHARACTERS:
        return (
            _invalid_question_answer(
                "Please keep your question under "
                f"{settings.TEXTBOOK_MAX_QUESTION_CHARACTERS} characters."
            ),
            None,
            [],
        )

    session = _chat_session_for(
        request.user,
        scope,
        book,
        question,
    )
    ChatMessage.objects.create(
        session=session,
        role="student",
        content=question,
    )
    if book:
        results = hybrid_search(
            student=request.user,
            query=question,
            book_id=book.pk,
        )
    else:
        results = hybrid_search(
            student=request.user,
            query=question,
        )

    if not has_sufficient_evidence(results):
        response = {
            "status": "insufficient_evidence",
            "answer": NO_EVIDENCE_ANSWER,
            "sources": [],
        }
        results = []
    else:
        response = generate_textbook_answer(
            question,
            results,
            language=request.user.get_preferred_language_display(),
        )

    if response["status"] in {"ok", "insufficient_evidence"}:
        ChatMessage.objects.create(
            session=session,
            role="assistant",
            content=response["answer"],
        )
    return response, session, results


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
                    f"{count} passages were saved. "
                    f"{topic_count} headings were detected."
                )
                return redirect("dashboard")

            except Exception:
                logger.exception(
                    "Textbook processing failed for book %s",
                    book.pk,
                )
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
@require_POST
def delete_book(request, book_id):
    book = get_object_or_404(
        Book,
        id=book_id,
        student=request.user,
    )
    pdf_storage = book.pdf_file.storage
    pdf_name = book.pdf_file.name
    book_title = book.title
    book.delete()

    try:
        if pdf_name:
            pdf_storage.delete(pdf_name)
    except OSError:
        logger.exception(
            "Failed to delete PDF storage file for book %s",
            book_id,
        )
        messages.warning(
            request,
            f'"{book_title}" and its database records were deleted, '
            "but its stored PDF could not be removed.",
        )
    else:
        messages.success(
            request,
            f'"{book_title}" and its textbook data were deleted.',
        )

    return redirect("dashboard")


@login_required
def book_chat(request, book_id):
    # A student cannot open another student's book.
    book = get_object_or_404(
        Book,
        id=book_id,
        student=request.user,
        status="ready",
    )

    query = request.POST.get("q", "").strip()
    chat_session = ChatSession.objects.filter(
        student=request.user,
        scope="book",
        book=book,
    ).order_by("-created_at").first()
    results = []
    answer = None

    if request.method == "POST" and not query:
        answer = _invalid_question_answer("Please enter a question.")
    elif query:
        answer, chat_session, results = _answer_question(
            request,
            "book",
            book,
            query,
        )

    topics = Topic.objects.filter(book=book)
    chat_messages = (
        chat_session.messages.order_by("created_at")
        if chat_session
        else []
    )

    return render(
        request,
        "textbooks/book_chat.html",
        {
            "book": book,
            "query": query,
            "results": results,
            "answer": answer,
            "chat_messages": chat_messages,
            "topics": topics,
        },
    )


@login_required
def main_room(request):
    has_ready_books = Book.objects.filter(
        student=request.user,
        status="ready",
    ).exists()
    query = request.POST.get("q", "").strip()
    results = []
    answer = None
    chat_session = ChatSession.objects.filter(
        student=request.user,
        scope="main_room",
        book__isnull=True,
    ).order_by("-created_at").first()

    if request.method == "POST" and not query:
        answer = _invalid_question_answer("Please enter a question.")
    elif query:
        answer, chat_session, results = _answer_question(
            request,
            "main_room",
            None,
            query,
        )

    chat_messages = (
        chat_session.messages.order_by("created_at")
        if chat_session
        else []
    )

    return render(
        request,
        "textbooks/main_room.html",
        {
            "query": query,
            "results": results,
            "answer": answer,
            "chat_messages": chat_messages,
            "has_ready_books": has_ready_books,
        },
    )