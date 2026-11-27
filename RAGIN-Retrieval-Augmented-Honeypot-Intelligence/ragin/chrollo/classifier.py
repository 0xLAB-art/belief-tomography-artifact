"""Random Forest behavioral classifier for attacker skill level assessment."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ragin.chrollo.features import FEATURE_NAMES, FeatureExtractor
from ragin.chrollo.features_seq import NGRAM_FEATURE_NAMES, SeqFeatureExtractor
from ragin.chrollo.models import SessionLog, SkillLevel

logger = logging.getLogger(__name__)

_MODEL_DIR = Path(os.environ.get("RAGIN_MODEL_DIR", "models/chrollo"))
_DEFAULT_MODEL_PATH = _MODEL_DIR / "rf_classifier.joblib"
_DEFAULT_SCALER_PATH = _MODEL_DIR / "scaler.joblib"

# Label mapping (matches Rust gateway SkillLevel enum order)
_LABEL_MAP = {
    SkillLevel.NOVICE: 0,
    SkillLevel.INTERMEDIATE: 1,
    SkillLevel.EXPERT: 2,
    SkillLevel.APT: 3,
}
_LABEL_INV = {v: k for k, v in _LABEL_MAP.items()}


@dataclass
class ClassificationResult:
    skill_level: SkillLevel
    confidence: float
    features_used: list[str]
    session_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    feature_values: dict[str, float] = field(default_factory=dict)
    # Additive Jev System One assessment (never required; None when unused).
    jev_assessment: dict | None = None

    @property
    def label(self) -> str:
        return self.skill_level.value


# Supported feature sets. "baseline" is the original 10-feature vector;
# "baseline+ngram" adds the 32 hashed command n-gram features (the only
# sequence family that improved accuracy across all three benchmark
# regimes — see results/model_quality/seq_features_benchmark.json).
FEATURE_SETS: dict[str, list[str]] = {
    "baseline": list(FEATURE_NAMES),
    "baseline+ngram": list(FEATURE_NAMES) + list(NGRAM_FEATURE_NAMES),
}


class ChrolloClassifier:
    """Random Forest classifier for honeypot session skill-level assessment.

    Trained on the synthetic four-tier dataset in data/training/
    (2,000 sessions, 500 per tier; scripts/generate_training_data.py) and
    tuned via out-of-fold search (scripts/tune_chrollo.py): 500 trees,
    max_depth=16, unweighted — 0.8875 held-out accuracy (n=400, Wilson 95%
    CI [0.853, 0.914]) with adjacent-tier confusion only. Reproducible
    metrics: models/chrollo/training_manifest.json and tuning_manifest.json.

    Args:
        model_path: where the RF model artifact lives.
        feature_set: key into ``FEATURE_SETS`` used when *training*. At
            inference time the active list is whatever was persisted next
            to the model (falling back to the artifact's actual feature
            count), so old artifacts keep working unchanged.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        feature_set: str = "baseline",
    ) -> None:
        if feature_set not in FEATURE_SETS:
            raise ValueError(f"Unknown feature_set {feature_set!r}; expected one of {sorted(FEATURE_SETS)}")
        self._feature_set = feature_set
        self._feature_names: list[str] = list(FEATURE_SETS[feature_set])
        self._extractor = SeqFeatureExtractor() if feature_set == "baseline+ngram" else FeatureExtractor()
        self._scaler: StandardScaler | None = None
        self._model: RandomForestClassifier | None = None
        self._model_path = Path(model_path) if model_path else _DEFAULT_MODEL_PATH
        self._loaded = False

        if self._model_path.exists():
            self._load()

    # ── Public API ───────────────────────────────────────────────────────

    def train(
        self,
        training_data: list[tuple[SessionLog, SkillLevel]],
        *,
        n_estimators: int = 200,
        max_depth: int = 20,
        min_samples_split: int = 5,
        cv_folds: int = 5,
        class_weight: str | dict[int, float] | None = "balanced",
        min_samples_leaf: int = 1,
        max_features: str | float = "sqrt",
    ) -> dict[str, float]:
        """Train the classifier on labeled session logs.

        Args:
            training_data: List of (SessionLog, SkillLevel) pairs.
            n_estimators: Number of trees in the forest.
            max_depth: Maximum tree depth.
            min_samples_split: Minimum samples to split a node.
            cv_folds: Cross-validation folds for scoring.
            class_weight: "balanced" or a per-class weight dict keyed by
                integer label (0=novice, 1=intermediate, 2=expert, 3=apt).
            min_samples_leaf: Minimum samples per leaf.
            max_features: Features considered per split ("sqrt", 0.5, ...).

        Returns:
            Dictionary with training metrics (accuracy, std, etc.).
        """
        if len(training_data) < 10:
            raise ValueError("Need at least 10 training samples")

        # Training always uses the feature set requested at construction,
        # regardless of what any previously-loaded artifact was trained with
        # (the constructor's _load() re-binds the extractor for inference).
        self._feature_names = list(FEATURE_SETS[self._feature_set])
        self._extractor = SeqFeatureExtractor() if self._feature_set == "baseline+ngram" else FeatureExtractor()

        X, y = self._prepare_data(training_data)

        rf_kwargs: dict = dict(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            max_features=max_features,
            class_weight=class_weight,
            random_state=42,
            n_jobs=-1,
        )

        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)

        self._model = RandomForestClassifier(**rf_kwargs)

        self._model.fit(X_scaled, y)

        # Cross-validation: wrap scaler+model in a Pipeline so each fold
        # fits its own scaling statistics (no leakage from the full-data
        # standardization used for the final model).
        counts = np.bincount(y) if len(y) else np.array([])
        present = counts[counts > 0]
        min_class = int(present.min()) if len(present) else 0
        n_splits = min(cv_folds, min_class)
        if n_splits >= 2:
            pipeline = Pipeline([("scaler", StandardScaler()), ("rf", RandomForestClassifier(**rf_kwargs))])
            cv_scores = cross_val_score(pipeline, X, y, cv=n_splits, scoring="accuracy")
        else:
            cv_scores = np.array([float("nan")])

        metrics = {
            "accuracy": float(cv_scores.mean()),
            "accuracy_std": float(cv_scores.std()),
            "n_estimators": float(n_estimators),
            "n_samples": float(len(y)),
            "n_features": float(X.shape[1]),
        }

        logger.info(
            "Chrollo trained: accuracy=%.3f ± %.3f (%d samples)",
            metrics["accuracy"],
            metrics["accuracy_std"],
            len(y),
        )

        self._save()
        self._loaded = True
        return metrics

    def classify(self, session_log: SessionLog) -> ClassificationResult:
        """Classify a session log and return skill-level with confidence."""
        if not self._loaded or self._model is None:
            raise RuntimeError("Model not loaded. Call train() first or provide a valid model_path.")
        if len(self._model.classes_) == 1:
            logger.warning(
                "Chrollo model is single-class (classes_=%s): every session "
                "will be classified %s. Retrain on multi-class data for real "
                "skill stratification.",
                self._model.classes_,
                _LABEL_INV.get(int(self._model.classes_[0]), "?"),
            )

        features = self._extractor.extract(session_log)
        X = np.array([[features[f] for f in self._feature_names]])
        X_scaled = X if self._scaler is None else self._scaler.transform(X)

        prediction = int(self._model.predict(X_scaled)[0])
        probabilities = self._model.predict_proba(X_scaled)[0]

        skill_level = _LABEL_INV[prediction]
        # predict_proba columns correspond to classes_ which may be a subset
        # of all 4 labels when training data doesn't cover every class.
        class_index = list(self._model.classes_).index(prediction)
        confidence = float(probabilities[class_index])

        # Top-2 margin for additional confidence context
        sorted_probs = sorted(probabilities, reverse=True)
        margin = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 1.0

        # If margin is tiny, cap confidence to signal uncertainty
        if margin < 0.05:
            confidence = min(confidence, 0.6)

        return ClassificationResult(
            skill_level=skill_level,
            confidence=round(confidence, 4),
            features_used=list(self._feature_names),
            session_id=session_log.session_id,
            feature_values=features,
        )

    def get_feature_importance(self) -> dict[str, float]:
        """Return per-feature importance from the trained Random Forest."""
        if self._model is None:
            return {}

        importances = self._model.feature_importances_
        return {name: round(float(imp), 6) for name, imp in zip(self._feature_names, importances, strict=False)}

    # ── Persistence ──────────────────────────────────────────────────────

    def _save(self) -> None:
        self._model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self._model, self._model_path)
        joblib.dump(self._scaler, self._model_path.with_suffix(".scaler.joblib"))
        joblib.dump(self._feature_names, self._model_path.with_suffix(".features.joblib"))
        logger.info("Model saved to %s", self._model_path)

    def _load(self) -> None:
        try:
            self._model = joblib.load(self._model_path)
            scaler_path = self._model_path.with_suffix(".scaler.joblib")
            if scaler_path.exists():
                self._scaler = joblib.load(scaler_path)
            else:
                self._scaler = StandardScaler()
            # Feature names persisted with the artifact win; fall back to the
            # requested set, then to whatever the model dimensionality says
            # (legacy artifacts trained on the baseline 10 features).
            features_path = self._model_path.with_suffix(".features.joblib")
            if features_path.exists():
                self._feature_names = list(joblib.load(features_path))
                self._extractor = (
                    SeqFeatureExtractor()
                    if any(f.startswith("ngram_") for f in self._feature_names)
                    else FeatureExtractor()
                )
            elif self._model is not None and self._model.n_features_in_ != len(self._feature_names):
                self._feature_names = list(FEATURE_NAMES)
                self._extractor = FeatureExtractor()
            self._loaded = True
            logger.info("Model loaded from %s (%d features)", self._model_path, len(self._feature_names))
        except Exception as e:
            logger.warning("Failed to load model from %s: %s", self._model_path, e)
            self._loaded = False

    # ── Internal ─────────────────────────────────────────────────────────

    def _prepare_data(self, data: list[tuple[SessionLog, SkillLevel]]) -> tuple[np.ndarray, np.ndarray]:
        X_rows = []
        y_labels = []
        for session, label in data:
            features = self._extractor.extract(session)
            X_rows.append([features[f] for f in self._feature_names])
            y_labels.append(_LABEL_MAP[label])
        return np.array(X_rows, dtype=np.float32), np.array(y_labels, dtype=np.int32)
