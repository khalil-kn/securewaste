# Document risk: contract (SCRUM-46 / SCRUM-47)

**Status: decided by Khalil Knaissi (SCRUM-46 owner), 26 Nov 2026. Decisions and their reasons are in section 8; challenge them in PR review.**

## 1. What risk is, and what it is not

| | Classification | Document risk |
|---|---|---|
| Question | What kind of document is this? | How dangerous is it to share it now? |
| Values | Public / Internal / Confidential / Highly Confidential | score 0–100 and level informational / low / medium / high / critical |
| Computed by | ML + rules (`core/ml_classifier.py`) | fixed formula (`core/risk.py`, `assess()`) |
| Input | document text | validated findings only |

**Rule: risk never reads the classification label, and the label never sets the risk.** A "Public" document with an API key is high risk; a "Confidential" document with no findings scores 0. Both are shown in separate cards on the results page.

## 2. Inputs

`assess(findings: list[Finding]) -> RiskAssessment`. Per finding it uses:

| Field | Use |
|---|---|
| `category` | weight from `detection/catalogue.py` (secret 45, card 40, national ID 30, passport 30, IBAN 25, label 10, keyword 8, phone 4, e-mail 3) |
| `confidence` | multiplies the weight; ≥ 0.8 is "high" |
| `value_hmac` | defines a *distinct* value (same value on several pages = one) |
| `review_status` | `false_positive` findings are ignored |

`severity`, `occurrences`, `masked_value` and `context` are **not** used. Total repetitions of one value add nothing; at most 3 extra distinct values per category count (20% of the weight each).

## 3. Missing-data behaviour

| Situation | Result |
|---|---|
| No findings, or only false positives | score 0, `informational`, no recommendations |
| Low-confidence finding | counts, but less (weight × confidence); a secret below 0.8 gets no 75 floor |
| Classifier failed or model missing | risk is still computed (it does not depend on the classifier) |
| Risk not approved (`SECUREWASTE_RISK_APPROVED=false`, the default) | computed nowhere visible: no risk card, no `risk` key in sync |
| Scan synced before Sprint 4 | cloud `risk` is `NULL` and stays readable |

## 4. Algorithm

Architecture §8 and ADR-0008, unchanged: weight × confidence per category with capped repetition, +10 combination bonus (≥ 2 categories of weight ≥ 25), +10 label amplifier (label + any weight ≥ 25), round half up, cap at 100, floors (high-confidence secret ≥ 75, payment card ≥ 50). Levels: 0–9 informational, 10–24 low, 25–49 medium, 50–74 high, 75–100 critical.

Rounding, cap and floors are factors too, so **the factor points always add up to the score** (tested). Same input always gives the same output, in any order (tested).

## 5. Output

```text
RiskAssessment.to_dict()
  score           int 0–100
  level           "informational" | "low" | "medium" | "high" | "critical"
  reasons         list[str]   human text, one per factor; listed points add up to the score
  factors         list[{code, points, reason}]   codes: category:<name>, combination_bonus,
                                                 label_amplifier, rounding, cap, floor:secret, floor:payment_card
  recommendations list[str]   fixed catalogue text, most serious first
  score_version   "additive-1+2026.11.0"   (algorithm version + RULESET_VERSION)
```

**Never in the output:** raw or masked values, context snippets, HMACs, file names, paths, page text. Reasons are catalogue labels plus counts (tested).

**Versioning:** change the algorithm → bump `RISK_MODEL_VERSION` in `core/risk.py`; change a weight or threshold → bump `RULESET_VERSION` in `catalogue.py`.

## 6. Cloud sync

Only the level crosses to the cloud, mapped to the three values `cloud_api/validation.py` accepts:

| Local level | Cloud `risk` |
|---|---|
| informational, low | `Low` |
| medium | `Medium` |
| high, critical | `High` |

Example event (approved risk, fictional):

```json
{"event_id": "…", "timestamp": "2026-12-01T10:30:00+00:00", "classification": "Confidential",
 "counts": {"email": 1, "phone": 1, "keyword": 0}, "risk": "High"}
```

Not approved → the `risk` key is left out and the cloud stores `NULL`, exactly like scans made before Sprint 4. Score, reasons, factors and recommendations are **never** synced; no document text and no feature vectors either. The cloud API needed no change: `risk` was already an optional, nullable field (migration 001, ADR-0011).

## 7. UI guidance (results page)

- Own card, above the classification card, titled "Document risk · application-defined estimate".
- Show `level` and `score`, then "Why this score" (`reasons`) and "Recommended actions" (`recommendations`).
- Always show: "Based only on the findings, not on the classification. Not a compliance score." and `score_version`.
- Show the card even when classification is unavailable. Do not show it when `risk` is `None`.
- Colours: reuse `sw-pill-sev-<level>` and `sw-meter-<level>` (`sw-meter-off` for informational).

Examples (real output of `assess()` on fictional findings):

| Findings | Score | Level | Reasons shown |
|---|---|---|---|
| none | 0 | informational | "No sensitive findings counted (findings marked false positive are excluded)." |
| 1 e-mail (0.8), 1 phone (0.7) | 5 | informational | +2.8 Phone number · +2.4 E-mail address · −0.2 Rounded |
| 1 card (0.95), 1 e-mail (0.9) | 50 | high | +38 Payment card number · +2.7 E-mail address · +0.3 Rounded · +9 Minimum score of 50 for a Luhn-valid payment card |
| e-mail, phone, card, IBAN, label | 97 | critical | +38 card · +23.8 IBAN · +10 label · +2.4 phone · +2.7 e-mail · +10 combination · +10 label with high-sensitivity data · +0.2 Rounded |

## 8. Decisions

1. **Risk stays OFF (`SECUREWASTE_RISK_APPROVED=false`) until the high-sensitivity detection rules exist.**
   Today the engine only detects e-mail, phone and keywords (`detect_service.py`; `validators.py` is a stub). A
   document with an API key or card number would therefore show **"Low"**, and a user could trust that and share
   it. A missing score is safer than a falsely reassuring one. Turn it on in the PR that adds the secret, card,
   IBAN and confidentiality-label rules to the engine (the hybrid classifier's `_luhn_check` / `_iban_check` can be
   reused for `validators.py`). Those rules are detection work and are out of scope for SCRUM-46.
2. **Cloud mapping as in section 6; `informational` is sent as `Low`, not omitted.**
   `NULL` must keep one meaning, "risk was not assessed" (old scans, risk off), so it is never confused with
   "assessed, nothing found". The cloud only has three levels, and `informational` is the bottom of `Low`.
3. **The switch is a deployment setting, not a per-user choice.** It turns the card and the synced level on
   together, so the cloud never holds a level the user was not shown.
4. **Findings marked *resolved* still count; only *false positive* is excluded.**
   "Resolved" means someone dealt with it, but the original file still contains the value. A redacted copy is a
   new document and gets its own scan and score.
