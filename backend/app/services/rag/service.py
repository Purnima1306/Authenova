"""
RAG Explanation Service
Retrieves grounded, standards-based explanations for flagged verification issues.
Uses semantic vector search when sentence-transformers is installed, with an
optimized TF-IDF cosine similarity fallback for lightweight execution.
"""
import re
import math
from typing import Dict, Any, List, Tuple

# Curated Regulatory & Verification Knowledge Base
KNOWLEDGE_BASE = [
    {
        "id": "kb_001",
        "topic": "expiry",
        "keywords": ["expired", "expiry", "lapsed", "date of expiry", "valid upto"],
        "text": "A document is considered expired if its expiry date is earlier than or equal to the current date. Expired documents should be flagged as high risk, as they are no longer legally valid for identity verification."
    },
    {
        "id": "kb_002",
        "topic": "passport_format",
        "keywords": ["passport", "format", "number", "digits", "uppercase", "letter"],
        "text": "Indian passport numbers follow the format of one uppercase letter followed by seven digits (e.g. M1234567). A passport number that does not match this pattern indicates a possible OCR error or a forged document."
    },
    {
        "id": "kb_003",
        "topic": "aadhaar_format",
        "keywords": ["aadhaar", "12 digits", "format", "uidai"],
        "text": "Aadhaar numbers are exactly 12 digits with no letters. Any deviation from this format, such as extra characters or incorrect length, should be treated as invalid."
    },
    {
        "id": "kb_004",
        "topic": "visa_format",
        "keywords": ["visa", "permit", "pattern", "standard"],
        "text": "Visa and permit numbers are issued according to country-specific standards. Deviation from expected alphanumeric patterns suggests data entry error or unauthorized modification."
    },
    {
        "id": "kb_005",
        "topic": "completeness",
        "keywords": ["missing", "required", "field", "unreadable", "empty"],
        "text": "A missing required field, such as name, date of birth, or document number, significantly reduces confidence in the document's completeness and warrants officer review."
    },
    {
        "id": "kb_006",
        "topic": "ocr_confidence",
        "keywords": ["ocr", "confidence", "low confidence", "text extraction"],
        "text": "Low OCR confidence on critical identity fields suggests the extracted text may be inaccurate due to tilt, blur, or glare, and downstream validation results should be treated with caution."
    },
    {
        "id": "kb_007",
        "topic": "tampering",
        "keywords": ["tampering", "digital editing", "ela", "copy-move", "recompression", "manipulation"],
        "text": "An elevated tampering detection score indicates evidence of digital editing such as photo replacement, text alteration, or duplicated visual regions, requiring close manual scrutiny."
    },
    {
        "id": "kb_008",
        "topic": "face_verification",
        "keywords": ["face", "similarity", "mismatch", "selfie", "impersonation", "photo"],
        "text": "A low face similarity score between the document photo and the presented selfie suggests the presenter may not match the identity shown on the credential, indicating potential impersonation."
    },
    {
        "id": "kb_009",
        "topic": "date_of_birth",
        "keywords": ["date of birth", "dob", "future", "past"],
        "text": "Date of birth must always be a date in the past. A date of birth that is today or in the future is logically invalid and indicates either a scanning anomaly or a counterfeit document."
    },
    {
        "id": "kb_010",
        "topic": "document_type",
        "keywords": ["document type", "unrecognized", "unsupported", "unknown"],
        "text": "Document types are limited to a known, recognized set (passport, visa, aadhaar, permit). An unrecognized document type indicates an unsupported credential or invalid template."
    }
]


class RagExplanationService:
    """Semantic retrieval of grounded explanations for verification findings."""

    def __init__(self):
        self.model = None
        self._try_load_model()
        self._init_tfidf_fallback()

    def _try_load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            for entry in KNOWLEDGE_BASE:
                entry["embedding"] = self.model.encode(entry["text"])
        except Exception:
            self.model = None

    def _init_tfidf_fallback(self):
        """Prepare vocabulary and word vectors for fast fallback retrieval."""
        all_words = set()
        for entry in KNOWLEDGE_BASE:
            words = re.findall(r"\w+", (entry["text"] + " " + " ".join(entry["keywords"])).lower())
            all_words.update(words)
        self.vocab = sorted(list(all_words))
        self.word2idx = {w: i for i, w in enumerate(self.vocab)}

        self.kb_vectors = []
        for entry in KNOWLEDGE_BASE:
            vec = [0.0] * len(self.vocab)
            text_tokens = re.findall(r"\w+", (entry["text"] + " " + " ".join(entry["keywords"])).lower())
            for t in text_tokens:
                if t in self.word2idx:
                    vec[self.word2idx[t]] += 1.0
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            self.kb_vectors.append(vec)

    def _retrieve_tfidf(self, query: str) -> Tuple[Dict[str, Any], float]:
        q_vec = [0.0] * len(self.vocab)
        tokens = re.findall(r"\w+", query.lower())
        for t in tokens:
            if t in self.word2idx:
                q_vec[self.word2idx[t]] += 1.0
        q_norm = math.sqrt(sum(x * x for x in q_vec))
        if q_norm == 0:
            return KNOWLEDGE_BASE[0], 0.5
        q_vec = [x / q_norm for x in q_vec]

        best_score = -1.0
        best_entry = KNOWLEDGE_BASE[0]
        for i, entry in enumerate(KNOWLEDGE_BASE):
            score = sum(a * b for a, b in zip(q_vec, self.kb_vectors[i]))
            if score > best_score:
                best_score = score
                best_entry = entry

        return best_entry, round(max(0.1, best_score), 4)

    def explain(self, query_text: str) -> Dict[str, Any]:
        """
        Takes a flagged issue or reason and retrieves the best matching grounded rule.
        """
        if not query_text or not query_text.strip():
            return {
                "rule_id": "kb_005",
                "explanation": "No specific query provided.",
                "source": "Authenova Standard Verification Criteria",
                "relevance_score": 0.0
            }

        if self.model is not None and "embedding" in KNOWLEDGE_BASE[0]:
            try:
                from sentence_transformers import util
                q_emb = self.model.encode(query_text)
                best_entry = None
                best_score = -1.0
                for entry in KNOWLEDGE_BASE:
                    sim = util.cos_sim(q_emb, entry["embedding"]).item()
                    if sim > best_score:
                        best_score = sim
                        best_entry = entry
                return {
                    "rule_id": best_entry["id"],
                    "explanation": f"Regarding flagged issue: {best_entry['text']}",
                    "source": "ICAO / National Identity Standards Reference Rule",
                    "relevance_score": round(best_score, 4)
                }
            except Exception:
                pass

        # Fallback
        entry, score = self._retrieve_tfidf(query_text)
        return {
            "rule_id": entry["id"],
            "explanation": f"Standard criterion: {entry['text']}",
            "source": "Authenova Document Verification Guidelines",
            "relevance_score": score
        }

    def explain_all_flags(self, flagged_reasons: List[str]) -> List[Dict[str, Any]]:
        """Explain a collection of flagged reasons."""
        explanations = []
        for reason in flagged_reasons:
            if reason and reason.strip():
                explanations.append(self.explain(reason.strip()))
        return explanations


# Singleton instance
rag_service = RagExplanationService()
