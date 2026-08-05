"""Contract text extraction service.

Deterministic keyword/regex-based extraction that identifies candidate
contract terms from pasted text. This is the no-API-key fallback; the same
interface (``extract_terms``) can later be backed by an LLM. Either way the
output is a DRAFT requiring human validation - extracted terms are created
with status "Inferred" and low confidence, never "Confirmed".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class ExtractedTerm:
    category: str
    term_name: str
    value: str
    evidence: str
    confidence: str = "Low"
    status: str = "Inferred"


# (category, term_name, regex) - regexes deliberately generous; humans review.
PATTERNS = [
    ("Pricing", "payment_terms_days",
     r"(?:net|payment terms? of)\s+(\d{2,3})\s*(?:days)?"),
    ("Pricing", "annual_productivity_pct",
     r"(?:annual (?:price|productivity) (?:reduction|improvement)[^.\d]{0,40})(\d+(?:\.\d+)?)\s*%"),
    ("Volume", "minimum_annual_volume_units",
     r"minimum (?:annual )?(?:volume|purchase|quantity)[^.\d]{0,40}([\d,]+)\s*(?:units)?"),
    ("Inventory & liability", "ncnr_liability_window_days",
     r"(?:non-?cancel(?:l)?able|NCNR)[^.\d]{0,60}(\d{2,3})\s*days?"),
    ("Inventory & liability", "material_authorization_window_days",
     r"material authorization[^.\d]{0,60}(\d{2,3})\s*days?"),
    ("Inventory & liability", "advance_payment_pct",
     r"(?:advance payment|deposit)[^.\d]{0,40}(\d+(?:\.\d+)?)\s*%"),
    ("Service", "required_otd_pct",
     r"on-?time delivery[^.\d]{0,40}(\d{2}(?:\.\d+)?)\s*%"),
    ("Service", "required_lead_time_days",
     r"lead time[^.\d]{0,40}(\d{1,3})\s*days?"),
    ("Quality", "first_pass_yield_commitment_pct",
     r"(?:first[- ]pass yield|FPY)[^.\d]{0,40}(\d{2}(?:\.\d+)?)\s*%"),
    ("Contract risk", "termination_notice_days",
     r"termination[^.\d]{0,60}(\d{2,3})\s*days?(?:[^.]{0,20}notice)?"),
]

KEYWORD_FLAGS = [
    ("Inventory & liability", "consignment_language",
     ["consign", "consigned", "consignment"]),
    ("Inventory & liability", "title_transfer_language",
     ["title transfer", "title shall pass", "transfer of title", "fob", "fca", "exw", "ddp"]),
    ("Inventory & liability", "vmi_language",
     ["vendor-managed", "vendor managed", "vmi"]),
    ("Cost transparency", "open_book_language",
     ["open-book", "open book", "cost breakdown", "audit right"]),
    ("Contract risk", "tooling_ownership_language",
     ["tooling", "fixtures", "test equipment ownership"]),
    ("Quality", "warranty_language", ["warranty", "epidemic failure", "field failure"]),
    ("Volume", "take_or_pay_language", ["take-or-pay", "take or pay", "capacity reservation"]),
]


def extract_terms(text: str) -> List[ExtractedTerm]:
    """Extract candidate terms. AI-free deterministic implementation."""
    results: List[ExtractedTerm] = []
    if not text or not text.strip():
        return results
    lowered = text.lower()

    for category, term_name, pattern in PATTERNS:
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            start = max(match.start() - 60, 0)
            end = min(match.end() + 60, len(text))
            results.append(ExtractedTerm(
                category=category,
                term_name=term_name,
                value=match.group(1).replace(",", ""),
                evidence="..." + text[start:end].strip() + "...",
            ))

    for category, term_name, keywords in KEYWORD_FLAGS:
        for kw in keywords:
            idx = lowered.find(kw)
            if idx >= 0:
                start = max(idx - 60, 0)
                end = min(idx + len(kw) + 60, len(text))
                results.append(ExtractedTerm(
                    category=category,
                    term_name=term_name,
                    value=f"Detected: '{kw}'",
                    evidence="..." + text[start:end].strip() + "...",
                ))
                break
    return results
