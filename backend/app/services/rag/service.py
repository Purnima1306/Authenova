"""
RAG Explanation Service with LLM Integration & Prompt Engineering
Retrieves grounded, standards-based rules for flagged verification issues,
then uses prompt-engineered LLMs (Google Gemini, OpenAI, or local endpoints)
to synthesize audit-ready explanations, risk analyses, and actionable officer recommendations.
Includes a deterministic offline synthesizer fallback for zero-dependency operation.
"""
import os
import re
import json
import math
import logging
import asyncio
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger("authenova.rag")

# ==============================================================================
# 1. Curated Regulatory & Verification Standards Knowledge Base
# ==============================================================================
KNOWLEDGE_BASE = [
    {
        "id": "kb_001",
        "topic": "expiry",
        "keywords": ["expired", "expiry", "lapsed", "date of expiry", "valid upto"],
        "source": "ICAO Doc 9303 Part 3 & National Identity Regulations",
        "text": "A document is considered expired if its expiry date is earlier than or equal to the current date. Expired documents should be flagged as high risk, as they are no longer legally valid for identity verification."
    },
    {
        "id": "kb_002",
        "topic": "passport_format",
        "keywords": ["passport", "format", "number", "digits", "uppercase", "letter"],
        "source": "ICAO Doc 9303 & Indian Passports Act Guidelines",
        "text": "Indian passport numbers follow the format of one uppercase letter followed by seven digits (e.g. M1234567). A passport number that does not match this pattern indicates a possible OCR error or a forged document."
    },
    {
        "id": "kb_003",
        "topic": "aadhaar_format",
        "keywords": ["aadhaar", "12 digits", "format", "uidai"],
        "source": "UIDAI Aadhaar Technical & Validation Standard",
        "text": "Aadhaar numbers are exactly 12 digits with no letters. Any deviation from this format, such as extra characters or incorrect length, should be treated as invalid."
    },
    {
        "id": "kb_004",
        "topic": "visa_format",
        "keywords": ["visa", "permit", "pattern", "standard"],
        "source": "ICAO MRTD Standards & National Immigration Regulations",
        "text": "Visa and permit numbers are issued according to country-specific standards. Deviation from expected alphanumeric patterns suggests data entry error or unauthorized modification."
    },
    {
        "id": "kb_005",
        "topic": "completeness",
        "keywords": ["missing", "required", "field", "unreadable", "empty"],
        "source": "ICAO Doc 9303 Part 4 Minimum Mandatory Data Set Standard",
        "text": "A missing required field, such as name, date of birth, or document number, significantly reduces confidence in the document's completeness and warrants officer review."
    },
    {
        "id": "kb_006",
        "topic": "ocr_confidence",
        "keywords": ["ocr", "confidence", "low confidence", "text extraction"],
        "source": "NIST SP 800-63A Digital Identity Guidelines (Enrollment Confidence)",
        "text": "Low OCR confidence on critical identity fields suggests the extracted text may be inaccurate due to tilt, blur, or glare, and downstream validation results should be treated with caution."
    },
    {
        "id": "kb_007",
        "topic": "tampering",
        "keywords": ["tampering", "digital editing", "ela", "copy-move", "recompression", "manipulation"],
        "source": "ISO/IEC 19794 Anti-Tampering & Image Forensics Standards",
        "text": "An elevated tampering detection score indicates evidence of digital editing such as photo replacement, text alteration, or duplicated visual regions, requiring close manual scrutiny."
    },
    {
        "id": "kb_008",
        "topic": "face_verification",
        "keywords": ["face", "similarity", "mismatch", "selfie", "impersonation", "photo"],
        "source": "ISO/IEC 19794-5 Biometric Data Interchange Formats (Face Image Data)",
        "text": "A low face similarity score between the document photo and the presented selfie suggests the presenter may not match the identity shown on the credential, indicating potential impersonation."
    },
    {
        "id": "kb_009",
        "topic": "date_of_birth",
        "keywords": ["date of birth", "dob", "future", "past"],
        "source": "ICAO 9303 Standard Validation Rule (Chronological Validity)",
        "text": "Date of birth must always be a date in the past. A date of birth that is today or in the future is logically invalid and indicates either a scanning anomaly or a counterfeit document."
    },
    {
        "id": "kb_010",
        "topic": "document_type",
        "keywords": ["document type", "unrecognized", "unsupported", "unknown", "mismatch"],
        "source": "ICAO Doc 9303 Machine Readable Travel Document Classification",
        "text": "Document types are limited to a known, recognized set (passport, visa, aadhaar, permit). An unrecognized document type indicates an unsupported credential or invalid template."
    }
]

