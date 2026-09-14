"""
Unit and Integration Tests for RAG Explanation Service with LLM & Prompt Engineering
"""
import pytest
from app.services.rag.service import RagExplanationService, rag_service, KNOWLEDGE_BASE


class TestRagExplanationService:
    """Test suite for semantic RAG retrieval and prompt-engineered explanation synthesis."""

    def test_knowledge_base_integrity(self):
        """Verify regulatory knowledge base contains required rules and authorities."""
        assert len(KNOWLEDGE_BASE) >= 10
        for entry in KNOWLEDGE_BASE:
            assert "id" in entry
            assert "topic" in entry
            assert "text" in entry
            assert "source" in entry
            assert len(entry["keywords"]) > 0

    def test_explain_sync_returns_structured_schema(self):
        """Verify synchronous explain returns all prompt-engineered schema fields."""
        res = rag_service.explain("Document is expired and past valid date")
        assert res["rule_id"] == "kb_001"
        assert res["topic"] == "expiry"
        assert "summary" in res and len(res["summary"]) > 0
        assert "risk_analysis" in res and len(res["risk_analysis"]) > 0
        assert "officer_recommendation" in res and len(res["officer_recommendation"]) > 0
        assert "explanation" in res
        assert "source" in res
        assert "model" in res
        assert res["relevance_score"] > 0

    def test_tampering_flag_grounding(self):
        """Verify tampering flags ground to anti-tampering standards with forensic guidance."""
        context = {
            "document_id": "DOC-TEST-001",
            "document_type": "passport",
            "tampering_flagged": True,
            "tampering_score": 0.42
        }
        res = rag_service.explain("High tampering risk detected with copy-move clone", context=context)
        assert res["rule_id"] == "kb_007"
        assert "manipulation" in res["summary"].lower() or "tampering" in res["summary"].lower()
        assert "officer_recommendation" in res
        assert "relevance_score" in res

    def test_face_mismatch_grounding(self):
        """Verify face verification mismatch triggers biometric standard and recapture action."""
        context = {
            "document_id": "DOC-TEST-002",
            "document_type": "passport",
            "face_match": False
        }
        res = rag_service.explain("Low face similarity score between document and selfie", context=context)
        assert res["rule_id"] == "kb_008"
        assert "face" in res["topic"] or "biometric" in res["summary"].lower()
        assert len(res["officer_recommendation"]) > 0

    @pytest.mark.anyio
    async def test_explain_async_and_batch(self):
        """Verify asynchronous explain_all_flags_async runs concurrently with context."""
        flags = [
            "Document is expired and passed validity",
            "Digital editing detected in portrait area",
            "Indian passport number format mismatch"
        ]
        context = {
            "document_id": "DOC-ASYNC-99",
            "document_type": "passport",
            "ocr_confidence": 65
        }
        results = await rag_service.explain_all_flags_async(flags, context=context)
        assert len(results) == 3
        rule_ids = [r["rule_id"] for r in results]
        assert "kb_001" in rule_ids
        assert "kb_007" in rule_ids
        assert "kb_002" in rule_ids

        for r in results:
            assert r["summary"]
            assert r["risk_analysis"]
            assert r["officer_recommendation"]

    def test_empty_query_safe_handling(self):
        """Verify safe handling of empty or blank query strings."""
        res = rag_service.explain("")
        assert "rule_id" in res
        assert "summary" in res
        assert "officer_recommendation" in res
