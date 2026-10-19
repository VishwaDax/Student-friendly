from django.conf import settings
from elasticsearch import Elasticsearch

_client = None


def get_es_client():
    global _client

    if _client is None:
        _client = Elasticsearch(settings.ELASTICSEARCH_URL)

    return _client


def create_book_index():
    client = get_es_client()
    index_name = settings.ELASTICSEARCH_BOOK_INDEX

    if not client.indices.exists(index=index_name):
        client.indices.create(
            index=index_name,
            mappings={
                "properties": {
                    "book_id": {"type": "integer"},
                    "student_id": {"type": "integer"},
                    "title": {"type": "text"},
                    "language": {"type": "keyword"},
                    "standard": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "content": {"type": "text"},
                }
            },
        )

    return client