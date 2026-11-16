"""Read-only audit of Secure Waste's synthetic classification dataset.

Run: python -m scripts.audit_ml_dataset
No model files or training data are changed.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "synthetic_dataset"
ROOT = DEFAULT_ROOT
SPLITS = ("train", "val", "test")
LABELS = ("Public", "Internal", "Confidential", "Highly Confidential")


def normalize(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def load(split: str) -> list[tuple[str, str, str]]:
    folder = ROOT / split
    rows = []
    for line in (folder / "labels.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        doc_id, label = line.split("\t", 1)
        rows.append((doc_id, label, (folder / f"{doc_id}.txt").read_text(encoding="utf-8")))
    return rows


def main() -> None:
    global ROOT

    parser = argparse.ArgumentParser(description="Audit synthetic dataset integrity.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()

    ROOT = args.dataset_dir.resolve()
    datasets = {split: load(split) for split in SPLITS}
    print("SECURE WASTE DATASET AUDIT (read-only)")
    print("=" * 65)
    for split, rows in datasets.items():
        counts = Counter(label for _, label, _ in rows)
        unique = len({normalize(text) for _, _, text in rows})
        print(
            f"{split:5} | total={len(rows):3} | unique_normalized={unique:3} | "
            + " | ".join(f"{label}={counts[label]}" for label in LABELS)
        )
        unknown = sorted(set(counts) - set(LABELS))
        if unknown:
            print("  ERROR unknown labels:", unknown)
    print("\nExact duplicates across splits:")
    for i, left in enumerate(SPLITS):
        for right in SPLITS[i + 1 :]:
            a = {normalize(t): (doc, label) for doc, label, t in datasets[left]}
            b = {normalize(t): (doc, label) for doc, label, t in datasets[right]}
            overlap = set(a) & set(b)
            print(f"  {left} vs {right}: {len(overlap)}")
            for key in sorted(overlap)[:5]:
                print(f"    {a[key]} <-> {b[key]}")
    print("\nNear-duplicates across train vs val/test (similarity >= 0.85):")
    train = [(doc, label, normalize(t)[:2000]) for doc, label, t in datasets["train"]]
    for split in ("val", "test"):
        pairs = []
        for doc, label, t in datasets[split]:
            n = normalize(t)[:2000]
            for train_doc, train_label, train_text in train:
                if abs(len(n) - len(train_text)) > max(len(n), len(train_text)) * 0.25:
                    continue
                score = SequenceMatcher(None, n, train_text, autojunk=False).ratio()
                if score >= 0.85:
                    pairs.append((score, doc, label, train_doc, train_label))
        pairs.sort(reverse=True)
        print(f"  {split}: {len(pairs)} near-duplicate pairs")
        for score, doc, label, other, other_label in pairs[:10]:
            print(f"    {score:.2f} {split}/{doc} ({label}) <-> train/{other} ({other_label})")
    print("\nCaution: this audit cannot detect semantic template leakage or prove generalization.")
    print("Do not use the previously inspected 40-case evaluation as a blind test set.")


if __name__ == "__main__":
    main()
