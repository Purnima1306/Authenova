
from app.embedder import generate_embedding
from app.verifier import verify_faces


def verify_images(reference_image, test_image, threshold=0.70):
    """
    Verify whether two images belong to the same person.

    Args:
        reference_image: Reference image file/path.
        test_image: Test image file/path.
        threshold: Similarity threshold for verification.

    Returns:
        Dictionary containing verification result.
    """

    if reference_image is None:
        raise ValueError("Reference image is required.")

    if test_image is None:
        raise ValueError("Test image is required.")

    # Generate face embeddings
    reference_embedding = generate_embedding(reference_image)
    test_embedding = generate_embedding(test_image)

    if reference_embedding is None:
        raise ValueError("No face detected in reference image.")

    if test_embedding is None:
        raise ValueError("No face detected in test image.")

    # Compare embeddings
    similarity, result = verify_faces(
        reference_embedding,
        test_embedding,
        threshold=threshold
    )

    verified = result == "PASS"

    return {
        "verified": verified,
        "similarity": round(float(similarity), 4),
        "threshold": threshold,
        "result": result
    }
