"""
Enhanced Pattern Detection Engine
Implements actual treasury patterns with statistical validation
"""

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

@dataclass
class GameRecord:
    """Enhanced game record with full analytics"""
    game_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    final_tick: int = 0
    end_price: float = 0.0
    peak_price: float = 1.0
    peak_tick: int = 0
    total_duration_ms: int = 0
    is_ultra_short: bool = False
    is_max_payout: bool = False
    is_moonshot: bool = False

    def __post_init__(self):
        if self.end_time and self.start_time:
            self.total_duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        self.is_ultra_short = self.final_tick &lt;= 10
        self.is_max_payout = abs(self.end_price - 0.020000000000000018) &lt; 1e-15
        self.is_moonshot = self.peak_price &gt;= 50.0

@dataclass
class PatternStatistics:
    total_occurrences: int = 0
    successful_predictions: int = 0
    failed_predictions: int = 0
    accuracy: float = 0.0
    confidence_interval: Tuple[float, float] = (0.0, 0.0)
    last_updated: datetime = field(default_factory=datetime.now)

    def update_accuracy(self):
        total_predictions = self.successful_predictions + self.failed_predictions
        if total_predictions &gt; 0:
            self.accuracy = self.successful_predictions / total_predictions
            if total_predictions &gt;= 10:
                std_err = math.sqrt((self.accuracy * (1 - self.accuracy)) / total_predictions)
                margin = 1.96 * std_err
                self.confidence_interval = (
                    max(0, self.accuracy - margin),
                    min(1, self.accuracy + margin),
                )
        self.last_updated = datetime.now()

