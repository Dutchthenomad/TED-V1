"""
ML-Enhanced Pattern Engine with Game-Specific Feature Engineering
Focuses ONLY on treasury patterns and game mechanics validated in the knowledge base
"""

import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import math
import statistics

logger = logging.getLogger(__name__)

@dataclass
class GameSpecificFeatures:
    """Features specific to rugs.fun game mechanics and treasury patterns"""
    pattern1_trigger_distance: float = 999.0
    pattern1_games_since: int = 999
    pattern1_recovery_probability: float = 0.0
    pattern2_ultra_short_probability: float = 0.081
    pattern2_clustering_factor: float = 1.0
    pattern2_recovery_window: int = 0
    pattern3_momentum_8x: float = 0.0
    pattern3_momentum_12x: float = 0.0
    pattern3_momentum_20x: float = 0.0
    pattern3_drought_multiplier: float = 1.0
    pattern3_games_since_moonshot: int = 999
    current_tick: int = 0
    current_multiplier: float = 1.0
    peak_multiplier: float = 1.0
    multiplier_acceleration: float = 0.0
    tick_progression_rate: float = 0.25
    tick_percentile_vs_history: float = 0.5
    duration_category: str = "normal"
    expected_rug_probability: float = 0.0005
    cumulative_survival_probability: float = 1.0
    recent_max_payout_frequency: float = 0.0
    recent_ultra_short_frequency: float = 0.0
    recent_moonshot_frequency: float = 0.0
    treasury_pressure_estimate: float = 0.5
    time_of_day_factor: float = 0.0
    session_game_position: int = 0
    consecutive_pattern_count: int = 0
    multiplier_vs_peak_ratio: float = 1.0
    time_at_current_level: int = 0
    multiplier_trajectory: str = "rising"
    estimated_player_count: int = 100
    buy_sell_ratio_estimate: float = 1.0

@dataclass
class GameAwareLearningState:
    """Learning state focused on game-specific patterns"""
    pattern_accuracy: Dict[str, float] = field(default_factory=lambda: {
        'pattern1': 0.85,
        'pattern2': 0.78,
        'pattern3': 0.91,
        'duration': 0.6,
        'treasury': 0.5
    })
    feature_weights: Dict[str, float] = field(default_factory=lambda: {
        'pattern1_distance': 0.3,
        'pattern2_clustering': 0.25,
        'pattern3_momentum': 0.35,
        'duration_percentile': 0.2,
        'treasury_pressure': 0.15,
        'drought_cycle': 0.25,
        'tick_progression': 0.1
    })
    learning_rate: float = 0.02
    prediction_history: deque = field(default_factory=lambda: deque(maxlen=100))
    accuracy_window: deque = field(default_factory=lambda: deque(maxlen=50))
    total_predictions: int = 0
    correct_predictions: int = 0

    def update_accuracy(self, prediction: float, actual: float, tolerance: float = 50.0):
        is_correct = abs(prediction - actual) <= tolerance
        self.prediction_history.append({
            'prediction': prediction,
            'actual': actual,
            'correct': is_correct,
            'error': abs(prediction - actual),
            'timestamp': datetime.now()
        })
        self.accuracy_window.append(is_correct)
        self.total_predictions += 1
        if is_correct:
            self.correct_predictions += 1
        if len(self.accuracy_window) >= 20:
            recent_accuracy = sum(self.accuracy_window) / len(self.accuracy_window)
            if recent_accuracy > 0.75:
                self.learning_rate = min(0.03, self.learning_rate * 1.02)
            elif recent_accuracy < 0.55:
                self.learning_rate = max(0.01, self.learning_rate * 0.98)

    def get_accuracy(self) -> float:
        if self.total_predictions == 0:
            return 0.6
        return self.correct_predictions / self.total_predictions

