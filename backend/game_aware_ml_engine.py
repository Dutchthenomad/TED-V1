"""
game_aware_ml_engine.py (wrapper)
---------------------------------
Backward-compatible wrapper around your existing ML engine that blends:
- Discrete-time hazard expectation/quantiles
- Ultra-short risk gate (cap extreme early overshoots)
- Online conformal PID to auto-tune tolerance
- Simple drift detector hooks

Keeps the same predict_rug_timing(...) signature and return dict keys.
"""

from typing import Dict, Any, Optional
from enhanced_pattern_engine import EnhancedPatternEngine  # existing
from ml_enhanced_engine import MLEnhancedPatternEngine    # existing

from hazard_head import DiscreteHazardHead
from conformal_wrapper import ConformalPID
from drift_detectors import SimplePageHinkley
from ultra_short_gate import UltraShortGate

class GameAwareMLPatternEngine(MLEnhancedPatternEngine):
    def __init__(self, base_pattern_engine: EnhancedPatternEngine, *, enable_hazard: bool = True, enable_gate: bool = True, enable_conformal: bool = True):
        super().__init__(base_pattern_engine)
        self.hazard = DiscreteHazardHead()
        self.conformal = ConformalPID(target=0.85)
        self.ph = SimplePageHinkley()
        self.gate = UltraShortGate()
        self.enable_hazard = enable_hazard
        self.enable_gate = enable_gate
        self.enable_conformal = enable_conformal
        self._last_prediction: Optional[Dict[str, Any]] = None

    # --- helper(s)
    def _safe_get(self, d: Dict[str, Any], key: str, default):
        try:
            return d.get(key, default)
        except Exception:
            return default

    def _collect_gate_signals(self) -> Dict[str, float]:
        """
        Pull a small set of generic signals from whatever the base engine exposes.
        These names are intentionally generic; map them to your feature extractor if available.
        """
        signals: Dict[str, float] = {}
        try:
            feats = getattr(self, "feature_extractor", None)
            if feats is not None:
                if hasattr(feats, "velocity"):
                    signals["velocity"] = float(feats.velocity())
                if hasattr(feats, "acceleration"):
                    signals["acceleration"] = float(feats.acceleration())
                if hasattr(feats, "ultra_short_cluster_factor"):
                    signals["cluster_factor"] = float(feats.ultra_short_cluster_factor())
                if hasattr(feats, "drought_phase"):
                    signals["drought_phase"] = float(feats.drought_phase())
        except Exception:
            pass
        # Defaults
        signals.setdefault("velocity", 0.0)
        signals.setdefault("acceleration", 0.0)
        signals.setdefault("cluster_factor", 0.0)
        signals.setdefault("drought_phase", 0.0)
        return signals

    def _build_hazard_logits(self, horizon: int = 40):
        """
        Build a simple per-tick logit stream for the hazard head.
        You can later replace this with a learned head. Keep cheap to compute.
        """
        logits = []
        try:
            feats = getattr(self, "feature_extractor", None)
            vol10 = 0.0
            mom = 0.0
            if feats is not None:
                if hasattr(feats, "calculate_volatility"):
                    # higher value = more stable
                    try:
                        vol10 = float(1.0 - feats.calculate_volatility(10))
                    except Exception:
                        vol10 = 0.0
                if hasattr(feats, "game_features_cache") and isinstance(feats.game_features_cache, dict):
                    mom = float(feats.game_features_cache.get('pattern_momentum', 0.0))
            for step in range(1, horizon + 1):
                z = -0.025 * step + 0.9 * vol10 + 0.35 * mom
                logits.append(z)
        except Exception:
            for step in range(1, horizon + 1):
                logits.append(-0.03 * step)
        return logits

    # --- primary API (unchanged signature)
    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -> Dict[str, Any]:
        # 1) call the existing ML engine
        base = super().predict_rug_timing(current_tick, current_price, peak_price) or {}
        pred = int(self._safe_get(base, "predicted_tick", self._safe_get(base, "prediction", 0)))
        tol  = int(self._safe_get(base, "tolerance", 65))

        # 2) hazard blend (non-destructive)
        if self.enable_hazard:
            hz = self.hazard.fold_stream(self._build_hazard_logits(horizon=40))
            # stronger pull to median when still early in the game
            w = 0.6 if current_tick <= 25 else 0.25
            pred = int(round((1.0 - w) * pred + w * int(hz["q50"])) )
            # use hazard spread to inform tolerance floor
            tol = max(tol, int(hz["q90"] - hz["q10"]))

        # 3) ultra-short gate (<= 10) to cap egregious overshoots
        if self.enable_gate and current_tick < 25:
            # Prefer explicit probability if your base model exposes one
            p_ultra = float(self._safe_get(base, "p_ultra_short", -1.0))
            if p_ultra < 0.0:  # not provided: compute ad-hoc score
                p_ultra = 0.7 if self.gate.trigger(self._collect_gate_signals()) else 0.3
            if p_ultra >= 0.6:
                pred = min(pred, min(10, current_tick + 5))
                # surface gate info
                base.setdefault("ml_enhancement", {})
                base["ml_enhancement"]["ultra_short_gate_applied"] = True
                base["ml_enhancement"]["ultra_short_prob"] = float(p_ultra)

        # 4) conformal: widen tolerance based on recent misses
        if self.enable_conformal:
            tol = self.conformal.widen(tol)

        # 5) ship result in the same dict shape
        out = dict(base)
        out["predicted_tick"] = int(pred)
        out["tolerance"] = int(tol)
        out.setdefault("confidence", float(out.get("confidence", 0.5)))
        out.setdefault("early_clamp_applied", bool(out.get("early_clamp_applied", False)))
        self._last_prediction = out
        return out

    # feedback hook; augments parent behavior
    def complete_game_analysis(self, completed_game) -> None:
        try:
            # derive a miss signal relative to the last band
            if self._last_prediction is not None and hasattr(completed_game, "final_tick"):
                pt = int(self._last_prediction.get("predicted_tick", 0))
                band = int(self._last_prediction.get("tolerance", 65))
                miss = abs(pt - int(completed_game.final_tick)) > band
                self.conformal.update(bool(miss))
                # drift on absolute error magnitude
                if self.ph.update(abs(pt - int(completed_game.final_tick))):
                    # on drift: softly widen for a few rounds by nudging alpha upward
                    self.conformal.alpha = min(self.conformal.max_alpha, self.conformal.alpha * 1.25)
        except Exception:
            pass
        # preserve original parent behavior
        try:
            return super().complete_game_analysis(completed_game)
        except Exception:
            return None

    def get_ml_status(self) -> Dict[str, Any]:
        # Build a backward-compatible status object
        parent = super().get_ml_status() if hasattr(super(), 'get_ml_status') else {}
        learning = parent.get('online_learner', parent.get('learning_metrics', {}))
        perf = {
            'accuracy': learning.get('overall_accuracy', 0.0),
            'recent_accuracy': learning.get('recent_accuracy', 0.0),
            'total_predictions': learning.get('total_predictions', 0)
        }
        status = {
            'ml_enabled': True,
            'prediction_method': 'hazard+conformal+gate',
            'learning_engine': learning,
            'performance': perf,
            'last_prediction': getattr(self, '_last_prediction', None),
            'modules': {
                'hazard': self.enable_hazard,
                'gate': self.enable_gate,
                'conformal': self.enable_conformal
            }
        }
        return status