class EnhancedPatternEngine:
    """Advanced pattern detection with statistical models"""

    def __init__(self):
        self.game_history: List[GameRecord] = []
        self.current_game: Optional[GameRecord] = None
        self.pattern_stats = {
            "pattern1": PatternStatistics(),
            "pattern2": PatternStatistics(),
            "pattern3": PatternStatistics(),
        }

        self.pattern1_config = {
            "trigger_value": 0.020000000000000018,
            "next_game_max_payout_prob": 0.211,
            "improvement_factor": 0.727,
            "expected_duration_increase": 50,
            "confidence_threshold": 0.85,
        }

        self.pattern2_config = {
            "high_payout_threshold": 0.015,
            "ultra_short_base_prob": 0.081,
            "ultra_short_threshold_ticks": 10,
            "recovery_window_games": 3,
            "recovery_improvement": [0.15, 0.18],
            "confidence_threshold": 0.78,
        }

        self.pattern3_config = {
            "momentum_thresholds": {
                8: {"moonshot_prob": 0.244, "target_multiplier": 50},
                12: {"moonshot_prob": 0.230, "target_multiplier": 100},
                20: {"moonshot_prob": 0.500, "target_multiplier": 50},
            },
            "drought_cycle_mean": 42,
            "drought_multipliers": {
                "normal": 1.0,
                "elevated": 1.2,
                "high": 1.5,
                "extreme": 2.0,
            },
        }

        self.pattern_states = {
            "pattern1": {
                "status": "NORMAL",
                "last_trigger_game": None,
                "games_since_trigger": None,
                "next_game_prediction": None,
                "active_prediction": False,
            },
            "pattern2": {
                "status": "NORMAL",
                "recent_ultra_shorts": [],
                "current_recovery_window": 0,
                "current_game_probability": 0.081,
                "active_recovery": False,
            },
            "pattern3": {
                "status": "NORMAL",
                "current_peak": 1.0,
                "threshold_alerts": [],
                "last_moonshot_game": None,
                "games_since_moonshot": 0,
                "drought_multiplier": 1.0,
            },
        }

    def add_completed_game(self, game_record: GameRecord):
        self.game_history.append(game_record)
        if len(self.game_history) &gt; 1000:
            self.game_history = self.game_history[-1000:]
        self._analyze_pattern1_trigger(game_record)
        self._analyze_pattern2_trigger(game_record)
        self._analyze_pattern3_trigger(game_record)
        self._update_pattern_statistics()
        logger.info(
            f"\U0001F4CA Game #{game_record.game_id} analyzed: Duration: {game_record.final_tick}t, End: {game_record.end_price:.6f}, Peak: {game_record.peak_price:.2f}x"
        )

    def _analyze_pattern1_trigger(self, game: GameRecord):
        if game.is_max_payout:
            self.pattern_states["pattern1"]["last_trigger_game"] = len(self.game_history) - 1
            self.pattern_states["pattern1"]["games_since_trigger"] = 0
            self.pattern_states["pattern1"]["status"] = "TRIGGERED"
            self.pattern_states["pattern1"]["active_prediction"] = True
            logger.info(f"\U0001F3AF Pattern 1 TRIGGERED: Max payout detected {game.end_price}")
        else:
            if self.pattern_states["pattern1"].get("games_since_trigger") is not None:
                self.pattern_states["pattern1"]["games_since_trigger"] += 1
                if self.pattern_states["pattern1"]["games_since_trigger"] &gt; 3:
                    self.pattern_states["pattern1"]["status"] = "NORMAL"
                    self.pattern_states["pattern1"]["active_prediction"] = False
                elif self.pattern_states["pattern1"]["games_since_trigger"] &lt;= 2:
                    self.pattern_states["pattern1"]["status"] = "MONITORING"

    def _analyze_pattern2_trigger(self, game: GameRecord):
        if game.is_ultra_short and game.end_price &gt;= self.pattern2_config["high_payout_threshold"]:
            self.pattern_states["pattern2"]["recent_ultra_shorts"].append(
                {
                    "game_index": len(self.game_history) - 1,
                    "end_price": game.end_price,
                    "duration": game.final_tick,
                }
            )
            self.pattern_states["pattern2"]["recent_ultra_shorts"] = self.pattern_states["pattern2"][
                "recent_ultra_shorts"
            ][-10:]
            self.pattern_states["pattern2"]["status"] = "TRIGGERED"
            self.pattern_states["pattern2"]["current_recovery_window"] = 3
            self.pattern_states["pattern2"]["active_recovery"] = True
            logger.info(
                f"\u26A1 Pattern 2 TRIGGERED: Ultra-short {game.end_price} at {game.final_tick}t"
            )
        if self.pattern_states["pattern2"]["current_recovery_window"] &gt; 0:
            self.pattern_states["pattern2"]["current_recovery_window"] -= 1
            if self.pattern_states["pattern2"]["current_recovery_window"] == 0:
                self.pattern_states["pattern2"]["active_recovery"] = False
                self.pattern_states["pattern2"]["status"] = "NORMAL"
        self._update_pattern2_probability()

    def _analyze_pattern3_trigger(self, game: GameRecord):
        if game.is_moonshot:
            self.pattern_states["pattern3"]["last_moonshot_game"] = len(self.game_history) - 1
            self.pattern_states["pattern3"]["games_since_moonshot"] = 0
            logger.info(f"\U0001F680 Moonshot detected: {game.peak_price:.1f}x")
        else:
            self.pattern_states["pattern3"]["games_since_moonshot"] += 1
        self._update_drought_multiplier()

    def _update_pattern2_probability(self):
        base_prob = self.pattern2_config["ultra_short_base_prob"]
        recent_games = 10
        if len(self.game_history) &gt;= recent_games:
            recent_ultra_shorts = sum(
                1
                for game in self.game_history[-recent_games:]
                if game.is_ultra_short
                and game.end_price &gt;= self.pattern2_config["high_payout_threshold"]
            )
            if recent_ultra_shorts &gt;= 3:
                adjusted_prob = min(0.25, base_prob * 2.0)
            elif recent_ultra_shorts &gt;= 2:
                adjusted_prob = base_prob * 1.5
            elif recent_ultra_shorts == 1:
                adjusted_prob = base_prob * 1.2
            else:
                adjusted_prob = base_prob
            self.pattern_states["pattern2"]["current_game_probability"] = adjusted_prob

    def _update_drought_multiplier(self):
        games_since = self.pattern_states["pattern3"]["games_since_moonshot"]
        if games_since &lt; 42:
            multiplier = 1.0
            zone = "NORMAL"
        elif games_since &lt; 63:
            multiplier = 1.2
            zone = "ELEVATED"
        elif games_since &lt; 84:
            multiplier = 1.5
            zone = "HIGH"
        else:
            multiplier = 2.0
            zone = "EXTREME"
        self.pattern_states["pattern3"]["drought_multiplier"] = multiplier
        if zone != "NORMAL":
            self.pattern_states["pattern3"]["status"] = f"DROUGHT_{zone}"
        else:
            self.pattern_states["pattern3"]["status"] = "NORMAL"

    def _update_pattern_statistics(self):
        if len(self.game_history) &lt; 20:
            return
        pattern1_predictions = 0
        pattern1_successes = 0
        for i, game in enumerate(self.game_history[:-1]):
            if game.is_max_payout and i + 1 &lt; len(self.game_history):
                pattern1_predictions += 1
                next_game = self.game_history[i + 1]
                if (
                    next_game.final_tick &gt; 205
                    or next_game.is_max_payout
                    or next_game.peak_price &gt;= 5.0
                ):
                    pattern1_successes += 1
        if pattern1_predictions &gt; 0:
            self.pattern_stats["pattern1"].successful_predictions = pattern1_successes
            self.pattern_stats["pattern1"].failed_predictions = pattern1_predictions - pattern1_successes
            self.pattern_stats["pattern1"].update_accuracy()
        momentum_predictions = 0
        momentum_successes = 0
        for game in self.game_history:
            if game.peak_price &gt;= 8:
                momentum_predictions += 1
                if game.peak_price &gt;= 50:
                    momentum_successes += 1
        if momentum_predictions &gt; 0:
            self.pattern_stats["pattern3"].successful_predictions = momentum_successes
            self.pattern_stats["pattern3"].failed_predictions = momentum_predictions - momentum_successes
            self.pattern_stats["pattern3"].update_accuracy()

    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -&gt; Dict:
        predictions: List[int] = []
        active_patterns: List[str] = []
        confidence_factors: List[float] = []

        if self.pattern_states["pattern1"]["active_prediction"]:
            predicted_extension = max(255, current_tick + 100)
            confidence = self.pattern1_config["confidence_threshold"]
            predictions.append(predicted_extension)
            confidence_factors.append(confidence)
            active_patterns.append("pattern1")
        current_prob = self.pattern_states["pattern2"]["current_game_probability"]
        if current_prob &gt; self.pattern2_config["ultra_short_base_prob"] * 1.5:
            if current_tick &lt; 20:
                predicted_rug = min(current_tick + 5, 10)
                confidence = min(0.9, current_prob * 10)
                predictions.append(predicted_rug)
                confidence_factors.append(confidence)
                active_patterns.append("pattern2")
        for threshold, config in self.pattern3_config["momentum_thresholds"].items():
            if peak_price &gt;= threshold:
                base_prob = config["moonshot_prob"]
                drought_mult = self.pattern_states["pattern3"]["drought_multiplier"]
                adjusted_prob = min(0.95, base_prob * drought_mult)
                if adjusted_prob &gt; 0.3:
                    if threshold == 20:
                        extension_factor = 1.5
                    elif threshold == 12:
                        extension_factor = 1.3
                    else:
                        extension_factor = 1.2
                    predicted_continuation = int(current_tick * extension_factor)
                    predictions.append(predicted_continuation)
                    confidence_factors.append(adjusted_prob)
                    active_patterns.append("pattern3")
                break
        if predictions:
            total_weight = sum(confidence_factors)
            weighted_prediction = sum(
                pred * conf for pred, conf in zip(predictions, confidence_factors)
            ) / max(total_weight, 1e-9)
            if len(confidence_factors) &gt; 1:
                avg_confidence = statistics.mean(confidence_factors)
                prediction_variance = statistics.variance(predictions)
            else:
                avg_confidence = confidence_factors[0]
                prediction_variance = 2500
            tolerance = max(50, int(math.sqrt(prediction_variance)))
        else:
            weighted_prediction = max(205, current_tick + 50)
            avg_confidence = 0.5
            tolerance = 75
            active_patterns = ["baseline"]
        return {
            "predicted_tick": int(weighted_prediction),
            "confidence": avg_confidence,
            "tolerance": tolerance,
            "based_on_patterns": active_patterns,
        }

    def get_pattern_dashboard_data(self) -&gt; Dict:
        return {
            "pattern1": {
                "name": "Post-Max-Payout Recovery",
                "status": self.pattern_states["pattern1"]["status"],
                "confidence": self.pattern1_config["confidence_threshold"],
                "last_trigger": self.pattern_states["pattern1"].get("games_since_trigger"),
                "next_game_prob": self.pattern1_config["next_game_max_payout_prob"],
                "improvement_factor": self.pattern1_config["improvement_factor"],
                "accuracy": self.pattern_stats["pattern1"].accuracy,
                "total_predictions": self.pattern_stats["pattern1"].successful_predictions
                + self.pattern_stats["pattern1"].failed_predictions,
            },
            "pattern2": {
                "name": "Ultra-Short High-Payout",
                "status": self.pattern_states["pattern2"]["status"],
                "confidence": self.pattern2_config["confidence_threshold"],
                "ultra_short_prob": self.pattern2_config["ultra_short_base_prob"],
                "current_game_prob": self.pattern_states["pattern2"]["current_game_probability"],
                "recovery_window": self.pattern_states["pattern2"]["current_recovery_window"],
                "recent_events": len(self.pattern_states["pattern2"]["recent_ultra_shorts"]),
                "accuracy": self.pattern_stats["pattern2"].accuracy,
            },
            "pattern3": {
                "name": "Momentum Thresholds",
                "status": self.pattern_states["pattern3"]["status"],
                "confidence": 0.91,
                "current_peak": self.pattern_states["pattern3"]["current_peak"],
                "next_alert": self._get_next_momentum_threshold(),
                "games_since_moonshot": self.pattern_states["pattern3"]["games_since_moonshot"],
                "drought_multiplier": self.pattern_states["pattern3"]["drought_multiplier"],
                "accuracy": self.pattern_stats["pattern3"].accuracy,
                "thresholds": self.pattern3_config["momentum_thresholds"],
            },
            "system_stats": {
                "total_games_analyzed": len(self.game_history),
                "pattern1_triggers": sum(1 for g in self.game_history if g.is_max_payout),
                "pattern2_triggers": sum(1 for g in self.game_history if g.is_ultra_short),
                "pattern3_moonshots": sum(1 for g in self.game_history if g.is_moonshot),
                "analysis_window": "1000 games" if len(self.game_history) &gt;= 1000 else f"{len(self.game_history)} games",
            },
        }

    def _get_next_momentum_threshold(self) -&gt; int:
        current_peak = self.pattern_states["pattern3"]["current_peak"]
        for threshold in sorted(self.pattern3_config["momentum_thresholds"].keys()):
            if current_peak &lt; threshold:
                return threshold
        return 50

    def update_current_game(self, tick: int, price: float):
        if not self.current_game:
            return
        if price &gt; self.pattern_states["pattern3"]["current_peak"]:
            self.pattern_states["pattern3"]["current_peak"] = price
            for threshold in self.pattern3_config["momentum_thresholds"].keys():
                if (
                    self.pattern_states["pattern3"]["current_peak"] &gt;= threshold
                    and threshold not in self.pattern_states["pattern3"]["threshold_alerts"]
                ):
                    self.pattern_states["pattern3"]["threshold_alerts"].append(threshold)
                    if threshold &gt;= 12:
                        self.pattern_states["pattern3"]["status"] = "APPROACHING"
                    logger.info(
                        f"\U0001F3AF Momentum threshold {threshold}x reached at {price:.2f}x"
                    )

