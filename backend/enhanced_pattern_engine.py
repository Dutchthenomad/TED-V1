"""
Enhanced Pattern Detection Engine
Implements ONLY validated treasury patterns from knowledge base
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# VALIDATED CONSTANTS FROM KNOWLEDGE BASE
TICK_DURATION_MS = 250  # Standard tick duration
MEDIAN_DURATION = 205   # Median game duration in ticks
MEAN_DURATION = 225     # Mean game duration in ticks

@dataclass
class GameRecord:
    """Game record with validated pattern markers"""
    game_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    final_tick: int = 0
    end_price: float = 0.0
    peak_price: float = 1.0
    peak_tick: int = 0
    total_duration_ms: int = 0
    
    # Validated pattern markers
    is_ultra_short: bool = False  # ≤10 ticks
    is_max_payout: bool = False   # &gt;=0.019
    is_moonshot: bool = False     # &gt;=50x
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.total_duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        
        # Validated pattern detection
        self.is_ultra_short = self.final_tick &lt;= 10
        self.is_max_payout = self.end_price &gt;= 0.019
        self.is_moonshot = self.peak_price &gt;= 50.0

@dataclass
class PatternStatistics:
    """Simple pattern tracking"""
    total_occurrences: int = 0
    successful_predictions: int = 0
    failed_predictions: int = 0
    accuracy: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)
    
    def update_accuracy(self):
        total = self.successful_predictions + self.failed_predictions
        if total &gt; 0:
            self.accuracy = self.successful_predictions / total
        self.last_updated = datetime.now()

class EnhancedPatternEngine:
    """Pattern detection using ONLY validated patterns from knowledge base"""
    
    def __init__(self):
        self.game_history: List[GameRecord] = []
        self.current_game: Optional[GameRecord] = None
        
        # Pattern 1: Post-Max-Payout Recovery (72.7% improvement)
        self.pattern1_config = {
            "trigger_threshold": 0.019,  # &gt;=0.019 is max payout
            "next_game_max_payout_prob": 0.211,  # 21.1% vs 12.2% baseline
            "duration_multiplier": 1.244,  # 24.4% longer
            "confidence": 0.85
        }
        
        # Pattern 2: Ultra-Short High-Payout (25.1% improvement)
        self.pattern2_config = {
            "ultra_short_threshold": 10,  # ≤10 ticks
            "high_payout_threshold": 0.015,
            "ultra_short_base_prob": 0.064,  # 6.4% baseline
            "post_high_payout_prob": 0.081,  # 8.1% after high payout
            "clustering_window": 10,
            "confidence": 0.78
        }
        
        # Pattern 3: Momentum Thresholds (validated thresholds only)
        self.pattern3_config = {
            "thresholds": {
                8: {"continuation_prob": 0.244, "target": 50},   # 24.4% to 50x
                12: {"continuation_prob": 0.230, "target": 100},  # 23.0% to 100x
                20: {"continuation_prob": 0.500, "target": 50}    # 50% to continue
            },
            "drought_mean": 42,  # Games between moonshots
            "drought_multipliers": {
                "normal": 1.0,    # &lt;42 games
                "elevated": 1.2,  # 42-63 games
                "high": 1.5,      # 63-84 games
                "extreme": 2.0    # &gt;84 games
            }
        }
        
        self.pattern_states = {
            "pattern1": {
                "games_since_max_payout": 999,
                "active": False
            },
            "pattern2": {
                "recent_ultra_shorts": [],
                "last_end_price": 0.0,
                "clustering_active": False
            },
            "pattern3": {
                "current_peak": 1.0,
                "games_since_moonshot": 0,
                "drought_multiplier": 1.0,
                "active_threshold": None
            }
        }
        
        self.pattern_stats = {
            "pattern1": PatternStatistics(),
            "pattern2": PatternStatistics(),
            "pattern3": PatternStatistics()
        }
    
    def add_completed_game(self, game_record: GameRecord):
        """Process completed game for pattern detection"""
        self.game_history.append(game_record)
        if len(self.game_history) &gt; 1000:
            self.game_history = self.game_history[-1000:]
        
        # Update pattern states
        self._update_pattern1(game_record)
        self._update_pattern2(game_record)
        self._update_pattern3(game_record)
        
        logger.info(f"📊 Game #{game_record.game_id}: {game_record.final_tick}t, "
                   f"End: {game_record.end_price:.3f}, Peak: {game_record.peak_price:.1f}x")
    
    def _update_pattern1(self, game: GameRecord):
        """Pattern 1: Post-Max-Payout Recovery"""
        if game.is_max_payout:
            self.pattern_states["pattern1"]["games_since_max_payout"] = 0
            self.pattern_states["pattern1"]["active"] = True
            logger.info(f"🎯 Pattern 1 TRIGGERED: Max payout {game.end_price:.3f}")
        else:
            if self.pattern_states["pattern1"]["games_since_max_payout"] &lt; 999:
                self.pattern_states["pattern1"]["games_since_max_payout"] += 1
            
            if self.pattern_states["pattern1"]["games_since_max_payout"] &gt; 3:
                self.pattern_states["pattern1"]["active"] = False
    
    def _update_pattern2(self, game: GameRecord):
        """Pattern 2: Ultra-Short High-Payout Detection"""
        # Track last game end price for prediction
        self.pattern_states["pattern2"]["last_end_price"] = game.end_price
        
        # Track ultra-short games
        if game.is_ultra_short:
            self.pattern_states["pattern2"]["recent_ultra_shorts"].append(game.game_id)
            # Keep only last 10 games
            self.pattern_states["pattern2"]["recent_ultra_shorts"] = \
                self.pattern_states["pattern2"]["recent_ultra_shorts"][-10:]
            
            # Check for clustering
            recent_count = len(self.pattern_states["pattern2"]["recent_ultra_shorts"])
            if recent_count &gt;= 2:
                self.pattern_states["pattern2"]["clustering_active"] = True
            
            logger.info(f"⚡ Ultra-short detected: {game.final_tick}t, {game.end_price:.3f}")
        else:
            # Decay clustering after non-ultra-short games
            if len(self.pattern_states["pattern2"]["recent_ultra_shorts"]) &gt; 0:
                self.pattern_states["pattern2"]["recent_ultra_shorts"].pop(0)
            if len(self.pattern_states["pattern2"]["recent_ultra_shorts"]) &lt; 2:
                self.pattern_states["pattern2"]["clustering_active"] = False
    
    def _update_pattern3(self, game: GameRecord):
        """Pattern 3: Momentum Thresholds"""
        if game.is_moonshot:
            self.pattern_states["pattern3"]["games_since_moonshot"] = 0
            logger.info(f"🚀 Moonshot detected: {game.peak_price:.1f}x")
        else:
            self.pattern_states["pattern3"]["games_since_moonshot"] += 1
        
        # Update drought multiplier
        games_since = self.pattern_states["pattern3"]["games_since_moonshot"]
        if games_since &lt; 42:
            self.pattern_states["pattern3"]["drought_multiplier"] = 1.0
        elif games_since &lt; 63:
            self.pattern_states["pattern3"]["drought_multiplier"] = 1.2
        elif games_since &lt; 84:
            self.pattern_states["pattern3"]["drought_multiplier"] = 1.5
        else:
            self.pattern_states["pattern3"]["drought_multiplier"] = 2.0
    
    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -&gt; Dict:
        """Generate prediction based on active patterns"""
        predictions = []
        active_patterns = []
        confidence_weights = []
        
        # Pattern 1: Post-Max-Payout Recovery
        if self.pattern_states["pattern1"]["active"]:
            games_since = self.pattern_states["pattern1"]["games_since_max_payout"]
            if games_since &lt;= 1:
                # Expect 24.4% longer game
                predicted = int(MEDIAN_DURATION * self.pattern1_config["duration_multiplier"])
                predictions.append(predicted)
                confidence_weights.append(self.pattern1_config["confidence"])
                active_patterns.append("pattern1_recovery")
        
        # Pattern 2: Ultra-Short Prediction
        last_price = self.pattern_states["pattern2"]["last_end_price"]
        if last_price &gt;= self.pattern2_config["high_payout_threshold"]:
            # Elevated ultra-short probability
            if current_tick &lt;= 5:  # Early game
                predictions.append(8)  # Predict ultra-short
                confidence_weights.append(self.pattern2_config["confidence"])
                active_patterns.append("pattern2_ultra_short")
        
        # Check for clustering
        if self.pattern_states["pattern2"]["clustering_active"]:
            if current_tick &lt;= 5:
                predictions.append(9)  # Predict another ultra-short
                confidence_weights.append(0.7)
                active_patterns.append("pattern2_clustering")
        
        # Pattern 3: Momentum Thresholds
        self.pattern_states["pattern3"]["current_peak"] = peak_price
        for threshold, config in self.pattern3_config["thresholds"].items():
            if peak_price &gt;= threshold:
                prob = config["continuation_prob"]
                drought_mult = self.pattern_states["pattern3"]["drought_multiplier"]
                adjusted_prob = min(0.95, prob * drought_mult)
                
                if adjusted_prob &gt; 0.3:
                    # Predict continuation
                    if threshold == 20:
                        predicted = int(current_tick * 1.5)
                    elif threshold == 12:
                        predicted = int(current_tick * 1.3)
                    else:
                        predicted = int(current_tick * 1.2)
                    
                    predictions.append(predicted)
                    confidence_weights.append(adjusted_prob)
                    active_patterns.append(f"pattern3_momentum_{threshold}x")
                break
        
        # Combine predictions
        if predictions:
            total_weight = sum(confidence_weights)
            weighted_prediction = sum(p * w for p, w in zip(predictions, confidence_weights))
            weighted_prediction /= total_weight
            avg_confidence = sum(confidence_weights) / len(confidence_weights)
            tolerance = 50
        else:
            # Default baseline
            weighted_prediction = MEDIAN_DURATION
            avg_confidence = 0.5
            tolerance = 75
            active_patterns = ["baseline"]
        
        return {
            "predicted_tick": int(weighted_prediction),
            "confidence": avg_confidence,
            "tolerance": tolerance,
            "based_on_patterns": active_patterns,
            "pattern_states": {
                "pattern1_active": self.pattern_states["pattern1"]["active"],
                "pattern2_clustering": self.pattern_states["pattern2"]["clustering_active"],
                "pattern3_peak": peak_price,
                "drought_multiplier": self.pattern_states["pattern3"]["drought_multiplier"]
            }
        }
    
    def update_current_game(self, tick: int, price: float):
        """Update current game state for live tracking"""
        if price &gt; self.pattern_states["pattern3"]["current_peak"]:
            self.pattern_states["pattern3"]["current_peak"] = price
            
            # Check for threshold crossings
            for threshold in self.pattern3_config["thresholds"].keys():
                if price &gt;= threshold and self.pattern_states["pattern3"]["active_threshold"] != threshold:
                    self.pattern_states["pattern3"]["active_threshold"] = threshold
                    logger.info(f"🎯 Momentum threshold {threshold}x reached at {price:.2f}x")
    
    def get_side_bet_recommendation(self) -&gt; Dict:
        """CRITICAL: Side bet arbitrage opportunity detection"""
        last_price = self.pattern_states["pattern2"]["last_end_price"]
        clustering = self.pattern_states["pattern2"]["clustering_active"]
        pattern1_active = self.pattern_states["pattern1"]["active"]
        
        # Calculate ultra-short probability
        base_prob = self.pattern2_config["ultra_short_base_prob"]
        
        if last_price &gt;= self.pattern2_config["high_payout_threshold"]:
            ultra_short_prob = self.pattern2_config["post_high_payout_prob"]  # 8.1%
        elif clustering:
            ultra_short_prob = base_prob * 1.5  # Clustering boost
        elif pattern1_active:
            ultra_short_prob = base_prob * 1.2  # Pattern 1 boost
        else:
            ultra_short_prob = base_prob  # 6.4%
        
        # Side bet pays 5:1 (400% profit)
        # EV = P(win) * 4.0 - P(lose) * 1.0
        expected_value = (ultra_short_prob * 4.0) - ((1 - ultra_short_prob) * 1.0)
        
        return {
            "action": "PLACE_SIDE_BET" if ultra_short_prob &gt; 0.07 else "WAIT",
            "ultra_short_probability": ultra_short_prob,
            "expected_value": expected_value,
            "confidence": ultra_short_prob,
            "reasoning": self._get_bet_reasoning(ultra_short_prob, last_price, clustering)
        }
    
    def _get_bet_reasoning(self, prob: float, last_price: float, clustering: bool) -&gt; str:
        """Explain side bet recommendation"""
        if prob &gt; 0.08:
            return f"HIGH CONFIDENCE: {prob:.1%} ultra-short probability (25% above baseline)"
        elif clustering:
            return f"CLUSTERING DETECTED: Recent ultra-shorts increase probability"
        elif last_price &gt;= 0.015:
            return f"POST-HIGH-PAYOUT: Elevated ultra-short probability"
        else:
            return f"BASELINE: {prob:.1%} probability, waiting for better opportunity"

    def get_pattern_dashboard_data(self) -&gt; Dict[str, Dict]:
        """Return a compact dashboard view for all patterns for frontend display"""
        # Pattern 1 view
        p1_active = self.pattern_states["pattern1"]["active"]
        games_since = self.pattern_states["pattern1"].get("games_since_max_payout", 999)
        p1_status = "TRIGGERED" if (p1_active and games_since &lt;= 1) else ("MONITORING" if p1_active else "NORMAL")
        baseline_max_payout = 0.122  # 12.2% baseline stated in KB
        p1 = {
            "status": p1_status,
            "confidence": self.pattern1_config["confidence"],
            "next_game_prob": self.pattern1_config["next_game_max_payout_prob"] if p1_active else baseline_max_payout,
            "last_trigger": f"{games_since}g" if p1_active else "—",
            "recovery_window": "next 1-2 games" if p1_active else "—"
        }
        
        # Pattern 2 view
        last_price = self.pattern_states["pattern2"].get("last_end_price", 0.0)
        clustering = self.pattern_states["pattern2"].get("clustering_active", False)
        base_prob = self.pattern2_config["ultra_short_base_prob"]
        if last_price &gt;= self.pattern2_config["high_payout_threshold"]:
            ultra_short_prob = self.pattern2_config["post_high_payout_prob"]
        elif clustering:
            ultra_short_prob = base_prob * 1.5
        elif p1_active:
            ultra_short_prob = base_prob * 1.2
        else:
            ultra_short_prob = base_prob
        p2_status = "TRIGGERED" if (clustering or last_price &gt;= self.pattern2_config["high_payout_threshold"]) else "NORMAL"
        p2 = {
            "status": p2_status,
            "confidence": self.pattern2_config["confidence"],
            "ultra_short_prob": ultra_short_prob,
            "recent_ultra_shorts": len(self.pattern_states["pattern2"].get("recent_ultra_shorts", [])),
            "next_alert": "early-game watch" if p2_status != "NORMAL" else "—"
        }
        
        # Pattern 3 view
        peak = self.pattern_states["pattern3"].get("current_peak", 1.0)
        drought_mult = self.pattern_states["pattern3"].get("drought_multiplier", 1.0)
        active_threshold = self.pattern_states["pattern3"].get("active_threshold")
        p3_status = "TRIGGERED" if (active_threshold is not None and active_threshold &gt;= 12) else ("APPROACHING" if peak &gt;= 8 else "NORMAL")
        p3_conf = 0.0
        for th, cfg in self.pattern3_config["thresholds"].items():
            if peak &gt;= th:
                p3_conf = max(p3_conf, min(0.95, cfg["continuation_prob"] * drought_mult))
        p3 = {
            "status": p3_status,
            "confidence": p3_conf or 0.5,
            "current_peak": peak,
            "drought_multiplier": drought_mult,
            "active_threshold": active_threshold,
            "next_alert": f"watch {12 if peak &lt; 12 else 20}x" if peak &gt;= 8 else "—"
        }
        
        return {"pattern1": p1, "pattern2": p2, "pattern3": p3}