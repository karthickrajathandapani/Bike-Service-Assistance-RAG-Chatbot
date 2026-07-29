"""
Fault diagnosis service: takes a plain-English symptom, retrieves relevant
troubleshooting context from the manual(s) via the hybrid retriever, and
asks the LLM to produce a ranked list of likely causes + suggested fixes
(grounded in the manual, via chains.answer_question-style flow but with a
diagnosis-specific prompt).
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.prompt import DIAGNOSIS_SYSTEM_PROMPT
from config.settings import ANTHROPIC_API_KEY, TOP_K_RETRIEVE, TOP_K_FINAL
from retrieval.hybrid_retriever import hybrid_search
from retrieval.reranker import rerank
from retrieval.citation import build_context_block, build_citations
from llm.llm import call_llm

# Simple keyword -> likely-cause fallback table, used when no LLM key is
# configured (or as a sanity backstop), based on common troubleshooting
# patterns for small-displacement motorcycles.
SYMPTOM_KEYWORDS = {
    "won't start": ["Battery", "Starter relay / starter motor", "Spark plug", "Fuel delivery / injector"],
    "wont start": ["Battery", "Starter relay / starter motor", "Spark plug", "Fuel delivery / injector"],
    "not starting": ["Battery", "Starter relay / starter motor", "Spark plug", "Fuel delivery / injector"],
    "overheating": ["Low coolant level", "Faulty radiator fan", "Blocked radiator", "Thermostat fault"],
    "won't shift": ["Clutch adjustment", "Shift pedal linkage", "Low engine oil"],
    "chain noise": ["Chain slack out of spec", "Dry/unlubricated chain", "Worn sprockets"],
    "brake spongy": ["Air in hydraulic brake line", "Low brake fluid", "Worn brake pads"],
}


def _fallback_causes(symptom: str):
    symptom_l = symptom.lower()
    for key, causes in SYMPTOM_KEYWORDS.items():
        if key in symptom_l:
            return causes
    return []


def diagnose(symptom: str, vehicle_key: Optional[str] = None) -> Dict:
    candidates = hybrid_search(symptom, top_k=TOP_K_RETRIEVE, vehicle_key=vehicle_key)
    top_chunks = rerank(symptom, candidates, top_k=TOP_K_FINAL)
    context_block = build_context_block(top_chunks)
    citations = build_citations(top_chunks)

    if not ANTHROPIC_API_KEY:
        fallback = _fallback_causes(symptom)
        answer = (
            "No ANTHROPIC_API_KEY configured, so here's a general checklist "
            "(add your key to .env for a manual-grounded diagnosis):\n- "
            + "\n- ".join(fallback or ["Unable to match a known symptom pattern."])
        )
        return {"symptom": symptom, "answer": answer, "citations": citations}

    system_prompt = DIAGNOSIS_SYSTEM_PROMPT.format(context=context_block or "(no relevant context found)")
    try:
        answer = call_llm(system=system_prompt, user_message=f"Symptom: {symptom}")
    except Exception as e:
        answer = f"Sorry, I couldn't generate a diagnosis right now ({e})."

    return {"symptom": symptom, "answer": answer, "citations": citations}
