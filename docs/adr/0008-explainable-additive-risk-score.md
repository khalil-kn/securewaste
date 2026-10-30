# ADR-0008: Explainable additive risk score

| | |
|---|---|
| Status | Accepted |
| Date | 2026-10-29 |
| Deciders | SecureWaste team |

## Context

Users need one overall answer ("is this safe to share?") and the reasons behind it. Findings are not equal: an API key matters far more than an e-mail address.

## Decision

Use the **weighted, additive model** in [Architecture §8](../02-architecture.md#8-risk-scoring-model): category weights × confidence, diminishing repetition, combination bonus, label amplifier, floors for validated secrets and cards, five levels with configurable thresholds. Every point added produces a human-readable reason. The UI labels it *application-defined risk estimate*.

## Alternatives considered

- **Count of findings** — treats an e-mail like an API key.
- **Max severity only** — ignores accumulation and combinations.
- **Statistical / ML model** — no labelled data; not explainable to a student team or a reviewer.
- **CVSS-like formula** — designed for vulnerabilities, not data exposure; would imply false precision.

## Consequences

- **(+)** Transparent and easy to unit-test with worked examples.
- **(+)** Tunable through the catalogue without code changes.
- **(−)** Weights are judgement calls and must be revisited with real feedback.
- **(−)** Not comparable with other tools' scores.