class GameSpecificFeatureExtractor:
    """Extract features specific to rugs.fun game mechanics"""
    def __init__(self, history_window: int = 25):
        self.history_window = history_window
        self.game_sequence = deque(maxlen=history_window)
        self.tick_progression_tracker = deque(maxlen=20)
        self.multiplier_history = deque(maxlen=50)
        self.PATTERN1_TRIGGER = 0.020000000000000018
        self.PATTERN2_ULTRA_SHORT_THRESHOLD = 10
        self.PATTERN2_HIGH_PAYOUT_THRESHOLD = 0.015
        self.PATTERN3_THRESHOLDS = [8, 12, 20]
        self.MOONSHOT_THRESHOLD = 50.0
        self.MEDIAN_DURATION = 205
        self.MEAN_DURATION = 225
        self.ULTRA_SHORT_PROBABILITY = 0.081

    def update_game_state(self, tick: int, multiplier: float, timestamp: datetime):
        self.tick_progression_tracker.append({'tick': tick, 'multiplier': multiplier, 'timestamp': timestamp})
        self.multiplier_history.append(multiplier)
        if len(self.multiplier_history) >= 5:
            recent_mult = list(self.multiplier_history)[-5:]
            acceleration = (recent_mult[-1] - recent_mult[0]) / 5.0
        else:
            acceleration = 0.0
        return acceleration

    def extract_features(self, current_game_state: Dict, pattern_states: Dict, game_history: List) -> GameSpecificFeatures:
        try:
            features = GameSpecificFeatures()
            current_tick = current_game_state.get('currentTick', 0)
            current_price = current_game_state.get('currentPrice', 1.0)
            peak_price = current_game_state.get('peak_price', current_price)
            features.current_tick = current_tick
            features.current_multiplier = current_price
            features.peak_multiplier = peak_price
            features.multiplier_vs_peak_ratio = current_price / peak_price if peak_price > 0 else 1.0
            pattern1_state = pattern_states.get('pattern1', {})
            features.pattern1_games_since = pattern1_state.get('games_since_trigger', 999) or 999
            features.pattern1_trigger_distance = abs(current_price - self.PATTERN1_TRIGGER)
            if features.pattern1_games_since <= 3:
                features.pattern1_recovery_probability = 0.211
            else:
                features.pattern1_recovery_probability = 0.122
            pattern2_state = pattern_states.get('pattern2', {})
            features.pattern2_ultra_short_probability = pattern2_state.get('current_game_probability', 0.081)
            features.pattern2_recovery_window = pattern2_state.get('current_recovery_window', 0)
            features.pattern2_clustering_factor = self._calculate_clustering_factor(game_history)
            pattern3_state = pattern_states.get('pattern3', {})
            current_peak = pattern3_state.get('current_peak', current_price)
            features.pattern3_momentum_8x = max(0, 8.0 - current_peak) / 8.0
            features.pattern3_momentum_12x = max(0, 12.0 - current_peak) / 12.0
            features.pattern3_momentum_20x = max(0, 20.0 - current_peak) / 20.0
            features.pattern3_games_since_moonshot = pattern3_state.get('games_since_moonshot', 999) or 999
            features.pattern3_drought_multiplier = pattern3_state.get('drought_multiplier', 1.0)
            features.tick_percentile_vs_history = self._calculate_tick_percentile(current_tick, game_history)
            features.duration_category = self._classify_duration(current_tick)
            survival_per_tick = 1.0 - 0.0005
            features.cumulative_survival_probability = survival_per_tick ** current_tick
            features.expected_rug_probability = 1.0 - survival_per_tick
            features.treasury_pressure_estimate = self._estimate_treasury_pressure(game_history)
            features.recent_max_payout_frequency = self._calculate_recent_frequency(game_history, lambda g: getattr(g, 'is_max_payout', False), 10)
            features.recent_ultra_short_frequency = self._calculate_recent_frequency(game_history, lambda g: getattr(g, 'is_ultra_short', False), 10)
            features.recent_moonshot_frequency = self._calculate_recent_frequency(game_history, lambda g: getattr(g, 'is_moonshot', False), 25)
            now = datetime.now()
            features.time_of_day_factor = (now.hour + now.minute / 60.0) / 24.0
            features.session_game_position = len(game_history) % 50
            features.consecutive_pattern_count = self._count_active_patterns(pattern_states)
            features.multiplier_acceleration = self.update_game_state(current_tick, current_price, now)
            features.multiplier_trajectory = self._analyze_trajectory()
            features.time_at_current_level = self._calculate_time_at_level()
            return features
        except Exception as e:
            logger.error(f"Error extracting game-specific features: {e}")
            return GameSpecificFeatures()

    def _calculate_clustering_factor(self, game_history: List) -> float:
        if len(game_history) < 10:
            return 1.0
        recent_games = game_history[-10:]
        ultra_short_count = sum(1 for game in recent_games if getattr(game, 'is_ultra_short', False))
        if ultra_short_count >= 3:
            return 2.0
        elif ultra_short_count >= 2:
            return 1.5
        elif ultra_short_count >= 1:
            return 1.2
        else:
            return 1.0

    def _calculate_tick_percentile(self, current_tick: int, game_history: List) -> float:
        if not game_history:
            return 0.5
        final_ticks = [getattr(game, 'final_tick', 0) for game in game_history[-100:]]
        final_ticks = [t for t in final_ticks if t > 0]
        if not final_ticks:
            return 0.5
        below_count = sum(1 for t in final_ticks if t < current_tick)
        return below_count / len(final_ticks)

    def _classify_duration(self, current_tick: int) -> str:
        if current_tick <= 10:
            return "ultra_short"
        elif current_tick <= 50:
            return "short"
        elif current_tick <= 200:
            return "normal"
        elif current_tick <= 500:
            return "extended"
        else:
            return "moonshot"

    def _estimate_treasury_pressure(self, game_history: List) -> float:
        if len(game_history) < 10:
            return 0.5
        recent_games = game_history[-10:]
        max_payout_count = sum(1 for g in recent_games if getattr(g, 'is_max_payout', False))
        moonshot_count = sum(1 for g in recent_games if getattr(g, 'is_moonshot', False))
        pressure = (max_payout_count * 0.1 + moonshot_count * 0.15) / len(recent_games)
        return max(0.0, min(1.0, pressure + 0.5))

    def _calculate_recent_frequency(self, game_history: List, condition_func, window: int) -> float:
        if len(game_history) < window:
            return 0.0
        recent_games = game_history[-window:]
        matching_count = sum(1 for game in recent_games if condition_func(game))
        return matching_count / len(recent_games)

    def _count_active_patterns(self, pattern_states: Dict) -> int:
        active_count = 0
        if pattern_states.get('pattern1', {}).get('status') in ['TRIGGERED', 'MONITORING']:
            active_count += 1
        if pattern_states.get('pattern2', {}).get('status') == 'TRIGGERED':
            active_count += 1
        if pattern_states.get('pattern3', {}).get('status') in ['APPROACHING', 'EXCEEDED']:
            active_count += 1
        return active_count

    def _analyze_trajectory(self) -> str:
        if len(self.multiplier_history) < 5:
            return "rising"
        recent = list(self.multiplier_history)[-5:]
        if recent[-1] > recent[0] * 1.05:
            return "rising"
        elif recent[-1] < recent[0] * 0.95:
            return "declining"
        else:
            return "plateau"

    def _calculate_time_at_level(self) -> int:
        if len(self.multiplier_history) < 3:
            return 0
        current_mult = self.multiplier_history[-1]
        time_at_level = 0
        for mult in reversed(list(self.multiplier_history)):
            if current_mult == 0:
                break
            if abs(mult - current_mult) / max(current_mult, 1e-9) < 0.1:
                time_at_level += 1
            else:
                break
        return time_at_level

