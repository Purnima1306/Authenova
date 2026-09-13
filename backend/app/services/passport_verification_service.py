"""
Passport Verification Service
Loads and executes the trained PassportVerificationModel for document-level
passport vs non-passport classification using 33-dimensional structural and visual features.
"""
import logging
import os
from typing import Dict, Any, Union
import numpy as np

from app.services.passport_verification.model import passport_verifier_model, MODEL_SAVE_PATH

logger = logging.getLogger("authenova.passport_verification")


class PassportVerificationService:
    """Production service interfacing with the trained PassportVerificationModel."""

    def __init__(self):
        self.model = passport_verifier_model
        self.model_version = "1.0.0"
        self._ensure_loaded()

    def _ensure_loaded(self) -> bool:
        """Ensure the model weights are loaded from the artifact file."""
        if not self.model.is_trained:
            success = self.model.load(MODEL_SAVE_PATH)
            if success:
                logger.info("[PassportVerification] Loaded model artifact from %s", MODEL_SAVE_PATH)
            else:
                logger.warning("[PassportVerification] Model artifact not found at %s", MODEL_SAVE_PATH)
            return success
        return True

    def classify_document(self, document_image: Union[str, np.ndarray]) -> Dict[str, Any]:
        """
        Classify whether the uploaded document image has the visual and structural features of a passport.
        
        Args:
            document_image: File path or cv2 numpy image (preferably canonical orientation).

        Returns:
            Structured verification result object.
        """
        logger.info("[PassportVerification] input received: %s", type(document_image).__name__)

        # Safe failure handling if model is missing or cannot load
        if not self._ensure_loaded():
            logger.error("[PassportVerification] Model artifact unavailable.")
            return {
                "is_passport": False,
                "confidence": 0.0,
                "status": "UNCERTAIN",
                "model": "passport_verifier",
                "model_version": self.model_version,
                "features": 0,
                "error": "Model artifact unavailable"
            }

        try:
            # Extract the exact 33-dimensional feature vector
            features = self.model.extract_document_features(document_image)
            feature_count = int(features.shape[0])
            logger.info("[PassportVerification] feature_count=%d", feature_count)

            if feature_count != 33:
                logger.warning("[PassportVerification] Unexpected feature dimension: %d (expected 33)", feature_count)

            # Inference
            features_2d = features.reshape(1, -1)
            prob = float(self.model.doc_classifier.predict_proba(features_2d)[0, 1])
            is_passport = bool(prob >= 0.50)
            confidence = round(prob, 4)

            # Non-misleading document-type classification status
            status = "PASSPORT_DETECTED" if is_passport else "NON_PASSPORT_DOCUMENT"

            logger.info("[PassportVerification] prediction=%s", is_passport)
            logger.info("[PassportVerification] confidence=%.4f", confidence)

            return {
                "is_passport": is_passport,
                "confidence": confidence,
                "status": status,
                "model": "passport_verifier",
                "model_version": self.model_version,
                "features": feature_count
            }

        except Exception as e:
            logger.error("[PassportVerification] Feature extraction or inference failed: %s", str(e))
            return {
                "is_passport": False,
                "confidence": 0.0,
                "status": "UNCERTAIN",
                "model": "passport_verifier",
                "model_version": self.model_version,
                "features": 0,
                "error": str(e)
            }


# Singleton service instance
passport_verification_service = PassportVerificationService()
