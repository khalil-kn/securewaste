# ADR-0005: Rule-based detection with validators as the baseline

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

Detection must be explainable, testable and measurable. AI is an optional later milestone, and its value can only be judged against a baseline.

## Decision

Implement detection as **modular rules**: each rule is a class with an ID, a category, a compiled regular expression, optional **validator** (Luhn, IBAN mod-97), optional **context words**, base confidence and adjustments. Rule metadata (weights, severities, explanations, recommendations) lives in a versioned catalogue (`RULESET_VERSION`).

## Alternatives considered

- **Regex only** — too many false positives (any 16 digits looks like a card).
- **Microsoft Presidio** — mature open-source PII framework, but brings NLP models and dependencies we cannot explain or tune yet; a good benchmark later.
- **ML / LLM classifier first** — opaque, needs labelled data, and sending documents to an external model would itself be a data exposure.

## Consequences

- **(+)** Every finding can say exactly which rule and validation fired.
- **(+)** Fast, deterministic, easy to unit-test with synthetic examples.
- **(+)** Provides the baseline for future AI comparison (precision/recall).
- **(−)** Misses unstructured sensitive text (e.g. a confidential paragraph without keywords).
- **(−)** Country-specific identifiers need careful, context-gated rules.
