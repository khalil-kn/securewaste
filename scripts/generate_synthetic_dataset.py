#!/usr/bin/env python3
"""Synthetic dataset generator for SecureWaste document classification (Sprint 2: SCRUM-19/20/21).

Generates balanced synthetic documents across four classification labels:
- Public: No sensitive data
- Internal: Emails, phone numbers, keywords
- Confidential: Payment cards, IBANs, national IDs, passports, confidentiality labels
- Highly Confidential: API keys, secrets, private keys

All data is synthetic/fictional - no real company or personal data.
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path

# =============================================================================
# Configuration
# =============================================================================

CLASSIFICATION_LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]

# Target samples per class for balanced dataset
SAMPLES_PER_CLASS = 50

# Output directory
OUTPUT_DIR = Path("tests/fixtures/synthetic_dataset")

# Random seed for reproducibility
SEED = 42

random.seed(SEED)


# =============================================================================
# Synthetic Data Templates
# =============================================================================

# Public documents - no sensitive content
PUBLIC_TEMPLATES = [
    "Meeting agenda for {date}: Discuss project timeline and deliverables.",
    "Weekly status report: All tasks on track. No blockers identified.",
    "Team lunch invitation: Join us Friday at 12pm in the cafeteria.",
    "Office holiday schedule: Closed Dec 24-26, Dec 31-Jan 1.",
    "Project kickoff notes: Goals, milestones, and team assignments.",
    "Quarterly review template: Objectives, achievements, next steps.",
    "Training session slides: Introduction to {topic} for new hires.",
    "Company policy reminder: Please review the updated handbook.",
    "Event announcement: Annual conference on {date} at {venue}.",
    "Internal newsletter: Employee spotlight, birthdays, and updates.",
]

# Internal documents - emails, phones, keywords
INTERNAL_TEMPLATES = [
    "Contact {name} at {email} or {phone} for project questions.",
    "HR onboarding: {name} ({email}) starts {date}. Assign buddy.",
    "IT support ticket: {name} reports issue with {system}. Contact {email}.",
    "Team directory: {name} - {role} - {email} - {phone}",
    "Meeting invite: {name} ({email}) scheduled sync for {date}.",
    "Access request: {name} needs {system} access. Email: {email}",
    "Performance review: {name} ({email}) - {date} with manager.",
    "Expense report: {name} submitted via {email}. Phone: {phone}",
    "Internal memo: {keyword} project update from {name} ({email}).",
    "Calendar invite: {name} at {email} - {topic} discussion {date}.",
]

# Confidential documents - payment cards, IBANs, IDs, labels
CONFIDENTIAL_TEMPLATES = [
    "Invoice #{id}: Payment card {card} for {amount}. CONFIDENTIAL",
    "Bank transfer: IBAN {iban} for {amount}. Reference: {ref}. CONFIDENTIAL",
    "Employee record: National ID {national_id} - {name}. CONFIDENTIAL",
    "Passport copy: {passport} for {name} travel. CONFIDENTIAL",
    "Client contract: Payment terms {card}. IBAN: {iban}. CONFIDENTIAL",
    "Payroll data: Employee {national_id} salary {amount}. CONFIDENTIAL",
    "Vendor payment: Card {card} IBAN {iban} amount {amount}. CONFIDENTIAL",
    "Travel booking: Passport {passport} for {name}. CONFIDENTIAL",
    "Financial statement: Account {iban} balance {amount}. CONFIDENTIAL",
    "Audit trail: Transaction {card} verified. CONFIDENTIAL",
]

# Highly Confidential - API keys, secrets, private keys
HIGHLY_CONFIDENTIAL_TEMPLATES = [
    "AWS credentials: AKIA{key} secret={secret}. HIGHLY CONFIDENTIAL",
    "Database config: password={pwd} api_key={key}. HIGHLY CONFIDENTIAL",
    "SSH private key: -----BEGIN PRIVATE KEY-----\n{key}\n-----END PRIVATE KEY-----. HIGHLY CONFIDENTIAL",
    "API token: Bearer {token}. DO NOT SHARE. HIGHLY CONFIDENTIAL",
    "Kubernetes secret: api-key={key} secret={secret}. HIGHLY CONFIDENTIAL",
    "Docker registry: username={user} password={pwd}. HIGHLY CONFIDENTIAL",
    "JWT signing key: {key}. Keep secure. HIGHLY CONFIDENTIAL",
    "Encryption key: {key} for {system}. HIGHLY CONFIDENTIAL",
    "Service account: {email} key={key}. HIGHLY CONFIDENTIAL",
    "Webhook secret: {secret} for {endpoint}. HIGHLY CONFIDENTIAL",
]


# =============================================================================
# Synthetic Value Generators
# =============================================================================

def gen_email() -> str:
    domains = ["example.com", "company.org", "test.net", "demo.io", "sample.co"]
    name = "".join(random.choices(string.ascii_lowercase, k=random.randint(5, 10)))
    return f"{name}@{random.choice(domains)}"


def gen_phone() -> str:
    formats = [
        lambda: f"+{random.randint(1, 99)} {random.randint(100, 999)} {random.randint(100, 999)} {random.randint(1000, 9999)}",
        lambda: f"({random.randint(100, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
        lambda: f"{random.randint(100, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
    ]
    return random.choice(formats)()


def gen_payment_card() -> str:
    prefix = "4"
    body = "".join(random.choices(string.digits, k=14))
    partial = prefix + body
    
    def luhn_checksum(num):
        digits = [int(d) for d in num]
        odd = digits[-1::-2]
        even = digits[-2::-2]
        total = sum(odd)
        for d in even:
            total += sum(divmod(d * 2, 10))
        return (10 - (total % 10)) % 10
    check = luhn_checksum(partial + "0")
    return partial + str(check)


def gen_iban() -> str:
    country = "DE"
    check = f"{random.randint(10, 99)}"
    bban = "".join(random.choices(string.digits + string.ascii_uppercase, k=20))
    return f"{country}{check} {bban[:4]} {bban[4:8]} {bban[8:12]} {bban[12:16]} {bban[16:20]}"


def gen_national_id() -> str:
    return "".join(random.choices(string.digits, k=8))


def gen_passport() -> str:
    letter = random.choice(string.ascii_uppercase)
    digits = "".join(random.choices(string.digits, k=7))
    return f"{letter}{digits}"


def gen_aws_key() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=16))


def gen_secret() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=32))


def gen_private_key_fragment() -> str:
    return "\n".join("".join(random.choices(string.ascii_letters + string.digits + "+/=", k=64)) for _ in range(4))


def gen_api_token() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=48))


def gen_jwt_key() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=64))


def gen_encryption_key() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def gen_webhook_secret() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=40))


# =============================================================================
# Document Generation
# =============================================================================

@dataclass
class SyntheticDocument:
    text: str
    label: str
    metadata: dict


def gen_public() -> SyntheticDocument:
    template = random.choice(PUBLIC_TEMPLATES)
    text = template.format(
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        topic=random.choice(["security", "compliance", "onboarding", "tools", "process"]),
        venue=random.choice(["Conference Room A", "Main Hall", "Virtual", "Building 3"]),
    )
    return SyntheticDocument(text=text, label="Public", metadata={})


def gen_internal() -> SyntheticDocument:
    template = random.choice(INTERNAL_TEMPLATES)
    name = f"{random.choice(['John', 'Jane', 'Bob', 'Alice', 'Mike', 'Sarah'])} {random.choice(['Smith', 'Doe', 'Johnson', 'Williams'])}"
    text = template.format(
        name=name,
        email=gen_email(),
        phone=gen_phone(),
        date=f"2026-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
        role=random.choice(["Engineer", "Manager", "Analyst", "Designer", "Lead"]),
        system=random.choice(["Jira", "GitLab", "Confluence", "Slack", "VPN"]),
        keyword=random.choice(["confidential", "internal", "budget", "roadmap", "strategy"]),
        topic=random.choice(["sprint planning", "architecture", "security", "deployment"]),
    )
    return SyntheticDocument(text=text, label="Internal", metadata={})


def gen_confidential() -> SyntheticDocument:
    template = random.choice(CONFIDENTIAL_TEMPLATES)
    name = f"{random.choice(['John', 'Jane', 'Bob', 'Alice'])} {random.choice(['Smith', 'Doe'])}"
    text = template.format(
        id=random.randint(10000, 99999),
        card=gen_payment_card(),
        iban=gen_iban(),
        national_id=gen_national_id(),
        passport=gen_passport(),
        amount=f"${random.randint(100, 10000):,.2f}",
        ref=f"REF{random.randint(10000, 99999)}",
        name=name,
    )
    return SyntheticDocument(text=text, label="Confidential", metadata={})


def gen_highly_confidential() -> SyntheticDocument:
    template = random.choice(HIGHLY_CONFIDENTIAL_TEMPLATES)
    text = template.format(
        key=gen_aws_key(),
        secret=gen_secret(),
        pwd=gen_secret(),
        token=gen_api_token(),
        user=f"user{random.randint(1, 100)}",
        email=gen_email(),
        endpoint=f"/api/webhook/{random.randint(100, 999)}",
        system=random.choice(["prod-db", "staging-api", "analytics", "payments"]),
    )
    return SyntheticDocument(text=text, label="Highly Confidential", metadata={})


GENERATORS = {
    "Public": gen_public,
    "Internal": gen_internal,
    "Confidential": gen_confidential,
    "Highly Confidential": gen_highly_confidential,
}


def generate_dataset(samples_per_class: int = SAMPLES_PER_CLASS) -> list[SyntheticDocument]:
    """Generate balanced synthetic dataset."""
    documents = []
    for label in CLASSIFICATION_LABELS:
        for i in range(samples_per_class):
            doc = GENERATORS[label]()
            doc.metadata = {
                "id": f"{label.lower().replace(' ', '_')}_{i:03d}",
                "generator": "synthetic",
                "seed": SEED,
            }
            documents.append(doc)
    random.shuffle(documents)
    return documents


def train_test_split(documents: list[SyntheticDocument], test_ratio: float = 0.2) -> tuple[list, list]:
    """Split dataset into train/test maintaining class balance."""
    by_label = {label: [] for label in CLASSIFICATION_LABELS}
    for doc in documents:
        by_label[doc.label].append(doc)
    
    train, test = [], []
    for label in CLASSIFICATION_LABELS:
        random.shuffle(by_label[label])
        split_idx = int(len(by_label[label]) * (1 - test_ratio))
        train.extend(by_label[label][:split_idx])
        test.extend(by_label[label][split_idx:])
    
    random.shuffle(train)
    random.shuffle(test)
    return train, test


def save_dataset(documents: list[SyntheticDocument], split: str) -> None:
    """Save dataset as text files with labels."""
    split_dir = OUTPUT_DIR / split
    split_dir.mkdir(parents=True, exist_ok=True)
    
    labels_file = split_dir / "labels.txt"
    with labels_file.open("w") as f:
        for doc in documents:
            text_file = split_dir / f"{doc.metadata['id']}.txt"
            text_file.write_text(doc.text, encoding="utf-8")
            f.write(f"{doc.metadata['id']}\t{doc.label}\n")


def generate_readme() -> None:
    """Generate README for the synthetic dataset."""
    total = SAMPLES_PER_CLASS * 4
    train_count = int(total * 0.8)
    test_count = total - train_count
    readme = f"""# SecureWaste Synthetic Classification Dataset

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

