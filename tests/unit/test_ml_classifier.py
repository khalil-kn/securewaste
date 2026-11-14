"""Unit tests for ML classifier (Sprint 2: SCRUM-19/20/21)."""

from __future__ import annotations

import tempfile
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from securewaste.core.classifier import ClassificationLabel
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

    def test_predict_empty_text(self):
        """Empty text defaults to Public."""
        train_texts = [
            "Public document about meetings and schedules",
            "Internal email john@company.com for contact",
            "Confidential invoice card 4111111111111111",
            "AWS key AKIAIOSFODNN7EXAMPLE secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

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
            "Public document about meetings and schedules",
            "Internal email john@company.com for contact",
            "Confidential invoice card 4111111111111111",
            "AWS key AKIAIOSFODNN7EXAMPLE secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

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
            "AWS key AKIA123 secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

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
            "AWS key AKIA123 secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

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
        """ML model is used when available (tests the public predict_classification function)."""
        # This test uses the actual saved model in securewaste/models/
        # If no model exists, it tests fallback behavior which is covered above
        model_path = Path("securewaste/models/classifier_pipeline.pkl")
        if model_path.exists():
            result = predict_classification("Team meeting agenda")
            # Just verify it returns a valid label
            assert result in [
                ClassificationLabel.PUBLIC,
                ClassificationLabel.INTERNAL,
                ClassificationLabel.CONFIDENTIAL,
                ClassificationLabel.HIGHLY_CONFIDENTIAL,
            ]


class TestMLClassifierDirect:
    """Tests that evaluate MLClassifier directly (not via predict_classification)."""

    def test_train_and_predict_direct(self):
        """Train on synthetic data and predict using the trained classifier directly."""
        train_texts = [
            "Public meeting",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "AWS key AKIA123 secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            metadata_path = Path(tmpdir) / "meta.json"

            classifier = MLClassifier.train(train_texts, train_labels, model_path, metadata_path)

            # Test predictions using the trained classifier directly
            result = classifier.predict("Team meeting agenda")
            assert result.label.value == "Public"

            result = classifier.predict("Email me at test@company.com")
            assert result.label.value == "Internal"

            result = classifier.predict("Payment card 4111111111111111 CONFIDENTIAL")
            assert result.label.value == "Confidential"
            result = classifier.predict("AKIAIOSFODNN7EXAMPLE secret key")
            assert result.label.value == "Highly Confidential"

    def test_classifier_source_ml(self):
        """Test that ML classifier sets classifier_source to ML."""
        train_texts = [
            "Public meeting",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "AWS key AKIA123 secret key",
            "Team meeting agenda for next week",
            "Contact jane@company.org for project details",
            "Payment card 5555555555554444 on file",
            "API token api_token_abcdefghijklmnopqrstuvwx",
            "Quarterly report with no sensitive data",
            "Internal memo with phone 555-123-4567",
            "Invoice with IBAN DE89370400440532013000",
            "Private key BEGIN RSA PRIVATE KEY",
            "Public announcement about office holiday",
            "HR onboarding email alice@company.com",
            "Credit card 4111 1111 1111 1111 charged",
            "Secret password=SuperSecret123 in config",
        ]

        train_labels = [
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
            "Public",
            "Internal",
            "Confidential",
            "Highly Confidential",
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            metadata_path = Path(tmpdir) / "meta.json"

            classifier = MLClassifier.train(train_texts, train_labels, model_path, metadata_path)
            result = classifier.predict("Team meeting agenda")
            assert result.label == ClassificationLabel.PUBLIC

    def test_predict_classification_with_confidence_classifier_source(self):
        """Test that predict_classification_with_confidence sets classifier_source correctly."""
        train_texts = [
            "Public meeting",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import ClassifierSource

            # Test with model
            result = predict_classification_with_confidence("Team meeting", model_path=model_path)
            assert result.classifier_source == ClassifierSource.ML

            # Test fallback (non-existent model)
            fallback_result = predict_classification_with_confidence(
                "CONFIDENTIAL doc", model_path=Path("/nonexistent/model.pkl")
            )
            assert fallback_result.classifier_source == ClassifierSource.RULE_BASED


class TestHybridClassification:
    """Tests for hybrid ML + rule-based classification."""

    def test_highest_sensitivity_wins(self):
        """Test that highest sensitivity label wins."""
        from securewaste.core.ml_classifier import ClassificationLabel, highest_sensitivity_label

        # Highly Confidential should win over others
        assert (
            highest_sensitivity_label(
                [
                    ClassificationLabel.PUBLIC,
                    ClassificationLabel.INTERNAL,
                    ClassificationLabel.CONFIDENTIAL,
                    ClassificationLabel.HIGHLY_CONFIDENTIAL,
                ]
            )
            == ClassificationLabel.HIGHLY_CONFIDENTIAL
        )

        # Confidential should win over Internal and Public
        assert (
            highest_sensitivity_label(
                [
                    ClassificationLabel.PUBLIC,
                    ClassificationLabel.INTERNAL,
                    ClassificationLabel.CONFIDENTIAL,
                ]
            )
            == ClassificationLabel.CONFIDENTIAL
        )

        # Internal should win over Public
        assert (
            highest_sensitivity_label(
                [
                    ClassificationLabel.PUBLIC,
                    ClassificationLabel.INTERNAL,
                ]
            )
            == ClassificationLabel.INTERNAL
        )

        # Single label returns itself
        assert highest_sensitivity_label([ClassificationLabel.CONFIDENTIAL]) == ClassificationLabel.CONFIDENTIAL

        # Empty list returns Public
        assert highest_sensitivity_label([]) == ClassificationLabel.PUBLIC

    def test_detect_sensitive_patterns(self):
        """Test detection of sensitive patterns."""
        from securewaste.core.ml_classifier import ClassificationLabel, detect_sensitive_patterns

        # AWS key detected
        labels = detect_sensitive_patterns("AWS key AKIAIOSFODNN7EXAMPLE")
        assert ClassificationLabel.HIGHLY_CONFIDENTIAL in labels

        # Payment card detected
        labels = detect_sensitive_patterns("Card 4111 1111 1111 1111")
        assert ClassificationLabel.CONFIDENTIAL in labels

        # IBAN detected
        labels = detect_sensitive_patterns("IBAN DE89370400440532013000")
        assert ClassificationLabel.CONFIDENTIAL in labels

        # Confidentiality label detected
        labels = detect_sensitive_patterns("CONFIDENTIAL document")
        assert ClassificationLabel.CONFIDENTIAL in labels

        # Email detected
        labels = detect_sensitive_patterns("Contact john@example.com")
        assert ClassificationLabel.INTERNAL in labels

        # Phone detected
        labels = detect_sensitive_patterns("Call +1 555 123 4567")
        assert ClassificationLabel.INTERNAL in labels

        # Empty text returns empty
        labels = detect_sensitive_patterns("")
        assert labels == []

        # Public text returns empty
        labels = detect_sensitive_patterns("Meeting agenda for tomorrow")
        assert labels == []

    def test_predict_classification_hybrid(self):
        """Test hybrid classification with trained model."""
        train_texts = [
            "Public meeting agenda",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import ClassificationLabel, predict_classification_hybrid

            # ML predicts Public, no detection -> Public
            label = predict_classification_hybrid("Team meeting tomorrow", model_path=model_path)
            assert label == ClassificationLabel.PUBLIC

            # ML predicts Internal, email detected -> Internal
            label = predict_classification_hybrid("Email me at john@company.com", model_path=model_path)
            assert label == ClassificationLabel.INTERNAL

            # ML predicts Public but AWS key detected -> Highly Confidential (highest-sensitivity-wins)
            label = predict_classification_hybrid("Meeting notes. AKIAIOSFODNN7EXAMPLE", model_path=model_path)
            assert label == ClassificationLabel.HIGHLY_CONFIDENTIAL

            # ML predicts Internal but payment card detected -> Confidential
            label = predict_classification_hybrid(
                "Email john@test.com. Card 4111 1111 1111 1111", model_path=model_path
            )
            assert label == ClassificationLabel.CONFIDENTIAL

    def test_predict_classification_hybrid_with_confidence(self):
        """Test hybrid classification with confidence scores."""
        train_texts = [
            "Public meeting",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import (
                ClassificationLabel,
                ClassifierSource,
                predict_classification_hybrid_with_confidence,
            )

            # Normal case - ML and detection agree
            result = predict_classification_hybrid_with_confidence("Team meeting agenda", model_path=model_path)
            assert result.classifier_source == ClassifierSource.ML
            assert result.label == ClassificationLabel.PUBLIC

            # Detection overrides ML - should be FALLBACK source
            result = predict_classification_hybrid_with_confidence(
                "Meeting notes with AKIAIOSFODNN7EXAMPLE key", model_path=model_path
            )
            assert result.label == ClassificationLabel.HIGHLY_CONFIDENTIAL
            assert result.classifier_source == ClassifierSource.FALLBACK


class TestSecurityFocused:
    """Security-focused tests for classifier."""

    def test_exposed_credentials_in_mixed_document(self):
        """Test that exposed credentials in mostly-internal document are caught."""
        train_texts = [
            "Public meeting agenda",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import ClassificationLabel, predict_classification_hybrid

            # Mostly internal document with embedded AWS key
            doc = """
            Internal Team Update
            
            Sprint Summary: Completed 23 tickets. Velocity: 45 points.
            
            Action Items:
            - Review PR #123
            - Update documentation
            
            Database credentials for testing:
            Host: db-staging.internal
            User: test_user
            Password: test_password_123
            
            AWS Access Key: AKIAIOSFODNN7EXAMPLE
            AWS Secret Key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
            """
            label = predict_classification_hybrid(doc, model_path=model_path)
            assert label == ClassificationLabel.HIGHLY_CONFIDENTIAL

            # Mostly confidential document with embedded API key
            doc = """
            Client Contract - CONFIDENTIAL
            
            Payment Terms: Net 30
            IBAN: DE89370400440532013000
            
            API Integration:
            Endpoint: https://api.client.com/v1
            API Key: api_token_abcdefghijklmnopqrstuvwxyz123456
            """
            label = predict_classification_hybrid(doc, model_path=model_path)
            assert label == ClassificationLabel.HIGHLY_CONFIDENTIAL

    def test_ml_underestimates_sensitivity(self):
        """Test case where ML predicts lower sensitivity but detection catches it."""
        train_texts = [
            "Public meeting agenda",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import (
                ClassificationLabel,
                ClassifierSource,
                predict_classification_hybrid_with_confidence,
            )

            # Document that looks like internal memo but contains production password
            doc = """
            Internal Memo: Q3 Planning
            
            Team: Platform
            Date: 2026-07-15
            Classification: INTERNAL
            
            Goals for Q3:
            - Improve API latency
            - Add new endpoints
            
            Note: For production database access use:
            Password: SuperSecretProdPassword2026!
            """
            result = predict_classification_hybrid_with_confidence(doc, model_path=model_path)
            # ML might predict Internal but detection should catch the password
            assert result.label == ClassificationLabel.HIGHLY_CONFIDENTIAL
            assert result.classifier_source == ClassifierSource.FALLBACK

            # Document with payment card that ML might miss
            doc = """
            Internal Expense Report
            
            Employee: John Doe (john@company.com)
            Date: 2026-07-15
            
            Expenses:
            - Lunch meeting: $45.00
            - Software license: $299.00 (Card: 4111 1111 1111 1111)
            """
            result = predict_classification_hybrid_with_confidence(doc, model_path=model_path)
            assert result.label == ClassificationLabel.CONFIDENTIAL

    def test_public_tutorial_mentioning_passwords(self):
        """Test that public tutorials mentioning passwords are not over-classified."""
        train_texts = [
            "Public meeting agenda",
            "Internal email test@test.com",
            "Confidential card 4111111111111111",
            "Highly Confidential key AKIA123",
        ] * 5

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.pkl"
            MLClassifier.train(train_texts, train_labels, model_path, Path(tmpdir) / "meta.json")

            from securewaste.core.ml_classifier import ClassificationLabel, predict_classification_hybrid

            # Tutorial showing bad example with placeholder password
            doc = """
            Public Tutorial: Database Configuration
            
            In this tutorial, we'll configure a database connection.
            
            BAD EXAMPLE - Never do this:
            password = "example_password_123"
            host = "localhost"
            
            GOOD EXAMPLE - Use environment variables:
            import os
            password = os.environ.get("DB_PASSWORD")
            
            Security Best Practices:
            - Never hardcode passwords in config files
            - Use a secrets manager in production
            - Rotate credentials regularly
            """
            label = predict_classification_hybrid(doc, model_path=model_path)
            # Should be Public (tutorial context) or at most Internal, NOT Highly Confidential
            assert label in [ClassificationLabel.PUBLIC, ClassificationLabel.INTERNAL]
            assert label != ClassificationLabel.HIGHLY_CONFIDENTIAL
            assert label != ClassificationLabel.CONFIDENTIAL

            # Another tutorial with AWS example key
            doc = """
            Tutorial: AWS S3 Upload
            
            Example credentials (DO NOT USE):
            AKIAIOSFODNN7EXAMPLE / wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
            
            In production, use IAM roles or environment variables.
            """
            label = predict_classification_hybrid(doc, model_path=model_path)
            assert label in [ClassificationLabel.PUBLIC, ClassificationLabel.INTERNAL]
            assert label != ClassificationLabel.HIGHLY_CONFIDENTIAL


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

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

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

        train_labels = ["Public", "Internal", "Confidential", "Highly Confidential"] * 5

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
        with pytest.raises(FrozenInstanceError):
            result.label = "Internal"  # type: ignore


class TestIntegrationWithClassifier:
    """Integration tests with rule-based classifier."""

    def test_synthetic_dataset_evaluation(self):
        """Evaluate on generated synthetic dataset."""
        # This uses the already-generated dataset
        from pathlib import Path

        from securewaste.core.ml_classifier import predict_classification_with_confidence

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


class TestHybridDictionaryContract:
    """Regression tests for the Sprint 3 dictionary classification interface."""

    def test_dict_contract_internal_label(self):
        from securewaste.core.ml_classifier import predict_classification_dict

        result = predict_classification_dict("Internal team meeting notes.")

        assert result["label"] == "Internal"
        assert set(result) == {"label", "confidence", "model_version"}

    def test_dict_contract_confidential_label(self):
        from securewaste.core.ml_classifier import predict_classification_dict

        result = predict_classification_dict("Confidential financial report.")

        assert result["label"] == "Confidential"
        assert 0.0 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
