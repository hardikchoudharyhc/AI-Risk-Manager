from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from risk_manager.verification.types import ModelExplanation


@dataclass
class MLEvidenceResult:
    score: float
    explanation: ModelExplanation
    missing_features: list[str]


class MLEvidenceModel:
    """Lightweight verifier-local ML model with optional SHAP explanations."""

    def __init__(
        self,
        feature_names: list[str],
        feature_ranges: dict[str, tuple[float, float]],
        feature_weights: dict[str, float],
        model_version: str,
        seed: int = 42,
    ):
        self.feature_names = feature_names
        self.feature_ranges = feature_ranges
        self.feature_weights = feature_weights
        self.model_version = model_version
        self.seed = seed

        self.scaler = StandardScaler()
        self.model = LogisticRegression(max_iter=500, random_state=seed)
        self._shap_ready = False
        self._shap_error: str | None = None

        self._fit_on_synthetic_distribution()

    def _fit_on_synthetic_distribution(self) -> None:
        """Fit a stable synthetic model used only for verifier evidence scoring."""
        rng = np.random.default_rng(self.seed)
        n = 1200

        X = np.zeros((n, len(self.feature_names)), dtype=float)

        for i, feature_name in enumerate(self.feature_names):
            low, high = self.feature_ranges.get(feature_name, (0.0, 1.0))
            X[:, i] = rng.uniform(low, high, size=n)

        normalized = np.zeros_like(X)
        latent = np.zeros(n, dtype=float)

        for i, feature_name in enumerate(self.feature_names):
            low, high = self.feature_ranges.get(feature_name, (0.0, 1.0))
            span = max(1e-6, high - low)
            normalized[:, i] = np.clip((X[:, i] - low) / span, 0.0, 1.0)
            latent += normalized[:, i] * self.feature_weights.get(feature_name, 0.0)

        latent += rng.normal(0.0, 0.15, size=n)
        threshold = np.quantile(latent, 0.6)
        y = (latent >= threshold).astype(int)

        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self._reference_scaled = X_scaled[:300]

        try:
            import shap  # type: ignore

            self._shap = shap
            self._shap_explainer = shap.LinearExplainer(self.model, self._reference_scaled)
            self._shap_ready = True
        except Exception as exc:  # pragma: no cover - environment dependent
            self._shap_ready = False
            self._shap_error = str(exc)

    def score_and_explain(self, feature_map: dict[str, Any]) -> MLEvidenceResult:
        x, missing_features = self._vectorize(feature_map)
        x_scaled = self.scaler.transform(x.reshape(1, -1))

        score = float(self.model.predict_proba(x_scaled)[0][1])

        if self._shap_ready:
            try:
                shap_values = self._shap_explainer.shap_values(x_scaled)
                if isinstance(shap_values, list):
                    shap_values = shap_values[1]
                values = np.asarray(shap_values).reshape(-1)
                contributions = [
                    {
                        "feature": name,
                        "value": float(x[idx]),
                        "contribution": float(values[idx]),
                        "abs_contribution": float(abs(values[idx])),
                    }
                    for idx, name in enumerate(self.feature_names)
                ]
                contributions.sort(key=lambda item: item["abs_contribution"], reverse=True)

                explanation = ModelExplanation(
                    method="shap",
                    available=True,
                    top_features=contributions[:5],
                    base_value=None,
                    model_output=score,
                    note="SHAP explanation computed from verifier-local logistic model.",
                )
            except Exception as exc:  # pragma: no cover - environment dependent
                explanation = self._coefficient_fallback(x_scaled, x, score, str(exc))
        else:
            explanation = self._coefficient_fallback(x_scaled, x, score, self._shap_error)

        return MLEvidenceResult(score=score, explanation=explanation, missing_features=missing_features)

    def _coefficient_fallback(
        self,
        x_scaled: np.ndarray,
        x_raw: np.ndarray,
        score: float,
        note: str | None,
    ) -> ModelExplanation:
        coef = np.asarray(self.model.coef_[0]).reshape(-1)
        contributions = coef * x_scaled.reshape(-1)

        ranked = [
            {
                "feature": name,
                "value": float(x_raw[idx]),
                "contribution": float(contributions[idx]),
                "abs_contribution": float(abs(contributions[idx])),
            }
            for idx, name in enumerate(self.feature_names)
        ]
        ranked.sort(key=lambda item: item["abs_contribution"], reverse=True)

        return ModelExplanation(
            method="model_coefficients",
            available=True,
            top_features=ranked[:5],
            base_value=float(self.model.intercept_[0]),
            model_output=score,
            note=(
                "SHAP unavailable; using coefficient-based contribution fallback"
                if note
                else "Coefficient-based contribution explanation"
            ),
        )

    def _vectorize(self, feature_map: dict[str, Any]) -> tuple[np.ndarray, list[str]]:
        x = np.zeros(len(self.feature_names), dtype=float)
        missing: list[str] = []

        for idx, name in enumerate(self.feature_names):
            if name not in feature_map:
                missing.append(name)
                low, high = self.feature_ranges.get(name, (0.0, 1.0))
                x[idx] = (low + high) / 2.0
                continue

            val = feature_map[name]
            if isinstance(val, bool):
                x[idx] = 1.0 if val else 0.0
            else:
                try:
                    x[idx] = float(val)
                except Exception:
                    missing.append(name)
                    low, high = self.feature_ranges.get(name, (0.0, 1.0))
                    x[idx] = (low + high) / 2.0

        return x, missing
