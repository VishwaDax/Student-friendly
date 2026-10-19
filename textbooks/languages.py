
LANGUAGE_CHOICES = [
    ("english", "English"),
    ("assamese", "Assamese"),
    ("bengali", "Bengali"),
    ("bodo", "Bodo"),
    ("dogri", "Dogri"),
    ("gujarati", "Gujarati"),
    ("hindi", "Hindi"),
    ("kannada", "Kannada"),
    ("kashmiri", "Kashmiri"),
    ("konkani", "Konkani"),
    ("maithili", "Maithili"),
    ("malayalam", "Malayalam"),
    ("manipuri", "Manipuri (Meitei)"),
    ("marathi", "Marathi"),
    ("nepali", "Nepali"),
    ("odia", "Odia"),
    ("punjabi", "Punjabi"),
    ("sanskrit", "Sanskrit"),
    ("santali", "Santali"),
    ("sindhi", "Sindhi"),
    ("tamil", "Tamil"),
    ("telugu", "Telugu"),
    ("urdu", "Urdu")
]

STANDARD_CHOICES = [
    (f"class_{number}", f"Class {number}")
    for number in range(1, 13)
]
