"""
tick_features.py
----------------
Lightweight streaming feature engine for tick-by-tick analysis.
Designed for O(1) updates with minimal CPU/memory overhead.
"""

from dataclasses import dataclass, field
from collections import deque
import math
from typing import Optional, Dict, Any

@dataclass
class TickSnapshot:
    """Single tick feature snapshot"""
    game_id: str
    tick: int
    price: float
    peak: float
    ema10: float
    ema40: float
    r_mean40: float
    r_std40: float
    up_streak: int
    down_streak: int
    drawdown: float       # (peak - price)/max(peak,1)
    dist_to_peak: float   # peak/price
    since_peak: int
    hazard_scale: float   # multiplicative, in (0, 1.5] (cap)
    epr_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'game_id': self.game_id,
            'tick': self.tick,
            'price': self.price,
            'peak': self.peak,
            'ema10': round(self.ema10, 4),
            'ema40': round(self.ema40, 4),
            'r_mean40': round(self.r_mean40, 6),
            'r_std40': round(self.r_std40, 6),
            'up_streak': self.up_streak,
            'down_streak': self.down_streak,
            'drawdown': round(self.drawdown, 4),
            'dist_to_peak': round(self.dist_to_peak, 4),
            'since_peak': self.since_peak,
            'hazard_scale': round(self.hazard_scale, 3),
            'epr_active': self.epr_active
        }

class TickFeatureEngine:
    """
    Stateless feature calculator for streaming tick data.
    Maintains rolling windows and exponential moving averages.
    """
    
    def __init__(self):
        """Initialize the feature engine"""
        self._last_price: Optional[float] = None
        self._ema10 = 1.0
        self._ema40 = 1.0
        self._rbuf = deque(maxlen=40)  # Rolling buffer for returns
        self._up = 0
        self._down = 0
        self._peak_tick = 0
        self._game_id: Optional[str] = None
        
    def reset(self, game_id: str):
        """Reset for a new game"""
        self._last_price = None
        self._ema10 = 1.0
        self._ema40 = 1.0
        self._rbuf.clear()
        self._up = 0
        self._down = 0
        self._peak_tick = 0
        self._game_id = game_id
        
    def update(self, game_id: str, tick: int, price: float, peak: float, epr_active: bool) -> TickSnapshot:
        """
        Update features with new tick data.
        Returns snapshot of current features in O(1) time.
        """
        # Reset if new game
        if game_id != self._game_id:
            self.reset(game_id)
            
        # Initialize last price if needed
        if self._last_price is None:
            self._last_price = max(price, 1e-6)
        
        # Calculate log return
        r = math.log(max(price, 1e-6) / self._last_price)
        self._rbuf.append(r)
        self._last_price = max(price, 1e-6)
        
        # Update EMAs (exponential moving averages)
        a10, a40 = 0.2, 0.05  # Alpha values for EMA
        self._ema10 = (1 - a10) * self._ema10 + a10 * price
        self._ema40 = (1 - a40) * self._ema40 + a40 * price
        
        # Update streaks
        if r > 0:
            self._up += 1
            self._down = 0
        elif r < 0:
            self._down += 1
            self._up = 0
        else:
            # No change, don't reset streaks
            pass
        
        # Calculate return statistics
        if len(self._rbuf) > 0:
            r_mean = sum(self._rbuf) / len(self._rbuf)
            r_var = sum((x - r_mean) ** 2 for x in self._rbuf) / max(1, len(self._rbuf))
            r_std = math.sqrt(r_var)
        else:
            r_mean = 0.0
            r_std = 0.0
        
        # Calculate drawdown and distance to peak
        drawdown = (max(peak, price) - price) / max(peak, 1.0)
        dist_to_peak = max(peak, 1.0) / max(price, 1e-6)
        
        # Update peak tick
        if peak == price:
            self._peak_tick = tick
        since_peak = tick - self._peak_tick
        
        # Calculate hazard scale (multiplicative factor)
        scale = 1.0
        
        # Lower hazard when EPR is active
        if epr_active:
            scale *= 0.85
        
        # Lower hazard for stable periods after peak
        if since_peak > 120 and r_std < 0.02:
            scale *= 0.90
        
        # Lower hazard for strong up-streaks
        if self._up >= 8:
            scale *= 0.92
        
        # Increase hazard for strong down-streaks
        if self._down >= 8:
            scale *= 1.08
        
        # Bound the scale
        scale = min(max(scale, 0.6), 1.5)
        
        return TickSnapshot(
            game_id=game_id,
            tick=tick,
            price=price,
            peak=peak,
            ema10=self._ema10,
            ema40=self._ema40,
            r_mean40=r_mean,
            r_std40=r_std,
            up_streak=self._up,
            down_streak=self._down,
            drawdown=drawdown,
            dist_to_peak=dist_to_peak,
            since_peak=since_peak,
            hazard_scale=scale,
            epr_active=epr_active
        )
        
    def get_hazard_adjustment(self) -> float:
        """Get the current hazard scale factor"""
        # Return the last calculated scale or 1.0 if not available
        return getattr(self, '_last_scale', 1.0)