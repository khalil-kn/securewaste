#!/usr/bin/env python3
"""Train ML classifier on synthetic dataset (Sprint 2: SCRUM-19/20/21).

Loads synthetic dataset, trains TF-IDF + LogisticRegression,
saves model to securewaste/models/, and evaluates on test set.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from securewaste.core.ml_classifier import train_and_save_model, predict_classification_with_confidence


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


def evaluate_classifier() -> dict:
    """Evaluate trained classifier on test set."""
    test_texts, test_labels = load_dataset("test")

    correct = 0
    total = len(test_texts)
    confusion = {}
    per_class = {}

    for text, true_label in zip(test_texts, test_labels, strict=True):
        result = predict_classification_with_confidence(text)
        pred_label = result.label.value

        if pred_label == true_label:
            correct += 1
        else:
            confusion[(true_label, pred_label)] = confusion.get((true_label, pred_label), 0) + 1

        # Per-class tracking
        if true_label not in per_class:
            per_class[true_label] = {"correct": 0, "total": 0}
        per_class[true_label]["total"] += 1
        if pred_label == true_label:
            per_class[true_label]["correct"] += 1

    accuracy = correct / total if total > 0 else 0

    # Per-class metrics
    per_class_metrics = {}
    for label, stats in per_class.items():
        precision = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        per_class_metrics[label] = {
            "accuracy": precision,
            "correct": stats["correct"],
            "total": stats["total"],
        }

    return {
        "accuracy": accuracy,
        "correct": correct,
        "total": total,
        "confusion": confusion,
        "per_class": per_class_metrics,
    }


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
    print("\nPer-Class Accuracy:")
    for label, stats in metrics["per_class"].items():
        print(f"  {label}: {stats['accuracy']:.2%} ({stats['correct']}/{stats['total']})")

    if metrics["confusion"]:
        print("\nConfusion Matrix (True -> Predicted):")
        for (true_label, pred_label), count in sorted(metrics["confusion"].items()):
            print(f"  {true_label} -> {pred_label}: {count}")

    # Error examples
    print("\nError Examples:")
    test_texts, test_labels = load_dataset("test")
    errors_shown = 0
    for text, true_label in zip(test_texts, test_labels, strict=True):
        result = predict_classification_with_confidence(text)
        if result.label.value != true_label and errors_shown < 3:
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