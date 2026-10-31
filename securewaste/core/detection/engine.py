"""Detection engine (FR-08 → FR-13). Owner: Milestone 1 issue #5."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from securewaste.core.detection.catalogue import ReviewStatus, Severity
from securewaste.core.detection.masking import mask, value_hmac
from securewaste.core.detection.models import Candidate, Finding
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText


class DetectionEngine:
    """Orchestrates detection rules across pages.

    Responsibilities:
    - Run each rule on each page
    - Filter by min_confidence
    - Merge duplicates (same value, rule, page)
    - Apply masking and HMAC
    - Attach catalogue metadata (severity, explanation, recommendation)
    """

    def __init__(self, rules: list[DetectionRule], min_confidence: float, hmac_key: bytes):
        self.rules = rules
        self.min_confidence = min_confidence
        self.hmac_key = hmac_key

    def scan(self, pages: list[PageText]) -> list[Finding]:
        """Run every rule on every page, drop low confidence, merge duplicates, mask values."""
        # Collect all candidates from all rules on all pages
        all_candidates: list[Candidate] = []

        for page in pages:
            for rule in self.rules:
                candidates = rule.find(page)
                all_candidates.extend(candidates)

        # Filter by minimum confidence
        filtered = [c for c in all_candidates if c.confidence >= self.min_confidence]

        # Merge duplicates: same rule_id, same normalized value, same page
        merged = self._merge_duplicates(filtered)

        # Convert to Findings with masking and HMAC
        findings = []
        for candidate in merged:
            finding = self._candidate_to_finding(candidate)
            findings.append(finding)

        return findings

    def _merge_duplicates(self, candidates: list[Candidate]) -> list[Candidate]:
        """Merge candidates with same rule_id, normalized value, and page_number.

        Uses value_hmac for comparison to avoid storing raw values.
        Keeps the candidate with highest confidence.
        """
        # Group by (rule_id, page_number, hmac)
        groups: dict[tuple[str, int, str], list[Candidate]] = defaultdict(list)

        for candidate in candidates:
            hmac_val = value_hmac(self.hmac_key, candidate.rule_id, candidate.raw_value)
            key = (candidate.rule_id, candidate.page_number, hmac_val)
            groups[key].append(candidate)

        merged = []
        for group in groups.values():
            # Keep highest confidence
            best = max(group, key=lambda c: c.confidence)
            # Sum occurrences
            total_occurrences = sum(c.occurrences for c in group)
            # Merge character spans (min start, max end)
            min_start = min(c.char_start for c in group)
            max_end = max(c.char_end for c in group)

            merged.append(
                replace(
                    best,
                    char_start=min_start,
                    char_end=max_end,
                    occurrences=total_occurrences,
                )
            )

        return merged

    def _candidate_to_finding(self, candidate: Candidate) -> Finding:
        """Convert a Candidate to a Finding with masking, HMAC, and catalogue data."""
        from securewaste.core.detection.catalogue import CATALOGUE

        cat_info = CATALOGUE.get(candidate.category)
        if cat_info:
            severity = cat_info.severity
            explanation = cat_info.explanation
            recommendation = cat_info.recommendation
        else:
            severity = Severity.INFORMATIONAL
            explanation = ""
            recommendation = ""

        masked_value = mask(candidate.category, candidate.raw_value)
        val_hmac = value_hmac(self.hmac_key, candidate.rule_id, candidate.raw_value)

        # Build context snippet (±30 chars, with detected values masked)
        context = self._build_context(candidate)

        return Finding(
            rule_id=candidate.rule_id,
            category=candidate.category,
            severity=severity,
            confidence=candidate.confidence,
            page_number=candidate.page_number,
            char_start=candidate.char_start,
            char_end=candidate.char_end,
            masked_value=masked_value,
            value_hmac=val_hmac,
            context=context,
            explanation=explanation,
            recommendation=recommendation,
            occurrences=candidate.occurrences,
            validation=candidate.validation,
            review_status=ReviewStatus.OPEN,
            id=None,  # Set when persisted
        )

    def _build_context(self, candidate: Candidate) -> str:
        """Build context snippet around the candidate, masking all detected values."""
        # This is a simplified version - in production, we'd mask all findings in the window
        # For now, just get ±30 chars around the match
        # The page text isn't available here, so we return a placeholder
        # The actual context building with masking happens in the service layer
        return f"[context for {candidate.rule_id} on page {candidate.page_number}]"
