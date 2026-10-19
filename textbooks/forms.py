from django import forms

from .models import Book


class BookUploadForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = [
            "title",
            "language",
            "standard",
            "subject",
            "pdf_file",
        ]

    def clean_pdf_file(self):
        pdf = self.cleaned_data["pdf_file"]

        if not pdf.name.lower().endswith(".pdf"):
            raise forms.ValidationError(
                "Only PDF files are allowed."
            )

        if pdf.size > 50 * 1024 * 1024:
            raise forms.ValidationError(
                "Maximum PDF size is 50 MB."
            )

        # Check the file signature rather than relying only
        # on the filename extension.
        if pdf.read(5) != b"%PDF-":
            raise forms.ValidationError(
                "The uploaded file is not a valid PDF."
            )

        pdf.seek(0)
        return pdf