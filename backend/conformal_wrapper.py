"""
conformal_wrapper.py
--------------------
Online conformal "PID-like" controller for interval width. No external deps.
This wrapper doesn't compute scores; feed it whether the last prediction missed its band.
"""

from dataclasses import dataclass

@dataclass
class ConformalPID:
    target: float = 0.85          # desired coverage (in-band fraction)
    kp: float = 0.6
    ki: float = 0.05
    min_alpha: float = 0.01       # minimum miss-rate (== max coverage)
    max_alpha: float = 0.5        # maximum miss-rate (== min coverage)

    def __post_init__(self):
        # alpha is "miss rate" target (1 - coverage)
        self.alpha = 1.0 - float(self.target)
        self.I = 0.0

    def update(self, last_miss: bool) -> float:
        """
        Update controller with last decision outcome.
        last_miss=True means the true value fell *outside* the previous band.
        Returns the new alpha (estimated miss rate), in [min_alpha, max_alpha].
        """
        e = (1.0 if last_miss else 0.0) - (1.0 - self.target)  # deviation from target miss-rate
        self.I += e
        self.alpha += self.kp * e + self.ki * self.I
        # clamp
        self.alpha = max(self.min_alpha, min(self.max_alpha, self.alpha))
        return self.alpha

    def widen(self, band_ticks: int) -> int:
        """
        Produce a widened interval (tolerance in ticks) based on current alpha.
        Simple monotone mapping: more alpha -> proportionally wider.
        """
        factor = 1.0 + 2.0 * self.alpha
        widened = int(round(band_ticks * factor))
        return max(1, widened)