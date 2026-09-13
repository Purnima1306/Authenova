from app.embedder import generate_embedding
from app.verifier import verify_faces


def test_same_person():
    image1 = "test_images/face_image.png"
    image2 = "test_images/face_image.png"

    embedding1 = generate_embedding(image1)
    embedding2 = generate_embedding(image2)

    similarity, result = verify_faces(
        embedding1,
        embedding2,
        threshold=0.70
    )

    print(f"\nSame-person similarity: {similarity}")
    print(f"Result: {result}")

    assert result == "PASS"


def test_different_person():
    image1 = "test_images/face_image.png"
    image2 = "test_images/different_face.png"

    embedding1 = generate_embedding(image1)
    embedding2 = generate_embedding(image2)

    similarity, result = verify_faces(
        embedding1,
        embedding2,
        threshold=0.75
    )

    print(f"\nDifferent-person similarity: {similarity}")
    print(f"Result: {result}")

    assert result == "FAIL"