# ==============================================================================
# 2. Prompt Engineering Specifications & Few-Shot Templates
# ==============================================================================
SYSTEM_PROMPT = """You are the Senior Compliance Officer and Identity Forensics Analyst at Authenova.
Your duty is to generate rigorous, audit-grade verification assessments for flagged document anomalies.
You are provided with:
1. Observed Document Finding & Context (Document ID, Document Type, Extraction Confidence, Tampering/Biometric Signals).
2. Retrieved Grounded Regulatory Standard (from ICAO Doc 9303, ISO/IEC, NIST, or National Authorities).

### STRICT INSTRUCTIONS:
1. GROUNDING MANDATE: Ground your assessment strictly in the provided regulatory standard and observed signals. Never hallucinate non-existent rules or speculate on unobserved facts.
2. PROFESSIONAL TONE: Authoritative, objective, risk-aware, and forensic.
3. OUTPUT FORMAT: Respond ONLY with a valid, clean JSON object (no markdown fences, no explanatory preambles) containing exactly these three keys:
   - "summary": A concise 1-sentence finding statement referencing the standard.
   - "risk_analysis": 1-2 clear sentences explaining the legal, operational, or fraud risk (e.g. impersonation, counterfeit credential, expired legal validity).
   - "officer_recommendation": Actionable step-by-step guidance for the reviewing officer (e.g. secondary tactile/UV check, biometric re-capture, manual MRZ calculation).
"""

FEW_SHOT_EXAMPLES = [
    {
        "input": (
            "Flag: High tampering risk (probability of digital editing).\n"
            "Document Type: passport | Extraction Confidence: 72%\n"
            "Grounded Standard [kb_007]: An elevated tampering detection score indicates evidence of digital editing such as photo replacement, text alteration, or duplicated visual regions."
        ),
        "output": {
            "summary": "Document exhibits visual manipulation indicators violating anti-tampering integrity standards.",
            "risk_analysis": "Detected digital editing artifacts in critical zones indicate high probability of credential forgery, unauthorized photo substitution, or metadata alteration.",
            "officer_recommendation": "Inspect physical document under oblique and UV illumination for surface tampering, laminate disturbance, or misaligned typeface. Request primary document re-submission if physical document is unavailable."
        }
    },
    {
        "input": (
            "Flag: Low face similarity score between document and selfie.\n"
            "Document Type: passport | Extraction Confidence: 85%\n"
            "Grounded Standard [kb_008]: A low face similarity score between the document photo and the presented selfie suggests the presenter may not match the identity shown on the credential."
        ),
        "output": {
            "summary": "Biometric 1:1 facial comparison failed the minimum match threshold against the presented credential.",
            "risk_analysis": "Significant geometric facial disparity indicates elevated risk of identity fraud or synthetic persona impersonation.",
            "officer_recommendation": "Require live biometric re-verification with active liveness challenge and capture under controlled, diffuse lighting; verify identity via secondary government database."
        }
    }
]


