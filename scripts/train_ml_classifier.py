#!/usr/bin/env python3
"""Train and evaluate SecureWaste's local TF-IDF classifier.

Validation is the default. Run --final-test only after model choices are frozen.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from securewaste.core.ml_classifier import MLClassifier

DEFAULT_DATASET_DIR = Path("tests/fixtures/synthetic_dataset")
DEFAULT_MODEL_DIR = Path("securewaste/models")
LABELS = ["Public", "Internal", "Confidential", "Highly Confidential"]


def load_dataset(split: str, dataset_dir: Path = DEFAULT_DATASET_DIR) -> tuple[list[str], list[str]]:
    """Read documents and tab-separated IDs/labels from one split."""
    if split not in {"train", "val", "test"}:
        raise ValueError(f"Unknown split: {split}")
    split_dir = Path(dataset_dir) / split
    labels_file = split_dir / "labels.txt"
    texts: list[str] = []
    labels: list[str] = []
    with labels_file.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                doc_id, label = line.rstrip("\r\n").split("\t", 1)
            except ValueError as exc:
                raise ValueError(f"Invalid label record at {labels_file}:{line_number}") from exc
            if label not in LABELS:
                raise ValueError(f"Unknown label {label!r} in {labels_file}:{line_number}")
            doc_path = split_dir / f"{doc_id}.txt"
            texts.append(doc_path.read_text(encoding="utf-8"))
            labels.append(label)
    if not texts:
        raise ValueError(f"No documents found in {split_dir}")
    return texts, labels


def compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Calculate per-class and aggregate classification metrics."""
    confusion = defaultdict(lambda: defaultdict(int))
    for true, pred in zip(y_true, y_pred, strict=True):
        confusion[true][pred] += 1

    per_class = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in labels if other != label)
        fn = sum(confusion[label][other] for other in labels if other != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    total_support = sum(m["support"] for m in per_class.values())
    correct = sum(confusion[label][label] for label in labels)

    def macro(metric: str) -> float:
        return sum(m[metric] for m in per_class.values()) / len(labels)

    def weighted(metric: str) -> float:
        return sum(m[metric] * m["support"] for m in per_class.values()) / total_support if total_support else 0.0

    return {
        "accuracy": correct / len(y_true) if y_true else 0.0,
        "correct": correct,
        "total": len(y_true),
        "macro_precision": macro("precision"),
        "macro_recall": macro("recall"),
        "macro_f1": macro("f1"),
        "weighted_precision": weighted("precision"),
        "weighted_recall": weighted("recall"),
        "weighted_f1": weighted("f1"),
        "per_class": per_class,
        "confusion_matrix": {key: dict(value) for key, value in confusion.items()},
    }


def evaluate_classifier(
    classifier: MLClassifier,
    split: str = "val",
    dataset_dir: Path = DEFAULT_DATASET_DIR,
) -> dict:
    """Evaluate an in-memory classifier on validation or test data."""
    if split not in {"val", "test"}:
        raise ValueError("split must be 'val' or 'test'")
    texts, true_labels = load_dataset(split, dataset_dir)
    predictions = [classifier.predict(text).label.value for text in texts]
    return compute_metrics(true_labels, predictions, LABELS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and evaluate the SecureWaste ML classifier.")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=DEFAULT_DATASET_DIR,
        help=f"Dataset directory (default: {DEFAULT_DATASET_DIR})",
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=DEFAULT_MODEL_DIR,
        help=f"Model output directory (default: {DEFAULT_MODEL_DIR})",
    )
    parser.add_argument(
        "--final-test",
        action="store_true",
        help="Evaluate held-out test split; use only after model choices are frozen.",
    )
    args = parser.parse_args()

    print(f"Dataset: {args.dataset_dir}")
    print(f"Model output: {args.model_dir}")
    print("Loading training data...")
    train_texts, train_labels = load_dataset("train", args.dataset_dir)
    print(f"Train samples: {len(train_texts)}")
    print(f"Train class distribution: {Counter(train_labels)}")

    print("\nTraining TF-IDF + LogisticRegression classifier...")
    args.model_dir.mkdir(parents=True, exist_ok=True)
    classifier = MLClassifier.train(
        train_texts,
        train_labels,
        model_path=args.model_dir / "classifier_pipeline.pkl",
        metadata_path=args.model_dir / "classifier_metadata.json",
    )
    print(f"Model saved to {args.model_dir}")

    evaluation_split = "test" if args.final_test else "val"
    print(f"\nEvaluating on {evaluation_split} set...")
    metrics = evaluate_classifier(classifier, evaluation_split, args.dataset_dir)

    print(f"\n=== {evaluation_split.title()} Set Results ===")
    print(f"Overall Accuracy: {metrics['accuracy']:.2%} ({metrics['correct']}/{metrics['total']})")
    for name in (
        "macro_precision",
        "macro_recall",
        "macro_f1",
        "weighted_precision",
        "weighted_recall",
        "weighted_f1",
    ):
        print(f"{name.replace('_', ' ').title()}: {metrics[name]:.2%}")

    print("\nPer-Class Metrics:")
    for label, stats in metrics["per_class"].items():
        print(f"  {label}:")
        for metric in ("precision", "recall", "f1"):
            print(f"    {metric.title()}: {stats[metric]:.2%}")
        print(f"    Support: {stats['support']}")

    print("\nConfusion Matrix (True -> Predicted):")
    print("  True \\ Pred: " + " ".join(f"{label[:12]:>12}" for label in LABELS))
    for true_label in LABELS:
        counts = metrics["confusion_matrix"].get(true_label, {})
        print(f"  {true_label[:12]:>12}: " + " ".join(f"{counts.get(label, 0):>12}" for label in LABELS))

    print("\n=== Limitations ===")
    print("- Synthetic data performance does NOT prove real-world accuracy")
    print(f"- Model trained on {len(train_texts)} synthetic training samples")
    print("- Validation is used during development; test is reserved for final evaluation")
    print("- The previously inspected 40-case evaluation is not a blind test set")
    print("- No external data, no cloud transmission, fully local")
    print("\nDone!")


if __name__ == "__main__":
    main()