- **Total samples**: {total}
- **Samples per class**: {SAMPLES_PER_CLASS}
- **Train/Test split**: 80/20 (stratified)
- **Train samples**: {train_count}
- **Test samples**: {test_count}
- **Random seed**: {SEED} (reproducible)

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
├── train/
│   ├── labels.txt          # id\\tlabel mapping
│   ├── public_000.txt
│   ├── internal_001.txt
│   └── ...
└── test/
    ├── labels.txt
    ├── confidential_000.txt
    └── ...
```

## Usage

```python
# Load training data
train_docs = []
with open("synthetic_dataset/train/labels.txt") as f:
    for line in f:
        doc_id, label = line.strip().split("\\t")
        text = Path(f"synthetic_dataset/train/{{doc_id}}.txt").read_text()
        train_docs.append((text, label))

# Train/test classifier (rule-based, no training needed)
from securewaste.core import predict_classification

for text, true_label in train_docs:
    pred_label = predict_classification(text)
    print(f"True: {{true_label}}, Pred: {{pred_label.value}}")
```

## Regenerating

```bash
python scripts/generate_synthetic_dataset.py
```

## Disclaimer

**All data is synthetic.** Generated values (cards, IBANs, keys, IDs) are randomly
created and have no real-world validity. Luhn check digits are computed for cards
but these are not real payment instruments.
"""
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main():
    print(f"Generating synthetic dataset ({SAMPLES_PER_CLASS} samples per class)...")
    
    documents = generate_dataset(SAMPLES_PER_CLASS)
    train, test = train_test_split(documents, test_ratio=0.2)
    
    print(f"Train: {len(train)} samples")
    print(f"Test: {len(test)} samples")
    
    # Verify balance
    for split_name, split_docs in [("train", train), ("test", test)]:
        counts = {label: sum(1 for d in split_docs if d.label == label) for label in CLASSIFICATION_LABELS}
        print(f"  {split_name}: {counts}")
    
    save_dataset(train, "train")
    save_dataset(test, "test")
    generate_readme()
    
    print(f"\nDataset saved to {OUTPUT_DIR}")
    print("Done!")


if __name__ == "__main__":
    main()