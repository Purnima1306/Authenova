from app.embedder import generate_embedding


from pathlib import Path

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    image_path = str(base_dir / "test_images/detected_face_1.jpg")

    embedding = generate_embedding(image_path)

    print("Embedding generated successfully!")
    print("Embedding length:", len(embedding))
    print("First 5 values:", embedding[:5])