class GameAwareLearningEngine:
    """Learning engine focused on game-specific patterns and mechanics"""
    def __init__(self):
        self.state = GameAwareLearningState()
        self.feature_importance = {}
        self.performance_tracker = deque(maxlen=200)
        self.pattern_correlation_tracker = {}

    def predict_with_features(self, features: GameSpecificFeatures, base_predictions: Dict[str, float]) -> Dict[str, Any]:
        try:
            pattern_adjustments = self._calculate_pattern_adjustments(features)
            duration_adjustment = self._calculate_duration_adjustment(features)
            treasury_adjustment = self._calculate_treasury_adjustment(features)
            weighted_prediction = 0.0
            total_weight = 0.0
            for pattern_id, prediction in base_predictions.items():
                weight = self.state.feature_weights.get(f"{pattern_id}_weight", 1.0)
                weighted_prediction += prediction * weight
                total_weight += weight
            if total_weight > 0:
                weighted_prediction /= total_weight
            ml_prediction = weighted_prediction + pattern_adjustments + duration_adjustment + treasury_adjustment
            confidence = self._calculate_game_confidence(features)
            return {
                'prediction': max(0, ml_prediction),
                'confidence': confidence,
                'base_prediction': weighted_prediction,
                'pattern_adjustments': pattern_adjustments,
                'duration_adjustment': duration_adjustment,
                'treasury_adjustment': treasury_adjustment,
                'feature_weights': dict(self.state.feature_weights),
                'key_features': self._get_key_features(features),
                'prediction_method': 'game_aware_ml'
            }
        except Exception as e:
            logger.error(f"Error in game-aware prediction: {e}")
            fallback = sum(base_predictions.values()) / len(base_predictions) if base_predictions else 200.0
            return {
                'prediction': fallback,
                'confidence': 0.5,
                'error': str(e),
                'fallback_used': True
            }

    def _calculate_pattern_adjustments(self, features: GameSpecificFeatures) -> float:
        adjustment = 0.0
        if features.pattern1_games_since <= 3:
            adjustment += 50 * (4 - features.pattern1_games_since) / 4
        if features.pattern2_clustering_factor > 1.0:
            ultra_short_boost = (features.pattern2_clustering_factor - 1.0) * -100
            adjustment += ultra_short_boost
        if features.current_multiplier >= 8:
            if features.current_multiplier >= 20:
                adjustment += 100
            elif features.current_multiplier >= 12:
                adjustment += 50
            else:
                adjustment += 30
        drought_bonus = (features.pattern3_drought_multiplier - 1.0) * 25
        adjustment += drought_bonus
        return adjustment

    def _calculate_duration_adjustment(self, features: GameSpecificFeatures) -> float:
        adjustment = 0.0
        if features.tick_percentile_vs_history > 0.8:
            adjustment += 20
        elif features.tick_percentile_vs_history < 0.2:
            adjustment -= 20
        if features.cumulative_survival_probability < 0.3:
            adjustment -= 30
        elif features.cumulative_survival_probability > 0.8:
            adjustment += 10
        return adjustment

    def _calculate_treasury_adjustment(self, features: GameSpecificFeatures) -> float:
        adjustment = 0.0
        pressure_adjustment = (features.treasury_pressure_estimate - 0.5) * -40
        adjustment += pressure_adjustment
        if features.recent_max_payout_frequency > 0.3:
            adjustment -= 25
        if features.recent_moonshot_frequency > 0.2:
            adjustment -= 35
        return adjustment

    def _calculate_game_confidence(self, features: GameSpecificFeatures) -> float:
        confidence = 0.6
        if features.pattern1_games_since <= 2:
            confidence += 0.1
        if features.pattern2_clustering_factor > 1.5:
            confidence += 0.05
        if features.current_multiplier >= 12:
            confidence += 0.15
        if features.tick_percentile_vs_history > 0.9 or features.tick_percentile_vs_history < 0.1:
            confidence += 0.1
        if features.treasury_pressure_estimate > 0.7 or features.treasury_pressure_estimate < 0.3:
            confidence += 0.05
        if features.consecutive_pattern_count >= 2:
            confidence += 0.1
        return max(0.1, min(0.95, confidence))

    def _get_key_features(self, features: GameSpecificFeatures) -> Dict[str, float]:
        return {
            'pattern1_games_since': features.pattern1_games_since,
            'pattern2_clustering': features.pattern2_clustering_factor,
            'current_multiplier': features.current_multiplier,
            'tick_percentile': features.tick_percentile_vs_history,
            'treasury_pressure': features.treasury_pressure_estimate,
            'drought_multiplier': features.pattern3_drought_multiplier,
            'survival_probability': features.cumulative_survival_probability
        }

    def update_weights(self, prediction_result: Dict, actual_outcome: float):
        try:
            prediction = prediction_result.get('prediction', 0)
            tolerance = 50.0
            self.state.update_accuracy(prediction, actual_outcome, tolerance)
            error = abs(prediction - actual_outcome)
            is_correct = error <= tolerance
            learning_rate = self.state.learning_rate
            if 'pattern_adjustments' in prediction_result:
                pattern_adj = prediction_result['pattern_adjustments']
                if (pattern_adj > 0 and actual_outcome > prediction) or (pattern_adj < 0 and actual_outcome < prediction):
                    self.state.feature_weights['pattern1_distance'] = min(0.5, self.state.feature_weights['pattern1_distance'] + learning_rate * 0.02)
                else:
                    self.state.feature_weights['pattern1_distance'] = max(0.1, self.state.feature_weights['pattern1_distance'] - learning_rate * 0.01)
            self.performance_tracker.append({
                'prediction': prediction,
                'actual': actual_outcome,
                'error': error,
                'correct': is_correct,
                'timestamp': datetime.now(),
                'learning_rate': learning_rate
            })
            logger.info(f"📈 Game-aware ML updated: accuracy={self.state.get_accuracy():.3f}, error={error:.1f}, lr={learning_rate:.4f}")
        except Exception as e:
            logger.error(f"Error updating game-aware weights: {e}")

    def get_performance_metrics(self) -> Dict:
        return {
            'overall_accuracy': self.state.get_accuracy(),
            'recent_accuracy': sum(self.state.accuracy_window) / len(self.state.accuracy_window) if self.state.accuracy_window else 0.0,
            'total_predictions': self.state.total_predictions,
            'current_learning_rate': self.state.learning_rate,
            'feature_weights': dict(self.state.feature_weights),
            'pattern_accuracy': dict(self.state.pattern_accuracy),
            'predictions_in_window': len(self.state.prediction_history),
            'prediction_method': 'game_aware_ml'
        }