class RagExplanationService:
    """
    Semantic retrieval of grounded standards paired with LLM prompt-engineered synthesis.
    Supports Google Gemini, OpenAI, custom endpoints, and an offline synthesizer fallback.
    """

    def __init__(self):
        self.model = None
        self._try_load_model()
        self._init_tfidf_fallback()

        # LLM Provider Configuration
        self.groq_api_key = os.environ.get("GROQ_API_KEY")
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.llm_api_base = os.environ.get("LLM_API_BASE")
        self.default_model = os.environ.get("LLM_MODEL_NAME")

        if self.groq_api_key or (self.openai_api_key and self.openai_api_key.startswith("gsk_")):
            self.provider = "groq"
            self.groq_api_key = self.groq_api_key or self.openai_api_key
            self.model_name = self.default_model or "qwen/qwen3.8-27b"
            self.llm_api_base = "https://api.groq.com/openai/v1"
        elif self.gemini_api_key:
            self.provider = "gemini"
            self.model_name = self.default_model or "gemini-1.5-flash"
        elif self.openai_api_key or self.llm_api_base:
            self.provider = "openai"
            self.model_name = self.default_model or "gpt-4o-mini"
        else:
            self.provider = "synthesizer"
            self.model_name = "authenova-rules-synthesizer"

        logger.info(
            "RagExplanationService initialized with provider '%s' (model: %s)",
            self.provider, self.model_name
        )

    # --------------------------------------------------------------------------
    # Retrieval Layer: Semantic Embeddings & TF-IDF Fallback
    # --------------------------------------------------------------------------
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

    def _retrieve_best_rule(self, query: str) -> Tuple[Dict[str, Any], float]:
        """Retrieve the most relevant regulatory rule using embeddings or TF-IDF."""
        if not query or not query.strip():
            return KNOWLEDGE_BASE[4], 0.1

        # 1. Semantic Embedding Search
        if self.model is not None and "embedding" in KNOWLEDGE_BASE[0]:
            try:
                from sentence_transformers import util
                q_emb = self.model.encode(query)
                best_entry = None
                best_score = -1.0
                for entry in KNOWLEDGE_BASE:
                    sim = util.cos_sim(q_emb, entry["embedding"]).item()
                    if sim > best_score:
                        best_score = sim
                        best_entry = entry
                return best_entry, round(max(0.1, best_score), 4)
            except Exception as e:
                logger.debug("Semantic embedding retrieval error: %s", e)

        # 2. Fast TF-IDF Fallback
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

    # --------------------------------------------------------------------------
    # Prompt Construction
    # --------------------------------------------------------------------------
    def _build_user_prompt(
        self,
        flag_query: str,
        rule: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Construct the prompt-engineered query injecting grounded rule and document signals."""
        ctx = context or {}
        doc_type = ctx.get("document_type", "unspecified identity document")
        doc_id = ctx.get("document_id", "N/A")
        ocr_conf = ctx.get("ocr_confidence", "N/A")
        tampering = "Flagged / Elevated Manipulation Probability" if ctx.get("tampering_flagged") else "Normal"
        face_match = "Mismatch" if ctx.get("face_match") is False else ("Match" if ctx.get("face_match") is True else "Skipped/Not provided")

        prompt = (
            f"EVALUATE THE FOLLOWING VERIFICATION FINDING:\n\n"
            f"[DOCUMENT SIGNALS]\n"
            f"- Document ID: {doc_id}\n"
            f"- Document Type: {doc_type}\n"
            f"- Observed Flag / Anomaly: {flag_query}\n"
            f"- Extraction Confidence: {ocr_conf}%\n"
            f"- Tampering Indicator: {tampering}\n"
            f"- Biometric Verification: {face_match}\n\n"
            f"[GROUNDED REGULATORY STANDARD]\n"
            f"- Standard Identifier: {rule['id']}\n"
            f"- Topic: {rule['topic']}\n"
            f"- Reference Authority: {rule.get('source', 'Authenova Regulatory Standards')}\n"
            f"- Mandatory Criterion: \"{rule['text']}\"\n\n"
            f"Generate the audit-grade JSON output with keys: \"summary\", \"risk_analysis\", \"officer_recommendation\"."
        )
        return prompt

    # --------------------------------------------------------------------------
    # Deterministic Contextual Synthesizer (Offline / Zero-Dependency Fallback)
    # --------------------------------------------------------------------------
    def _synthesize_offline(
        self,
        flag_query: str,
        rule: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Prompt-engineered deterministic synthesizer producing consistent, audit-ready
        explanations without external API dependencies.
        """
        ctx = context or {}
        doc_type = ctx.get("document_type", "document").capitalize()
        topic = rule.get("topic", "compliance")

        synthesis_table = {
            "expiry": {
                "summary": f"{doc_type} failed temporal validity check under {rule['id']}; document has lapsed or passed expiry threshold.",
                "risk_analysis": "Operating with an expired credential invalidates legal authentication and presents substantial compliance risk under immigration and KYC regulations.",
                "officer_recommendation": "Reject credential as expired. Instruct applicant to present an active, unexpired government-issued photo identity."
            },
            "passport_format": {
                "summary": f"Credential identifier deviates from standardized {doc_type} numbering conventions ({rule['id']}).",
                "risk_analysis": "Incorrect character counts or alphanumeric structures suggest optical distortion, transcription failure, or forged passport metadata.",
                "officer_recommendation": "Cross-reference the visual zone against the Machine Readable Zone (MRZ) checksum lines. If mismatch persists, require physical document review."
            },
            "aadhaar_format": {
                "summary": f"UIDAI format violation detected under {rule['id']}; number does not conform to exact 12-digit standard.",
                "risk_analysis": "Non-compliant Aadhaar numbering indicates invalid identification data, counterfeit cards, or OCR character segmentation error.",
                "officer_recommendation": "Verify number format with applicant or request masked e-Aadhaar with verifiable cryptographic QR code."
            },
            "visa_format": {
                "summary": f"Visa endorsement structure deviates from standard consular issuance pattern ({rule['id']}).",
                "risk_analysis": "Malformed visa registration codes carry severe regulatory risk of unauthorized travel permissions or altered endorsements.",
                "officer_recommendation": "Cross-check visa number against issuing authority registry and inspect border entry stamps."
            },
            "completeness": {
                "summary": f"Critical mandatory identity fields are missing or unreadable under {rule['id']}.",
                "risk_analysis": "Incomplete identity credentials prevent full 4-eye verification and compromise audit trail integrity.",
                "officer_recommendation": "Examine document image for severe crop, glare, or occlusions. Request a clear, high-resolution re-scan with all 4 document borders visible."
            },
            "ocr_confidence": {
                "summary": f"Low optical character extraction confidence recorded across primary identity fields ({rule['id']}).",
                "risk_analysis": "Sub-threshold OCR confidence elevates probability of misread names, dates, or serial numbers, impeding automated validation.",
                "officer_recommendation": "Perform manual key-from-image verification of suspect fields or request image capture under diffuse, non-reflective illumination."
            },
            "tampering": {
                "summary": f"Digital image forensic analysis detected tampering, copy-move duplicates, or compression anomalies ({rule['id']}).",
                "risk_analysis": "Forensic anomalies indicate probable image manipulation, such as portrait substitution, altered dates, or cloned security patterns.",
                "officer_recommendation": "Flag for Level 2 Fraud Investigation. Inspect physical substrate under UV and side lighting for laminate lifting or ink discrepancies."
            },
            "face_verification": {
                "summary": f"Presented selfie does not match the portrait extracted from the {doc_type} ({rule['id']}).",
                "risk_analysis": "Low biometric similarity score indicates high risk of identity impersonation, presenter spoofing, or fraudulent document presentation.",
                "officer_recommendation": "Require live biometric recapture with active 3D liveness challenge. Escalate to supervisor if facial divergence persists."
            },
            "date_of_birth": {
                "summary": f"Date of birth violates chronological reality constraints under {rule['id']}.",
                "risk_analysis": "A future or logically impossible birth date indicates an artificial test document, algorithmic extraction hallucination, or fraudulent printing.",
                "officer_recommendation": "Manually verify the printed date against MRZ character positions 14-19 (YYMMDD format)."
            },
            "document_type": {
                "summary": f"Document visual layout does not match expected template specifications for {doc_type} ({rule['id']}).",
                "risk_analysis": "Structural layout misalignment indicates an unsupported document format, obsolete revision, or fabricated identity card template.",
                "officer_recommendation": "Verify that the submitted credential matches accepted national identity document types for this workflow."
            }
        }

        entry = synthesis_table.get(topic, {
            "summary": f"Verification anomaly detected against standard {rule['id']}: {flag_query}.",
            "risk_analysis": f"Finding deviates from {rule.get('source', 'compliance guidelines')} and represents an elevated identity verification risk.",
            "officer_recommendation": f"Refer to {rule.get('source', 'standard guidelines')} and perform secondary officer review."
        })
        return entry

    # --------------------------------------------------------------------------
    # External LLM Calls (Gemini & OpenAI)
    # --------------------------------------------------------------------------
    async def _call_gemini_async(self, user_prompt: str) -> Optional[Dict[str, str]]:
        """Call Google Gemini REST API using prompt engineering."""
        if not self.gemini_api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{"parts": [{"text": user_prompt}]}],
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                        parsed = self._extract_json_response(text)
                        if parsed:
                            return parsed
                else:
                    logger.warning("Gemini API call returned status %d: %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.warning("Gemini API call failed (%s); falling back to offline synthesizer.", e)
        return None

    async def _call_groq_async(self, user_prompt: str) -> Optional[Dict[str, str]]:
        """Call Groq Cloud ultra-fast LPU API using prompt engineering."""
        if not self.groq_api_key:
            return None

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.groq_api_key}"
        }

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        parsed = self._extract_json_response(content)
                        if parsed:
                            return parsed
                else:
                    logger.warning("Groq API call returned status %d: %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.warning("Groq API call failed (%s); falling back to offline synthesizer.", e)
        return None

    async def _call_openai_async(self, user_prompt: str) -> Optional[Dict[str, str]]:
        """Call OpenAI-compatible REST API using prompt engineering."""
        if not self.openai_api_key and not self.llm_api_base:
            return None

        base_url = (self.llm_api_base or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.openai_api_key:
            headers["Authorization"] = f"Bearer {self.openai_api_key}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
            "response_format": {"type": "json_object"}
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        parsed = self._extract_json_response(content)
                        if parsed:
                            return parsed
                else:
                    logger.warning("OpenAI API call returned status %d: %s", response.status_code, response.text[:200])
        except Exception as e:
            logger.warning("OpenAI API call failed (%s); falling back to offline synthesizer.", e)
        return None

    def _extract_json_response(self, text: str) -> Optional[Dict[str, str]]:
        """Extract and sanitize structured JSON from model response."""
        try:
            clean = text.strip()
            # Remove markdown fences if model returned them
            if clean.startswith("```"):
                clean = re.sub(r"^```[a-zA-Z]*\n?", "", clean)
                clean = re.sub(r"\n?```$", "", clean).strip()
            data = json.loads(clean)
            if isinstance(data, dict) and "summary" in data:
                return {
                    "summary": str(data.get("summary", "")).strip(),
                    "risk_analysis": str(data.get("risk_analysis", "")).strip(),
                    "officer_recommendation": str(data.get("officer_recommendation", "")).strip()
                }
        except Exception as e:
            logger.debug("Failed to parse LLM JSON: %s", e)
        return None

    # --------------------------------------------------------------------------
    # Main Public Explanation Interface
    # --------------------------------------------------------------------------
    async def explain_async(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Asynchronously retrieves the grounded standard and synthesizes an audit-grade
        explanation via LLM prompt engineering with automatic fallback.
        """
        rule, score = self._retrieve_best_rule(query_text)
        user_prompt = self._build_user_prompt(query_text, rule, context)

        # Attempt LLM generation if configured
        llm_result = None
        used_model = self.model_name

        if self.provider == "groq":
            llm_result = await self._call_groq_async(user_prompt)
        elif self.provider == "gemini":
            llm_result = await self._call_gemini_async(user_prompt)
        elif self.provider == "openai":
            llm_result = await self._call_openai_async(user_prompt)

        # Fallback to deterministic prompt synthesizer if LLM not configured or failed
        if not llm_result:
            llm_result = self._synthesize_offline(query_text, rule, context)
            used_model = "authenova-rules-synthesizer"

        summary = llm_result.get("summary", "")
        risk_analysis = llm_result.get("risk_analysis", "")
        officer_rec = llm_result.get("officer_recommendation", "")

        # Unified single-string explanation for backwards compatibility
        composite_explanation = f"{summary} [Risk Analysis]: {risk_analysis} [Officer Action]: {officer_rec}"

        return {
            "rule_id": rule["id"],
            "topic": rule.get("topic", "compliance"),
            "summary": summary,
            "risk_analysis": risk_analysis,
            "officer_recommendation": officer_rec,
            "explanation": composite_explanation,
            "source": rule.get("source", "Authenova Document Verification Guidelines"),
            "relevance_score": score,
            "model": used_model
        }

    def explain(
        self,
        query_text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Synchronous explanation entry point.
        Uses cached/offline prompt synthesizer for instant synchronous responses.
        """
        rule, score = self._retrieve_best_rule(query_text)
        llm_result = self._synthesize_offline(query_text, rule, context)

        summary = llm_result.get("summary", "")
        risk_analysis = llm_result.get("risk_analysis", "")
        officer_rec = llm_result.get("officer_recommendation", "")
        composite_explanation = f"{summary} [Risk Analysis]: {risk_analysis} [Officer Action]: {officer_rec}"

        return {
            "rule_id": rule["id"],
            "topic": rule.get("topic", "compliance"),
            "summary": summary,
            "risk_analysis": risk_analysis,
            "officer_recommendation": officer_rec,
            "explanation": composite_explanation,
            "source": rule.get("source", "Authenova Document Verification Guidelines"),
            "relevance_score": score,
            "model": "authenova-rules-synthesizer"
        }

    async def explain_all_flags_async(
        self,
        flagged_reasons: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Explain a collection of flagged reasons concurrently via async LLM synthesis."""
        tasks = [
            self.explain_async(reason.strip(), context)
            for reason in flagged_reasons
            if reason and reason.strip()
        ]
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    def explain_all_flags(
        self,
        flagged_reasons: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Synchronous batch explanation for backward compatibility."""
        explanations = []
        for reason in flagged_reasons:
            if reason and reason.strip():
                explanations.append(self.explain(reason.strip(), context))
        return explanations


# Singleton instance
rag_service = RagExplanationService()
