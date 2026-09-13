import numpy as np


def cosine_similarity(embedding1, embedding2):
    """
    Calculate cosine similarity between two face embeddings.
    """

    vector1 = np.asarray(embedding1, dtype=np.float32)
    vector2 = np.asarray(embedding2, dtype=np.float32)

    norm1 = np.linalg.norm(vector1)
    norm2 = np.linalg.norm(vector2)

    if norm1 == 0 or norm2 == 0:
        raise ValueError("Cannot calculate similarity for zero embeddings.")

    similarity = np.dot(vector1, vector2) / (norm1 * norm2)

    return float(similarity)


def verify_faces(embedding1, embedding2, threshold=0.70):
    """
    Compare two face embeddings and return cosine similarity and result.
    """
    similarity = cosine_similarity(embedding1, embedding2)
    result = "PASS" if similarity >= threshold else "FAIL"
    return similarity, result