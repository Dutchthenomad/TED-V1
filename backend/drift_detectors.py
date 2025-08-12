"""
drift_detectors.py
------------------
Lightweight change-detection utilities without extra dependencies.
"""

class SimplePageHinkley:
    """
    Minimal Page-Hinkley drift detector on a univariate stream (e.g., absolute errors).
    If `update(x)` returns True, a change is suspected.
    """
    def __init__(self, delta: float = 0.005, lam: float = 50.0, alpha: float = 0.01):
        self.delta = float(delta)
        self.lam = float(lam)
        self.alpha = float(alpha)  # mean update rate
        self.reset()

    def reset(self):
        self._mean = 0.0
        self._min_cum = 0.0
        self._cum = 0.0

    def update(self, x: float) -> bool:
        self._mean += self.alpha * (x - self._mean)
        self._cum += x - self._mean - self.delta
        self._min_cum = min(self._min_cum, self._cum)
        ph_stat = self._cum - self._min_cum
        if ph_stat > self.lam:
            self.reset()
            return True
        return False