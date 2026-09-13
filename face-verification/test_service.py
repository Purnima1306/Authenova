import json

from app.service import verify_images


from pathlib import Path

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    reference_image = str(base_dir / "test_images/face_image.png")
    test_image = str(base_dir / "test_images/different_face.png")

    result = verify_images(
        reference_image,
        test_image
    )

    print("===== VERIFICATION RESULT =====")
    print(json.dumps(result, indent=4))