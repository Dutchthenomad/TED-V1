"""
ultra_short_gate.py
-------------------
A tiny, pluggable "ultra-short (<=10)" risk gate. You can later replace the scoring
with a proper trained classifier; the interface remains stable.
"""

from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class UltraShortGate:
    # linear weights over a few generic signals; tune via grid-search
    w_intercept: float = -1.5
    w_velocity: float = 1.2
    w_accel: float = 0.8
    w_cluster: float = 1.0
    w_drought: float = -0.4
    threshold: float = 0.6  # probability threshold to trigger the cap

    def _sigmoid(self, z: float) -> float:
        # basic logistic
        if z >= 0:
            ez = math.exp(-z)
            return 1.0 / (1.0 + ez)
        else:
            ez = math.exp(z)
            return ez / (1.0 + ez)

    def score(self, signals: Dict[str, float]) -> float:
        v = signals.get("velocity", 0.0)
        a = signals.get("acceleration", 0.0)
        c = signals.get("cluster_factor", 0.0)       # recent ultra-short clustering proxy
        d = signals.get("drought_phase", 0.0)        # higher means long since big game
        z = (self.w_intercept +
             self.w_velocity * v +
             self.w_accel * a +
             self.w_cluster * c +
             self.w_drought * d)
        return self._sigmoid(z)

    def trigger(self, signals: Dict[str, float]) -> bool:
        return self.score(signals) >= self.threshold