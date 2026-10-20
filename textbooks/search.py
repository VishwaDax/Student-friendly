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

def search_textbooks(student, query, book_id=None, limit=10):
    """
    Search only the authenticated student's indexed books.

    If book_id is supplied, search only that student's
    selected book.
    """
    query = query.strip()

    if not query:
        return []

    client = get_es_client()

    filters = [
        {"term": {"student_id": student.id}},
    ]

    if book_id is not None:
        filters.append(
            {"term": {"book_id": book_id}}
        )

    response = client.search(
        index=settings.ELASTICSEARCH_BOOK_INDEX,
        size=limit,
        query={
            "bool": {
                "filter": filters,
                "must": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "content^3",
                                "title^2",
                            ],
                            "type": "best_fields",
                        }
                    }
                ],
            }
        },
        _source=[
            "book_id",
            "student_id",
            "title",
            "language",
            "page_number",
            "content",
        ],
    )

    results = []

    for hit in response["hits"]["hits"]:
        source = hit["_source"]

        results.append({
            "book_id": source["book_id"],
            "title": source["title"],
            "language": source["language"],
            "page_number": source["page_number"],
            "content": source["content"],
            "score": hit["_score"],
        })

    return results