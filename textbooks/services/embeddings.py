from functools import lru_cache

import numpy as np
from django.conf import settings


@lru_cache(maxsize=1)
def get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Textbook embeddings require sentence-transformers. "
            "Install project dependencies with "
            "`pip install -r requirements.txt`."
        ) from exc

    return SentenceTransformer(settings.TEXTBOOK_EMBEDDING_MODEL)


def encode_texts(texts):
    """Return normalized 384-dimensional embeddings for non-empty text."""
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    vectors = np.asarray(vectors, dtype=np.float32)

    expected_shape = (
        len(texts),
        settings.TEXTBOOK_EMBEDDING_DIMENSIONS,
    )
    if vectors.shape != expected_shape:
        raise ValueError(
            f"Embedding model returned shape {vectors.shape}; "
            f"expected {expected_shape}."
        )
    if not np.isfinite(vectors).all():
        raise ValueError("Embedding model returned non-finite values.")

    norms = np.linalg.norm(vectors, axis=1)
    if np.any(norms == 0):
        raise ValueError("Embedding model returned a zero-length vector.")

    vectors = vectors / norms[:, np.newaxis]
    return vectors.tolist()
