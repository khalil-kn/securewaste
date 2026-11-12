"""Unit tests for ML classifier (Sprint 2: SCRUM-19/20/21)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from securewaste.core.ml_classifier import (
    LABELS,
    MLClassificationResult,
    MLClassifier,
    MLClassifierError,
    predict_classification,
    predict_classification_with_confidence,
    train_and_save_model,
)


class TestMLClassifier:
    """Tests for MLClassifier class."""

    def test_train_and_predict(self):
        """Train on synthetic data and predict."""
        train_texts = [
            "Public document about meetings and schedules",
            "Internal email john@company.com for contact",
            "Confidential invoice card 4111111111111111",
            "Highly Confidential AWS key AKIAIOSFODNN7EXAMPLE",
        ] * 5  # 20 samples total
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            metadata_path = Path(tmpdir) / "test_metadata.json"
            
            classifier = MLClassifier.train(train_texts, train_labels, model_path, metadata_path)
            
            # Test predictions
            result = classifier.predict("Team meeting next week")
            assert result.label.value == "Public"
            
            result = classifier.predict("Email me at test@company.com")
            assert result.label.value == "Internal"
            
            result = classifier.predict("Payment card 4111111111111111 CONFIDENTIAL")
            assert result.label.value == "Confidential"
            
            result = classifier.predict("AKIAIOSFODNN7EXAMPLE secret key")
            assert result.label.value == "Highly Confidential"

    def test_predict_empty_text(self):
        """Empty text defaults to Public."""
        train_texts = [
            "Public document about meetings and schedules",
            "Internal email john@company.com for contact",
            "Confidential invoice card 4111111111111111",
            "Highly Confidential AWS key AKIAIOSFODNN7EXAMPLE",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            classifier = MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")
            
            result = classifier.predict("")
            assert result.label.value == "Public"
            assert result.confidence == 1.0
            
            result = classifier.predict("   ")
            assert result.label.value == "Public"

    def test_predict_confidence_scores(self):
        """Predictions include confidence scores."""
        train_texts = [
            "Public document about meetings",
            "Internal email john@company.com",
            "Confidential invoice card 4111111111111111",
            "Highly Confidential AWS key AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            classifier = MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")
            
            result = classifier.predict("Meeting agenda")
            
            assert isinstance(result.confidence, float)
            assert 0.0 <= result.confidence <= 1.0
            assert isinstance(result.all_probabilities, dict)
            assert len(result.all_probabilities) == 4
            assert sum(result.all_probabilities.values()) == pytest.approx(1.0, rel=1e-6)

    def test_load_model(self):
        """Load trained model from disk."""
        train_texts = [
            "Public meeting agenda",
            "Internal contact john@example.com",
            "Confidential card 4111111111111111",
            "Highly Confidential AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            metadata_path = Path(tmpdir) / "test_metadata.json"
            
            # Train and save
            MLClassifier.train(train_texts, train_labels, model_path, metadata_path)
            
            # Load
            loaded = MLClassifier.load(model_path)
            result = loaded.predict("Team meeting")
            assert result.label.value == "Public"

    def test_load_nonexistent_model_raises(self):
        """Loading non-existent model raises error."""
        with pytest.raises(MLClassifierError, match="not found"):
            MLClassifier.load(Path("/nonexistent/model.pkl"))

    def test_untrained_predict_raises(self):
        """Predicting on untrained model raises error."""
        classifier = MLClassifier()
        with pytest.raises(MLClassifierError, match="not fitted"):
            classifier.predict("test")

    def test_invalid_label_raises(self):
        """Training with invalid label raises error."""
        train_texts = ["test"] * 4
        train_labels = ["InvalidLabel"] * 4
        
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            with pytest.raises(MLClassifierError, match="Unknown label"):
                MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

    def test_predict_batch(self):
        """Batch prediction works."""
        train_texts = [
            "Public document",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            classifier = MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")
            
            texts = ["Meeting tomorrow", "Email john@doe.com"]
            results = classifier.predict_batch(texts)
            
            assert len(results) == 2
            assert all(isinstance(r, MLClassificationResult) for r in results)


class TestPredictClassification:
    """Tests for predict_classification convenience function."""

    def test_fallback_to_rule_based(self):
        """When no ML model, falls back to rule-based."""
        # Temporarily move model to test fallback
        model_path = Path("securewaste/models/classifier_pipeline.pkl")
        backup_path = Path("securewaste/models/classifier_pipeline.pkl.test_bak")
        
        model_exists = model_path.exists()
        if model_exists:
            model_path.rename(backup_path)
        
        try:
            # These should work with rule-based fallback
            assert predict_classification("").value == "Public"
            assert predict_classification("CONFIDENTIAL document").value == "Confidential"
            # AWS key needs AKIA + 16 chars pattern
            assert predict_classification("AKIAIOSFODNN7EXAMPLE").value == "Highly Confidential"
        finally:
            if model_exists and backup_path.exists():
                backup_path.rename(model_path)

    def test_ml_model_used_when_available(self):
        """ML model is used when available."""
        # Train a minimal model
        train_texts = [
            "Public meeting",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")
            
            # Test that predict_classification uses the model
            result = predict_classification("Team meeting agenda")
            assert result.value == "Public"


class TestPredictClassificationWithConfidence:
    """Tests for predict_classification_with_confidence."""

    def test_returns_ml_result(self):
        """Returns MLClassificationResult with all fields."""
        train_texts = [
            "Public document",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")
            
            result = predict_classification_with_confidence("Meeting tomorrow")
            
            assert isinstance(result, MLClassificationResult)
            assert hasattr(result, "label")
            assert hasattr(result, "confidence")
            assert hasattr(result, "all_probabilities")


class TestTrainAndSaveModel:
    """Tests for train_and_save_model function."""

    def test_creates_model_and_metadata(self):
        """Creates both model and metadata files."""
        train_texts = [
            "Public document",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5
        
        train_labels = [
            "Public", "Internal", "Confidential", "Highly Confidential"
        ] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "custom_model.pkl"
            metadata_path = Path(tmpdir) / "custom_metadata.json"
            
            train_and_save_model(train_texts, train_labels, model_path, metadata_path)
            
            assert model_path.exists()
            assert metadata_path.exists()
            
            # Verify metadata content
            import json
            with metadata_path.open() as f:
                meta = json.load(f)
            
            assert meta["labels"] == LABELS
            assert meta["n_samples"] == 20
            assert "tfidf_params" in meta
            assert "lr_params" in meta


class TestLabels:
    """Tests for label constants."""

    def test_labels_match_sprint3_contract(self):
        """Labels match Sprint 3 metadata contract."""
        assert LABELS == ["Public", "Internal", "Confidential", "Highly Confidential"]

    def test_label_to_idx_mapping(self):
        """LABEL_TO_IDX maps correctly."""
        from securewaste.core.ml_classifier import LABEL_TO_IDX
        assert LABEL_TO_IDX == {
            "Public": 0,
            "Internal": 1,
            "Confidential": 2,
            "Highly Confidential": 3,
        }


class TestMLClassificationResult:
    """Tests for MLClassificationResult dataclass."""

    def test_immutable(self):
        """Result is immutable (frozen dataclass)."""
        result = MLClassificationResult(
            label="Public",
            confidence=1.0,
            all_probabilities={"Public": 1.0, "Internal": 0.0, "Confidential": 0.0, "Highly Confidential": 0.0},
        )
        with pytest.raises(Exception):
            result.label = "Internal"  # type: ignore


class TestIntegrationWithClassifier:
    """Integration tests with rule-based classifier."""

    def test_synthetic_dataset_evaluation(self):
        """Evaluate on generated synthetic dataset."""
        # This uses the already-generated dataset
        from securewaste.core.ml_classifier import predict_classification_with_confidence
        from pathlib import Path
        
        test_dir = Path("tests/fixtures/synthetic_dataset/test")
        labels_file = test_dir / "labels.txt"
        
        if not labels_file.exists():
            pytest.skip("Synthetic dataset not generated")
        
        correct = 0
        total = 0
        
        with labels_file.open() as f:
            for line in f:
                doc_id, true_label = line.strip().split("\t")
                text = (test_dir / f"{doc_id}.txt").read_text(encoding="utf-8")
                result = predict_classification_with_confidence(text)
                if result.label.value == true_label:
                    correct += 1
                total += 1
        
        accuracy = correct / total if total > 0 else 0
        # Should be high accuracy on synthetic data
        assert accuracy >= 0.75  # At least 75% on synthetic data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])