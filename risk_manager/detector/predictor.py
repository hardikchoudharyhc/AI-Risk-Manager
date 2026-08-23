"""Detector predictor for inference on new transactions."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from risk_manager.detector.model import DetectorModel, FeaturePreprocessor, CASE_TYPES


@dataclass
class DetectorPrediction:
    """Output of detector prediction."""
    case_type: str
    confidence: float
    probabilities: dict[str, float]
    model_version: str
    timestamp: str


class Predictor:
    """Load and use detector for inference."""
    
    def __init__(self, model_dir: Path, model_version: str = "1.0"):
        """Load model and preprocessor from disk."""
        self.model_dir = Path(model_dir)
        self.model_version = model_version
        
        self.detector = DetectorModel.load(self.model_dir / "model.pkl")
        self.preprocessor = FeaturePreprocessor.load(self.model_dir / "preprocessor.pkl")
    
    def predict(self, features_dict: dict) -> DetectorPrediction:
        """Predict case type from feature dict."""
        # Preprocess
        X_scaled = self.preprocessor.transform([features_dict])
        
        # Predict
        y_pred_enc = self.detector.predict(X_scaled)[0]
        y_proba = self.detector.predict_proba(X_scaled)[0]
        
        # Decode
        case_type = self.preprocessor.decode_labels(np.array([y_pred_enc]))[0]
        confidence = float(y_proba[y_pred_enc])
        
        # Build probability dict
        probs = {
            case_types: float(prob)
            for case_types, prob in zip(CASE_TYPES, y_proba)
        }
        
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        
        return DetectorPrediction(
            case_type=case_type,
            confidence=confidence,
            probabilities=probs,
            model_version=self.model_version,
            timestamp=now,
        )
