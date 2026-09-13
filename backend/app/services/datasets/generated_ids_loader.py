"""
Dataset Loader for AmAFakePerson123/TrialforGeneratedIDs (MIDV-2020)
Provides robust local caching, parsing of VIA annotations, and seamless loading
without triggering HuggingFace's imagefolder string class label bug.
"""
import os
import json
from typing import Dict, Any, List, Optional
import cv2
import numpy as np
from PIL import Image

# Resolve repo root directory (Authenova/data/samples/generated_ids)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../"))
BASE_DATA_DIR = os.path.join(REPO_ROOT, "data/samples/generated_ids")


def load_trial_generated_ids(sample_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load and parse document samples from the AmAFakePerson123/TrialforGeneratedIDs dataset.
    Returns a list of structured document records with images, bounding boxes, and ground-truth metadata.
    """
    data_dir = sample_dir or BASE_DATA_DIR
    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Generated IDs sample directory not found at {data_dir}")

    # Discover all annotation JSONs
    annotation_files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
    annotations_by_type: Dict[str, Dict[str, Any]] = {}

    for ann_file in annotation_files:
        doc_type = ann_file.replace(".json", "")
        with open(os.path.join(data_dir, ann_file), "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                meta_dict = data.get("_via_img_metadata", {})
                # Index by filename attribute for clean lookup (e.g. "63.jpg")
                by_filename = {item["filename"]: item for item in meta_dict.values() if "filename" in item}
                annotations_by_type[doc_type] = by_filename
            except Exception:
                continue

    # Discover image files
    image_files = [f for f in os.listdir(data_dir) if f.endswith((".jpg", ".png"))]
    records: List[Dict[str, Any]] = []

    for img_file in image_files:
        img_path = os.path.join(data_dir, img_file)
        parts = img_file.rsplit("_", 1)
        if len(parts) != 2:
            continue
        doc_type = parts[0]
        file_num = parts[1].split(".")[0]
        via_filename = f"{int(file_num):02d}.jpg" if file_num.isdigit() else parts[1]

        # Extract annotations if available
        meta = annotations_by_type.get(doc_type, {}).get(via_filename, {})
        fields: Dict[str, Any] = {}
        boxes: Dict[str, Any] = {}

        if meta and "regions" in meta:
            for r in meta["regions"]:
                attr = r.get("region_attributes", {})
                shape = r.get("shape_attributes", {})
                f_name = attr.get("field_name")
                val = attr.get("value")
                if f_name:
                    fields[f_name] = val
                    if shape:
                        boxes[f_name] = shape

        is_passport = "passport" in doc_type.lower()

        records.append({
            "image_path": img_path,
            "filename": img_file,
            "document_type": doc_type,
            "is_passport": is_passport,
            "fields": fields,
            "boxes": boxes,
            "photo_box": boxes.get("photo") or boxes.get("face"),
            "mrz_line0": fields.get("mrz_line0"),
            "mrz_line1": fields.get("mrz_line1")
        })

    return records