class GameAwareMLPatternEngine:
    """Main engine combining treasury patterns with game-aware ML"""
    def __init__(self, base_pattern_engine):
        self.base_engine = base_pattern_engine
        self.feature_extractor = GameSpecificFeatureExtractor()
        self.learning_engine = GameAwareLearningEngine()
        self.ml_enabled = True
        self.performance_comparison = {
            'ml_predictions': [],
            'base_predictions': [],
            'ml_accuracy': 0.0,
            'base_accuracy': 0.0
        }
        self._last_prediction = None
        self._error_count = 0
        self._last_error = None

    def update_current_game(self, tick: int, price: float):
        self.base_engine.update_current_game(tick, price)
        self.feature_extractor.update_game_state(tick, price, datetime.now())

    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -> Dict:
        try:
            base_prediction = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            if not self.ml_enabled:
                self._last_prediction = base_prediction
                return base_prediction
            current_game_state = {'currentTick': current_tick, 'currentPrice': current_price, 'peak_price': peak_price}
            pattern_states = self.base_engine.pattern_states
            game_history = self.base_engine.game_history
            features = self.feature_extractor.extract_features(current_game_state, pattern_states, game_history)
            base_predictions = {
                'statistical': base_prediction.get('predicted_tick', 200),
                'pattern1': current_tick + 55 if pattern_states.get('pattern1', {}).get('status') == 'TRIGGERED' else current_tick + 25,
                'pattern2': 8 if features.pattern2_clustering_factor > 1.5 else current_tick + 30,
                'pattern3': int(current_tick * 1.2) if current_price >= 8 else current_tick + 20
            }
            ml_result = self.learning_engine.predict_with_features(features, base_predictions)
            ml_accuracy = self.learning_engine.state.get_accuracy()
            ml_weight = min(0.6, max(0.2, ml_accuracy))
            base_weight = 1.0 - ml_weight
            final_prediction = (ml_result['prediction'] * ml_weight + base_prediction['predicted_tick'] * base_weight)
            enhanced_result = {
                'predicted_tick': int(final_prediction),
                'confidence': ml_result['confidence'],
                'tolerance': base_prediction.get('tolerance', 50),
                'based_on_patterns': base_prediction.get('based_on_patterns', []) + ['game_aware_ml'],
                'ml_enhancement': {
                    'ml_prediction': ml_result['prediction'],
                    'base_prediction': base_prediction['predicted_tick'],
                    'ml_weight': ml_weight,
                    'pattern_adjustments': ml_result.get('pattern_adjustments', 0),
                    'duration_adjustment': ml_result.get('duration_adjustment', 0),
                    'treasury_adjustment': ml_result.get('treasury_adjustment', 0),
                    'key_features': ml_result.get('key_features', {}),
                    'game_features': {
                        'current_tick': features.current_tick,
                        'duration_category': features.duration_category,
                        'treasury_pressure': features.treasury_pressure_estimate,
                        'pattern_count': features.consecutive_pattern_count
                    }
                },
                'performance': self.learning_engine.get_performance_metrics()
            }
            self._last_prediction = enhanced_result
            return enhanced_result
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Error in game-aware ML prediction: {e}")
            fallback = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            fallback['ml_error'] = str(e)
            fallback['fallback_used'] = True
            self._last_prediction = fallback
            return fallback

    def complete_game_analysis(self, completed_game):
        try:
            self.base_engine.add_completed_game(completed_game)
            if self._last_prediction:
                actual_tick = completed_game.final_tick
                self.learning_engine.update_weights(self._last_prediction, actual_tick)
                self.performance_comparison['ml_predictions'].append({
                    'predicted': self._last_prediction.get('predicted_tick', 0),
                    'actual': actual_tick,
                    'game_id': completed_game.game_id
                })
                if len(self.performance_comparison['ml_predictions']) > 100:
                    self.performance_comparison['ml_predictions'] = self.performance_comparison['ml_predictions'][-100:]
                self._update_performance_comparison()
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Error in game analysis: {e}")

    def _update_performance_comparison(self):
        try:
            ml_preds = self.performance_comparison['ml_predictions'][-50:]
            if len(ml_preds) >= 10:
                ml_correct = sum(1 for p in ml_preds if abs(p['predicted'] - p['actual']) <= 50)
                self.performance_comparison['ml_accuracy'] = ml_correct / len(ml_preds)
                logger.info(f"📊 Game-aware ML Performance: {self.performance_comparison['ml_accuracy']:.3f} accuracy over {len(ml_preds)} predictions")
        except Exception as e:
            logger.error(f"Error updating performance comparison: {e}")

    def get_ml_status(self) -> Dict:
        return {
            'ml_enabled': self.ml_enabled,
            'prediction_method': 'game_aware_ml',
            'feature_extractor': {
                'game_sequence_length': len(self.feature_extractor.game_sequence),
                'multiplier_history_length': len(self.feature_extractor.multiplier_history),
                'last_trajectory': self.feature_extractor._analyze_trajectory()
            },
            'learning_engine': self.learning_engine.get_performance_metrics(),
            'performance_comparison': self.performance_comparison,
            'system_health': {
                'errors': getattr(self, '_error_count', 0),
                'last_error': getattr(self, '_last_error', None)
            }
        }

    def _store_prediction_for_evaluation(self, prediction_result):
        self._last_prediction = prediction_result