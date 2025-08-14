"""
game_aware_ml_engine.py (wrapper)
---------------------------------
Backward-compatible wrapper around your existing ML engine that blends:
- Discrete-time hazard expectation/quantiles
- Ultra-short risk gate (cap extreme early overshoots)
- Online conformal PID to auto-tune tolerance
- Simple drift detector hooks
- Early-Peak Regime (EPR) detection and adaptation

Keeps the same predict_rug_timing(...) signature and return dict keys.
"""

from typing import Dict, Any, Optional
import math
import os
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
        self._init_epr()  # Initialize Early-Peak Regime
        self._stream_scale = 1.0  # Initialize stream scale
        
    # -------- EPR: Early Peak Regime --------
    def _init_epr(self):
        self._epr = {
            "active": False,
            "first_hit_tick": None,
            "ema": 1.0,
            "sustain_ticks": 0,
            "cfg": {
                "tmax": int(os.getenv("EPR_EARLY_TICK_MAX", "120")),
                "ratio_thr": float(os.getenv("EPR_RATIO_THRESHOLD", "3.0")),
                "sustain_min": int(os.getenv("EPR_MIN_SUSTAIN_TICKS", "10")),
                "ema_alpha": float(os.getenv("EPR_BASELINE_EMA_ALPHA", "0.1")),
                "haz_scale": float(os.getenv("EPR_HAZARD_SCALE", "0.75")),
                "haz_tau": int(os.getenv("EPR_HAZARD_DECAY_TAU", "120")),
                "spread_wide": int(os.getenv("EPR_SPREAD_WIDE", "160")),
                "q_wide": float(os.getenv("EPR_QUANTILE_WIDE_SPREAD", "0.7")),
            }
        }

    def _update_epr(self, tick: int, current_mult: float, peak_mult: float):
        if not hasattr(self, "_epr"):
            self._init_epr()
        epr = self._epr
        cfg = epr["cfg"]
        # EMA baseline of multiplier (≥1.0)
        epr["ema"] = (1 - cfg["ema_alpha"]) * epr["ema"] + cfg["ema_alpha"] * max(1.0, current_mult or 1.0)
        ratio = max(1.0, (peak_mult or 1.0)) / max(1.0, epr["ema"])
        if tick <= cfg["tmax"] and ratio >= cfg["ratio_thr"]:
            epr["sustain_ticks"] += 1
            if not epr["active"] and epr["sustain_ticks"] >= cfg["sustain_min"]:
                epr["active"] = True
                epr["first_hit_tick"] = tick
        else:
            epr["sustain_ticks"] = max(0, epr["sustain_ticks"] - 1)
        return epr

    def _epr_hazard_scale(self, tick: int):
        if not hasattr(self, "_epr"):
            return 1.0
        epr = self._epr
        cfg = epr["cfg"]
        if not epr["active"] or epr["first_hit_tick"] is None:
            return 1.0
        dt = max(0, tick - epr["first_hit_tick"])
        # scale in (0,1], decays toward 1.0 as dt grows
        return cfg["haz_scale"] + (1.0 - cfg["haz_scale"]) * math.exp(-dt / max(1, cfg["haz_tau"]))
    
    def register_stream_scale(self, scale: float):
        """Register hazard scale from tick feature engine"""
        self._stream_scale = max(0.6, min(1.5, float(scale)))

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
        Apply EPR hazard scaling multiplicatively (add log(scale) to logit).
        """
        logits = []
        
        # Apply EPR and stream hazard scaling
        scale = 1.0
        if hasattr(self, "_epr"):
            # Use last known tick if available
            last_tick = getattr(self, "_last_tick", 0)
            scale = max(1e-6, self._epr_hazard_scale(last_tick))
        
        # Multiply with stream scale if available
        if hasattr(self, "_stream_scale"):
            scale *= self._stream_scale
        
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
                base = -0.025 * step + 0.9 * vol10 + 0.35 * mom
                logits.append(base + math.log(scale))
        except Exception:
            for step in range(1, horizon + 1):
                base = -0.03 * step
                logits.append(base + math.log(scale) if scale > 0 else base)
        return logits

    # --- primary API (unchanged signature)
    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -> Dict[str, Any]:
        # Update EPR state
        self._update_epr(current_tick, current_price, peak_price)
        self._last_tick = current_tick  # Store for hazard scaling
        
        # 1) call the existing ML engine
        base = super().predict_rug_timing(current_tick, current_price, peak_price) or {}
        pred = int(self._safe_get(base, "predicted_tick", self._safe_get(base, "prediction", 0)))
        tol  = int(self._safe_get(base, "tolerance", 65))

        # 2) hazard blend with EPR awareness
        if self.enable_hazard:
            hz = self.hazard.fold_stream(self._build_hazard_logits(horizon=80))
            q10, q50, q90 = int(hz["q10"]), int(hz["q50"]), int(hz["q90"])
            spread = q90 - q10
            
            # Dynamic quantile adjustment based on recent bias
            qt = 0.5
            
            # Check if quantile adjustment is enabled
            if os.getenv("QUANTILE_ADJUSTMENT_ENABLED", "false").lower() == "true":
                # Get median E40 from recent predictions (would need to be passed in or stored)
                median_e40 = getattr(self, "_median_e40", 0.0)
                
                # Apply adjustment with dead zone
                if abs(median_e40) > 0.1:  # Outside dead zone
                    # qt = 0.5 + clip(medE40, -0.3, +0.3) * 0.3
                    adjustment = max(-0.3, min(0.3, median_e40)) * 0.3
                    qt = 0.5 + adjustment
                    qt = max(0.3, min(0.8, qt))  # Bound between 0.3 and 0.8
            
            # Override with higher quantile when spread is wide or EPR is active
            if spread > self._epr["cfg"]["spread_wide"] or self._epr["active"]:
                qt = max(qt, self._epr["cfg"]["q_wide"])  # e.g., 0.7
            
            # Get the appropriate quantile
            q_key = f"q{int(qt*100)}"
            pred_tick = int(hz.get(q_key, q50))
            
            # Store the quantile used for auditing
            self._qt_used = qt
            
            # stronger pull to prediction when still early in the game
            w = 0.6 if current_tick <= 25 else 0.25
            pred = int(round((1.0 - w) * pred + w * pred_tick))
            # use hazard spread to inform tolerance floor
            tol = max(tol, spread // 2)

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

    def side_bet_signal(self, current_tick: int, current_price: float, peak_price: float) -> Dict[str, Any]:
        """
        Hazard-based side-bet signal with EPR awareness:
        - Computes P(rug within next 40 ticks) from hazard head CDF
        - EV for 5x gross payout (net +4/-1) => EV = 4*p - (1-p)
        - Action threshold defaults to 0.20 (configurable)
        - Prudent threshold bump (+0.02) when EPR is active
        """
        window = int(os.getenv("SIDEBET_WINDOW_TICKS", "40"))
        thr = float(os.getenv("SIDEBET_PWIN_THRESHOLD", "0.20"))
        
        # Update EPR state and check if active
        epr_active = False
        if hasattr(self, "_epr"):
            self._update_epr(current_tick, current_price, peak_price)
            epr_active = bool(self._epr.get("active"))
            if epr_active:
                thr = thr + 0.02  # Prudent bump in long-leaning regime
        
        # Additional bump for extreme peaks (10x+)
        if peak_price >= 10.0:
            thr = thr + 0.03  # Additional +0.03 for extreme peaks (total +0.05 if EPR also active)

        hz = self.hazard.fold_stream(self._build_hazard_logits(horizon=window))
        cdf = hz.get("cdf", [])
        # P(win in next window) = CDF[window-1]
        p_win = cdf[window - 1] if len(cdf) >= window else (cdf[-1] if cdf else 0.0)
        ev = 4.0 * p_win - (1.0 - p_win)
        action = "PLACE_SIDE_BET" if p_win > thr else "WAIT"

        signal = {
            "action": action,
            "p_win_40": p_win,           # name kept for dashboard familiarity
            "expected_value": ev,
            "confidence": max(0.5, min(0.95, p_win)),
            "tick": current_tick,
            "epr_active": epr_active,
            "threshold_used": thr,
        }
        # surface in status
        self._last_prediction = getattr(self, "_last_prediction", {}) or {}
        self._last_prediction["last_side_bet_signal"] = signal
        return signal

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