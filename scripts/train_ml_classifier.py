#!/usr/bin/env python3
"""Train ML classifier on synthetic dataset (Sprint 2: SCRUM-19/20/21).

Loads synthetic dataset, trains TF-IDF + LogisticRegression,
saves model to securewaste/models/, and evaluates on test set.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from securewaste.core.ml_classifier import predict_classification_with_confidence, train_and_save_model


def load_dataset(split: str) -> tuple[list[str], list[str]]:
    """Load texts and labels from dataset split."""
    split_dir = Path(f"tests/fixtures/synthetic_dataset/{split}")
    labels_file = split_dir / "labels.txt"

    texts, labels = [], []
    with labels_file.open() as f:
        for line in f:
            doc_id, label = line.strip().split("\t")
            text = (split_dir / f"{doc_id}.txt").read_text(encoding="utf-8")
            texts.append(text)
            labels.append(label)

    return texts, labels


def compute_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict:
    """Compute precision, recall, F1, and confusion matrix."""
    # Confusion matrix: true_label -> pred_label -> count
    confusion = defaultdict(lambda: defaultdict(int))
    for true, pred in zip(y_true, y_pred, strict=True):
        confusion[true][pred] += 1

    # Per-class metrics
    per_class = {}
    for label in labels:
        tp = confusion[label][label]
        fp = sum(confusion[other][label] for other in labels if other != label)
        fn = sum(confusion[label][other] for other in labels if other != label)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_class[label] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    # Macro averages
    macro_precision = sum(m["precision"] for m in per_class.values()) / len(labels)
    macro_recall = sum(m["recall"] for m in per_class.values()) / len(labels)
    macro_f1 = sum(m["f1"] for m in per_class.values()) / len(labels)

    # Weighted averages (by support)
    total_support = sum(m["support"] for m in per_class.values())
    weighted_precision = (
        sum(m["precision"] * m["support"] for m in per_class.values()) / total_support if total_support > 0 else 0.0
    )
    weighted_recall = (
        sum(m["recall"] * m["support"] for m in per_class.values()) / total_support if total_support > 0 else 0.0
    )
    weighted_f1 = sum(m["f1"] * m["support"] for m in per_class.values()) / total_support if total_support > 0 else 0.0

    # Overall accuracy
    correct = sum(confusion[label][label] for label in labels)
    total = len(y_true)
    accuracy = correct / total if total > 0 else 0.0

    # Convert confusion to regular dict for JSON serialization
    confusion_dict = {k: dict(v) for k, v in confusion.items()}

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "macro_f1": macro_f1,
        "weighted_precision": weighted_precision,
        "weighted_recall": weighted_recall,
        "weighted_f1": weighted_f1,
        "per_class": per_class,
        "confusion_matrix": confusion_dict,
    }


def evaluate_classifier() -> dict:
    """Evaluate trained classifier on test set."""
    test_texts, test_labels = load_dataset("test")
    labels = ["Public", "Internal", "Confidential", "Highly Confidential"]

    y_pred = []
    for text in test_texts:
        result = predict_classification_with_confidence(text)
        y_pred.append(result.label.value)

    return compute_metrics(test_labels, y_pred, labels)


def main() -> None:
    print("Loading training data...")
    train_texts, train_labels = load_dataset("train")
    print(f"Train samples: {len(train_texts)}")

    # Verify class balance
    print(f"Train class distribution: {Counter(train_labels)}")

    print("\nTraining TF-IDF + LogisticRegression classifier...")
    _ = train_and_save_model(train_texts, train_labels)
    print("Model saved to securewaste/models/")

    print("\nEvaluating on test set...")
    metrics = evaluate_classifier()

    print("\n=== Test Set Results ===")
    print(f"Overall Accuracy: {metrics['accuracy']:.2%} ({metrics['correct']}/{metrics['total']})")
    print(f"Macro Precision: {metrics['macro_precision']:.2%}")
    print(f"Macro Recall: {metrics['macro_recall']:.2%}")
    print(f"Macro F1: {metrics['macro_f1']:.2%}")
    print(f"Weighted Precision: {metrics['weighted_precision']:.2%}")
    print(f"Weighted Recall: {metrics['weighted_recall']:.2%}")
    print(f"Weighted F1: {metrics['weighted_f1']:.2%}")
    print("\nPer-Class Metrics:")
    for label, stats in metrics["per_class"].items():
        print(f"  {label}:")
        print(f"    Precision: {stats['precision']:.2%}")
        print(f"    Recall: {stats['recall']:.2%}")
        print(f"    F1: {stats['f1']:.2%}")
        print(f"    Support: {stats['support']}")

    if metrics["confusion_matrix"]:
        print("\nConfusion Matrix (True -> Predicted):")
        labels = ["Public", "Internal", "Confidential", "Highly Confidential"]
        # Print header
        print("  True \\ Pred:  " + "  ".join(f"{name[:12]:>12}" for name in labels))
        for true_label in labels:
            row = f"  {true_label[:12]:>12}: "
            for pred_label in labels:
                count = metrics["confusion_matrix"].get(true_label, {}).get(pred_label, 0)
                row += f"{count:>12} "
            print(row)

    # Error examples
    print("\nError Examples:")
    test_texts, test_labels = load_dataset("test")
    errors_shown = 0
    for text, true_label in zip(test_texts, test_labels, strict=True):
        result = predict_classification_with_confidence(text)
        if result.label.value != true_label and errors_shown < 5:
            print(f"  True: {true_label}, Pred: {result.label.value} (conf: {result.confidence:.2f})")
            print(f"  Text: {text[:100]}...")
            errors_shown += 1

    print("\n=== Limitations ===")
    print("- Synthetic data performance does NOT prove real-world accuracy")
    print("- Model trained on 160 synthetic samples (50 per class)")
    print("- Rule-based fallback used for patterns not captured by TF-IDF")
    print("- No external data, no cloud transmission, fully local")

    print("\nDone!")


if __name__ == "__main__":
    main()
