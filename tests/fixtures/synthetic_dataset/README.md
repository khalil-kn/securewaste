# SecureWaste Synthetic Classification Dataset

Generated for Sprint 2 (SCRUM-19, SCRUM-20, SCRUM-21) - AI/ML document classification.

## Overview

This dataset contains **synthetic/fictional documents** for training and evaluating
a document sensitivity classifier. **No real company data, personal information,
or credentials are included.**

## Classes (4 labels)

| Label | Description | Example Content |
|-------|-------------|-----------------|
| `Public` | No sensitive data | Meeting agendas, announcements, policies |
| `Internal` | Emails, phones, keywords | Contact info, team directories, internal memos |
| `Confidential` | Payment cards, IBANs, IDs, labels | Invoices, contracts, payroll, travel docs |
| `Highly Confidential` | API keys, secrets, private keys | Credentials, tokens, encryption keys |

## Dataset Statistics

- **Total samples**: 200
- **Samples per class**: 50
- **Train/Validation/Test samples**: 137/32/31
- **Split policy**: grouped by source template to prevent template leakage
- **Random seed**: 42 (reproducible)

## Split Integrity

Documents generated from the same source template are kept in exactly one split.
This reduces template leakage between training, validation, and test data.

## Features for Classification

The classifier uses these heuristic features (rule-based, no ML model):

1. **Explicit labels**: CONFIDENTIAL, INTERNAL, RESTRICTED keywords
2. **High-sensitivity patterns**:
   - AWS keys (AKIA...)
   - API keys, secrets, passwords
   - Private keys (BEGIN PRIVATE KEY)
3. **Payment cards**: 16-digit Luhn-valid numbers
4. **IBANs**: Country code + check digits + BBAN
5. **National IDs**: 8-digit numbers
6. **Passports**: Letter + 7 digits
7. **Emails**: Standard email format
8. **Phones**: Various international/national formats

## Label Criteria (Decision Logic)

```
if has_secret_pattern:           -> Highly Confidential
elif has_card_or_iban_or_id:     -> Confidential
elif has_confidentiality_label:  -> Confidential
elif has_email_or_phone:         -> Internal
else:                            -> Public
```

Priority order: Highly Confidential > Confidential > Internal > Public

## File Structure

```
synthetic_dataset/
â”œâ”€â”€ train/
â”‚   â”œâ”€â”€ labels.txt          # id\tlabel mapping
â”‚   â”œâ”€â”€ public_000.txt
â”‚   â”œâ”€â”€ internal_001.txt
â”‚   â””â”€â”€ ...
â””â”€â”€ test/
    â”œâ”€â”€ labels.txt
    â”œâ”€â”€ confidential_000.txt
    â””â”€â”€ ...
```

## Usage

```python
# Load training data
train_docs = []
with open("synthetic_dataset/train/labels.txt") as f:
    for line in f:
        doc_id, label = line.strip().split("\t")
        text = Path(f"synthetic_dataset/train/{doc_id}.txt").read_text()
        train_docs.append((text, label))

# Train/test classifier (rule-based, no training needed)
from securewaste.core import predict_classification

for text, true_label in train_docs:
    pred_label = predict_classification(text)
    print(f"True: {true_label}, Pred: {pred_label.value}")
```

## Regenerating

```bash
python scripts/generate_synthetic_dataset.py
```

## Disclaimer

**All data is synthetic.** Generated values (cards, IBANs, keys, IDs) are randomly
created and have no real-world validity. Luhn check digits are computed for cards
but these are not real payment instruments.
