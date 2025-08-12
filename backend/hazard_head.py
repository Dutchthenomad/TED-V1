"""
hazard_head.py
--------------
Discrete-time survival (hazard) head utilities for streaming end-of-game prediction.
Non-destructive: can be blended with your existing predictor. No external deps.
"""

from typing import Iterable, Dict, List
import math

def _sigmoid(z: float) -> float:
    # numerically stable logistic
    if z >= 0:
        ez = math.exp(-z)
        return 1.0 / (1.0 + ez)
    else:
        ez = math.exp(z)
        return ez / (1.0 + ez)

class DiscreteHazardHead:
    """
    Stateless helper for folding a per-tick logit stream into survival / PMF / quantiles.

    Usage:
        logits = model_logits_iter(...)   # any iterable of per-tick logits (length up to lookahead horizon)
        stats = DiscreteHazardHead().fold_stream(logits)
        stats -> {
          "E": expected_tick (int),
          "q10","q50","q90": quantile ticks,
          "cdf": list of CDF values (1 - S_t),
          "S_tail": survival after last tick
        }

    Notes:
      - logits can be crude proxies (e.g., handcrafted) or a learned head later.
      - Keep lookahead modest (e.g., 30–120 ticks) to avoid latency.
    """

    def __init__(self, max_t: int = 1200):
        self.max_t = max_t

    def fold_stream(self, logits_iter: Iterable[float]) -> Dict[str, object]:
        S = 1.0
        exp_T = 0.0
        cdf: List[float] = []
        pmf: List[float] = []
        for t, z in enumerate(logits_iter, start=1):
            if t > self.max_t:  # hard safety cap
                break
            # hazard at tick t
            if z >= 0:
                ez = math.exp(-z)
                h = 1.0 / (1.0 + ez)
            else:
                ez = math.exp(z)
                h = ez / (1.0 + ez)
            p = h * S                     # pmf at tick t
            pmf.append(p)
            S *= (1.0 - h)                # survival to t
            exp_T += t * p
            cdf.append(1.0 - S)           # CDF at t

        def _quantile(alpha: float) -> int:
            if not cdf:
                return 1
            for idx, F in enumerate(cdf, start=1):
                if F >= alpha:
                    return idx
            return len(cdf)

        return {
            "E": int(round(exp_T)) if exp_T > 0 else len(cdf) if cdf else 1,
            "q10": _quantile(0.10),
            "q50": _quantile(0.50),
            "q90": _quantile(0.90),
            "cdf": cdf,
            "pmf": pmf,
            "S_tail": S,
        }