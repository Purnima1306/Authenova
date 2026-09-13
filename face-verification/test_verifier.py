from app.embedder import generate_embedding
from app.verifier import cosine_similarity


from pathlib import Path

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    image1 = str(base_dir / "test_images/detected_face_1.jpg")

    embedding1 = generate_embedding(image1)
    embedding2 = generate_embedding(image1)

    similarity = cosine_similarity(embedding1, embedding2)

    print("Similarity score:", similarity)