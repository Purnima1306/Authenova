"""
Generated IDs Dataset & Passport Verification Model Evaluation Suite
Evaluates dataset loading from AmAFakePerson123/TrialforGeneratedIDs and tests
retrained passport authenticity and biometric verification models.
"""
import os
import pytest
from app.services.datasets.generated_ids_loader import load_trial_generated_ids
from app.services.passport_verification.model import passport_verifier_model

REAL_PASSPORT = "backend/uploads/DOC-8A14A02C_doc.jpeg"


class TestGeneratedIdsEvaluation:
    def test_load_trial_generated_ids_records(self):
        records = load_trial_generated_ids()
        assert len(records) > 0, "No records loaded from TrialforGeneratedIDs"
        passports = [r for r in records if r["is_passport"]]
        non_passports = [r for r in records if not r["is_passport"]]
        assert len(passports) > 0, "No passport records found"
        assert len(non_passports) > 0, "No non-passport records found"

    def test_passport_verification_model_training(self):
        records = load_trial_generated_ids()
        metrics = passport_verifier_model.train_on_records(records)
        assert metrics["accuracy"] >= 0.90
        assert metrics["precision"] >= 0.90
        assert metrics["recall"] >= 0.90
        assert metrics["f1"] >= 0.90
        assert metrics["roc_auc"] >= 0.90

    def test_verify_real_passport(self):
        if not os.path.exists(REAL_PASSPORT):
            pytest.skip("Real passport not found")
        res = passport_verifier_model.verify_document(REAL_PASSPORT)
        assert res["is_passport"] is True
        assert res["passport_confidence"] >= 0.70
        assert res["verification_status"] == "VERIFIED_PASSPORT"

    def test_verify_non_passport_rejection(self):
        records = load_trial_generated_ids()
        non_passports = [r for r in records if not r["is_passport"]]
        if not non_passports:
            pytest.skip("No non-passport sample found")
        sample = non_passports[0]
        res = passport_verifier_model.verify_document(sample["image_path"])
        assert res["is_passport"] is False
        assert res["passport_confidence"] < 0.50
        assert res["verification_status"] == "NON_PASSPORT_DOCUMENT"

    def test_biometric_calibration_scaling(self):
        low_p = passport_verifier_model.calibrate_biometric_similarity(0.30)
        thresh_p = passport_verifier_model.calibrate_biometric_similarity(0.58)
        high_p = passport_verifier_model.calibrate_biometric_similarity(0.85)
        # Calibrated match probability must be strictly monotonic
        assert low_p < thresh_p < high_p
        # Near threshold should be balanced around 0.50
        assert 0.45 <= thresh_p <= 0.55
