"""Secret and credential rule (FR-11). SCRUM-46.

High confidence for formats that are almost never anything else (AWS access key IDs, private-key
blocks, live provider tokens); lower confidence for "password = ..." style assignments, which are
often placeholders. Placeholders and environment-variable references are ignored.
Bounded quantifiers only (ReDoS, threat T-18).
"""

from __future__ import annotations

import re

from securewaste.core.detection.catalogue import Category
from securewaste.core.detection.models import Candidate
from securewaste.core.detection.rules.base import DetectionRule
from securewaste.core.extraction import PageText

# Publicly documented AWS examples (AWS docs), never real credentials.
KNOWN_EXAMPLES = frozenset({"AKIAIOSFODNN7EXAMPLE", "AKIAEXAMPLEKEY12345"})
_PLACEHOLDER = re.compile(r"(?i)example|placeholder|dummy|fake|sample|changeme|your[_-]|<|\*{3}|x{6}|\$\{|%\(")
_ENV_REFERENCE = re.compile(r"(?i)^(?:os\.environ|os\.getenv|process\.env|env\(|getenv)")

# (pattern, confidence, value group). Group 0 = whole match is the secret.
_PATTERNS: tuple[tuple[re.Pattern[str], float, int], ...] = (
    (re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Z0-9])"), 0.95, 0),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"), 0.95, 0),
    (re.compile(r"(?<![\w-])(?:sk|rk)_live_[A-Za-z0-9]{16,99}"), 0.95, 0),
    (re.compile(r"(?<![\w-])gh[pousr]_[A-Za-z0-9]{36,255}"), 0.95, 0),
    (re.compile(r"(?<![\w-])xox[abpr]-[A-Za-z0-9-]{10,200}"), 0.9, 0),
    (re.compile(r"(?i)[a-z][a-z0-9+.-]{1,20}://[^\s:/@]{1,64}:([^\s@/]{6,128})@"), 0.9, 1),  # creds in URL
    (
        re.compile(
            r"(?i)(?<![\w-])(?:password|passwd|pwd|api[_ -]?key|secret(?:[_ -]?key)?|access[_ -]?token|auth[_ -]?token)"
            r"\s{0,3}[:=]\s{0,3}[\"']?([^\s\"']{8,128})"
        ),
        0.8,
        1,
    ),
)


class SecretRule(DetectionRule):
    rule_id = "secret.pattern"
    category = Category.SECRET
    base_confidence = 0.8
    context_words = ("password", "token", "secret", "key", "credential")

    def find(self, page: PageText) -> list[Candidate]:
        found: dict[tuple[int, int], Candidate] = {}
        for pattern, confidence, group in _PATTERNS:
            for m in pattern.finditer(page.text):
                value = m.group(group)
                if value in KNOWN_EXAMPLES or _PLACEHOLDER.search(value) or _ENV_REFERENCE.match(value):
                    continue
                span = m.span(group)
                if span not in found or found[span].confidence < confidence:
                    found[span] = Candidate(
                        rule_id=self.rule_id,
                        category=self.category,
                        page_number=page.page_number,
                        char_start=span[0],
                        char_end=span[1],
                        raw_value=value,
                        confidence=confidence,
                    )
        return sorted(found.values(), key=lambda c: c.char_start)