class IntegratedPatternTracker:
    """Enhanced pattern tracker that integrates EnhancedPatternEngine"""

    def __init__(self):
        self.enhanced_engine = EnhancedPatternEngine()
        self.current_game = None
        self.connected_clients: List = []

    def process_game_update(self, data):
        game_id = data.get("gameId", 0)
        current_tick = data.get("tickCount", 0)
        current_price = data.get("price", 1.0)
        is_active = data.get("active", True)
        is_rugged = data.get("rugged", False)
        if not self.current_game or self.current_game["gameId"] != game_id:
            if self.current_game:
                completed_game = GameRecord(
                    game_id=self.current_game["gameId"],
                    start_time=self.current_game["startTime"],
                    end_time=datetime.now(),
                    final_tick=self.current_game.get("currentTick", 0),
                    end_price=self.current_game.get("currentPrice", 0.0),
                    peak_price=self.current_game.get("peak_price", 1.0),
                )
                self.enhanced_engine.add_completed_game(completed_game)
            self.current_game = {
                "gameId": game_id,
                "startTime": datetime.now(),
                "peak_price": current_price,
            }
            self.enhanced_engine.pattern_states["pattern3"]["current_peak"] = current_price
            self.enhanced_engine.pattern_states["pattern3"]["threshold_alerts"] = []
        self.current_game.update(
            {
                "currentTick": current_tick,
                "currentPrice": current_price,
                "isActive": is_active,
                "isRugged": is_rugged,
            }
        )
        if current_price &gt; self.current_game["peak_price"]:
            self.current_game["peak_price"] = current_price
        self.enhanced_engine.update_current_game(current_tick, current_price)
        prediction = self.enhanced_engine.predict_rug_timing(
            current_tick, current_price, self.current_game["peak_price"]
        )
        patterns = self.enhanced_engine.get_pattern_dashboard_data()
        return {
            "game_state": {
                "gameId": game_id,
                "currentTick": current_tick,
                "currentPrice": current_price,
                "isActive": is_active,
                "isRugged": is_rugged,
            },
            "patterns": patterns,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat(),
            "enhanced": True,
        }