"""
ML-Enhanced Pattern Engine with Smart Feature Engineering and Online Learning
Additive ML layer that enhances existing statistical patterns without replacing them
"""

import numpy as np
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque
import math
import statistics
from scipy import stats  # noqa: F401  # reserved for future use

logger = logging.getLogger(__name__)

@dataclass
class MLFeatures:
    """Structured feature container for ML processing"""
    # Technical indicators
    rsi: float = 50.0
    macd: float = 0.0
    macd_signal: float = 0.0
    bb_upper: float = 1.0
    bb_lower: float = 1.0
    bb_position: float = 0.5  # 0=at lower band, 1=at upper band

    # Price momentum features
    price_momentum_5: float = 0.0   # 5-tick momentum
    price_momentum_10: float = 0.0  # 10-tick momentum
    price_acceleration: float = 0.0  # Rate of change of momentum
    volatility: float = 0.0         # Price volatility over window

    # Cross-game features
    games_since_pattern1: int = 999
    games_since_pattern2: int = 999
    games_since_moonshot: int = 999
    pattern_momentum: float = 0.0    # Combined pattern strength
    treasury_pressure: float = 0.0   # Estimated treasury pressure

    # Timing features
    tick_percentile: float = 0.0     # Current tick vs. historical distribution
    time_of_day: float = 0.0        # Hour of day (normalized 0-1)
    session_game_count: int = 0      # Games in current session

    # Player behavior proxies
    peak_to_current_ratio: float = 1.0
    price_stability: float = 0.0      # How stable price has been
    trend_strength: float = 0.0       # Strength of current trend

@dataclass
class OnlineLearningState:
    """State for online learning algorithm"""
    pattern_weights: Dict[str, float] = field(default_factory=lambda: {
        'pattern1': 1.0,
        'pattern2': 1.0,
        'pattern3': 1.0,
        'ml_features': 0.1  # Start with low weight for ML
    })
    feature_weights: Dict[str, float] = field(default_factory=dict)
    learning_rate: float = 0.01
    prediction_history: deque = field(default_factory=lambda: deque(maxlen=100))
    accuracy_window: deque = field(default_factory=lambda: deque(maxlen=50))
    total_predictions: int = 0
    correct_predictions: int = 0

    def update_accuracy(self, prediction: float, actual: float, tolerance: float = 50.0):
        """Update prediction accuracy and adjust weights"""
        is_correct = abs(prediction - actual) <= tolerance
        self.prediction_history.append({
            'prediction': prediction,
            'actual': actual,
            'correct': is_correct,
            'timestamp': datetime.now()
        })
        self.accuracy_window.append(is_correct)
        self.total_predictions += 1
        if is_correct:
            self.correct_predictions += 1
        # Adjust learning rate based on recent performance
        if len(self.accuracy_window) >= 10:
            recent_accuracy = sum(self.accuracy_window) / len(self.accuracy_window)
            if recent_accuracy > 0.7:
                self.learning_rate = min(0.02, self.learning_rate * 1.05)
            elif recent_accuracy < 0.5:
                self.learning_rate = max(0.005, self.learning_rate * 0.95)

    def get_accuracy(self) -> float:
        if self.total_predictions == 0:
            return 0.5
        return self.correct_predictions / self.total_predictions

class SmartFeatureExtractor:
    """Advanced feature extraction from game sequences"""
    def __init__(self, history_window: int = 20):
        self.history_window = history_window
        self.price_history = deque(maxlen=history_window)
        self.tick_history = deque(maxlen=history_window)
        self.game_features_cache = {}

    def update_price_history(self, price: float, tick: int):
        self.price_history.append(price)
        self.tick_history.append(tick)

    def calculate_rsi(self, period: int = 14) -> float:
        if len(self.price_history) < period + 1:
            return 50.0
        prices = list(self.price_history)[-period-1:]
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d for d in deltas if d > 0]
        losses = [-d for d in deltas if d < 0]
        if not gains or not losses:
            return 50.0
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return max(0, min(100, rsi))

    def calculate_macd(self, fast: int = 5, slow: int = 10, signal: int = 5) -> Tuple[float, float]:
        if len(self.price_history) < slow:
            return 0.0, 0.0
        prices = list(self.price_history)
        if len(prices) >= slow:
            fast_ma = sum(prices[-fast:]) / fast
            slow_ma = sum(prices[-slow:]) / slow
            macd = fast_ma - slow_ma
        else:
            macd = 0.0
        signal_line = macd * 0.8
        return macd, signal_line

    def calculate_bollinger_bands(self, period: int = 10, std_dev: int = 2) -> Tuple[float, float, float]:
        if len(self.price_history) < period:
            current_price = self.price_history[-1] if self.price_history else 1.0
            return current_price * 1.1, current_price, current_price * 0.9
        prices = list(self.price_history)[-period:]
        ma = sum(prices) / len(prices)
        variance = sum((p - ma) ** 2 for p in prices) / len(prices)
        std = math.sqrt(variance)
        upper = ma + (std_dev * std)
        lower = ma - (std_dev * std)
        return upper, ma, lower

    def calculate_momentum(self, periods: List[int]) -> List[float]:
        if len(self.price_history) < max(periods):
            return [0.0] * len(periods)
        current_price = self.price_history[-1]
        momentums = []
        for period in periods:
            if len(self.price_history) >= period + 1:
                past_price = self.price_history[-(period + 1)]
                momentum = (current_price - past_price) / past_price if past_price > 0 else 0.0
            else:
                momentum = 0.0
            momentums.append(momentum)
        return momentums

    def calculate_volatility(self, period: int = 10) -> float:
        if len(self.price_history) < period:
            return 0.0
        prices = list(self.price_history)[-period:]
        if len(prices) < 2:
            return 0.0
        returns = [(prices[i] / prices[i-1] - 1) for i in range(1, len(prices)) if prices[i-1] > 0]
        if not returns:
            return 0.0
        return statistics.stdev(returns) if len(returns) > 1 else 0.0

    def extract_features(self, current_game_state: Dict, pattern_states: Dict, game_history: List) -> MLFeatures:
        try:
            features = MLFeatures()
            features.rsi = self.calculate_rsi()
            features.macd, features.macd_signal = self.calculate_macd()
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands()
            features.bb_upper = bb_upper
            features.bb_lower = bb_lower
            current_price = current_game_state.get('currentPrice', 1.0)
            if bb_upper > bb_lower:
                features.bb_position = (current_price - bb_lower) / (bb_upper - bb_lower)
            else:
                features.bb_position = 0.5
            momentums = self.calculate_momentum([5, 10])
            features.price_momentum_5 = momentums[0] if len(momentums) > 0 else 0.0
            features.price_momentum_10 = momentums[1] if len(momentums) > 1 else 0.0
            if len(momentums) >= 2:
                features.price_acceleration = momentums[0] - momentums[1]
            features.volatility = self.calculate_volatility()
            features.games_since_pattern1 = pattern_states.get('pattern1', {}).get('games_since_trigger', 999) or 999
            features.games_since_pattern2 = self._games_since_last_ultra_short(game_history)
            features.games_since_moonshot = pattern_states.get('pattern3', {}).get('games_since_moonshot', 999) or 999
            active_patterns = 0
            if pattern_states.get('pattern1', {}).get('status') in ['TRIGGERED', 'MONITORING']:
                active_patterns += 1
            if pattern_states.get('pattern2', {}).get('status') == 'TRIGGERED':
                active_patterns += 1
            if pattern_states.get('pattern3', {}).get('status') in ['APPROACHING', 'EXCEEDED', 'DROUGHT_ELEVATED', 'DROUGHT_HIGH', 'DROUGHT_EXTREME']:
                active_patterns += 1
            features.pattern_momentum = active_patterns / 3.0
            features.treasury_pressure = self._estimate_treasury_pressure(game_history[-10:] if game_history else [])
            current_tick = current_game_state.get('currentTick', 0)
            features.tick_percentile = self._calculate_tick_percentile(current_tick, game_history)
            now = datetime.now()
            features.time_of_day = (now.hour + now.minute / 60.0) / 24.0
            features.session_game_count = len(game_history) % 100
            peak_price = current_game_state.get('peak_price', current_price)
            features.peak_to_current_ratio = current_price / peak_price if peak_price > 0 else 1.0
            features.price_stability = 1.0 / (1.0 + features.volatility)
            features.trend_strength = abs(features.price_momentum_10)
            return features
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return MLFeatures()

    def _games_since_last_ultra_short(self, game_history: List) -> int:
        if not game_history:
            return 999
        for i in range(len(game_history) - 1, -1, -1):
            game = game_history[i]
            if getattr(game, 'is_ultra_short', False):
                return len(game_history) - 1 - i
        return 999

    def _estimate_treasury_pressure(self, recent_games: List) -> float:
        if not recent_games:
            return 0.5
        high_payout_count = sum(1 for g in recent_games if getattr(g, 'is_max_payout', False))
        moonshot_count = sum(1 for g in recent_games if getattr(g, 'is_moonshot', False))
        pressure = (high_payout_count + moonshot_count * 2) / (len(recent_games) * 3)
        return max(0.0, min(1.0, pressure))

    def _calculate_tick_percentile(self, current_tick: int, game_history: List) -> float:
        if not game_history:
            return 0.0
        final_ticks = [getattr(game, 'final_tick', 0) for game in game_history[-100:]]
        final_ticks = [t for t in final_ticks if t > 0]
        if not final_ticks:
            return 0.0
        below_count = sum(1 for t in final_ticks if t < current_tick)
        return below_count / len(final_ticks)

class OnlineLearningEngine:
    """Online learning system for dynamic weight adjustment"""
    def __init__(self):
        self.state = OnlineLearningState()
        self.feature_importance = {}
        self.performance_tracker = deque(maxlen=200)

    def predict_with_features(self, features: MLFeatures, base_predictions: Dict[str, float]) -> Dict[str, Any]:
        try:
            feature_score = self._calculate_feature_score(features)
            weighted_prediction = 0.0
            total_weight = 0.0
            for pattern_id, prediction in base_predictions.items():
                weight = self.state.pattern_weights.get(pattern_id, 1.0)
                weighted_prediction += prediction * weight
                total_weight += weight
            if total_weight > 0:
                weighted_prediction /= total_weight
            ml_adjustment = feature_score * self.state.pattern_weights.get('ml_features', 0.1)
            final_prediction = weighted_prediction + ml_adjustment
            confidence = self._calculate_confidence(features, base_predictions)
            return {
                'prediction': max(0, final_prediction),
                'confidence': confidence,
                'feature_score': feature_score,
                'base_prediction': weighted_prediction,
                'ml_adjustment': ml_adjustment,
                'pattern_weights': dict(self.state.pattern_weights),
                'features_used': self._get_important_features(features)
            }
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            fallback = sum(base_predictions.values()) / len(base_predictions) if base_predictions else 200.0
            return {
                'prediction': fallback,
                'confidence': 0.5,
                'error': str(e),
                'fallback_used': True
            }

    def _calculate_feature_score(self, features: MLFeatures) -> float:
        score = 0.0
        if features.rsi > 70:
            score += 20
        elif features.rsi < 30:
            score -= 20
        if features.macd > features.macd_signal:
            score -= 10
        else:
            score += 10
        if features.bb_position > 0.8:
            score += 15
        elif features.bb_position < 0.2:
            score -= 15
        score += features.pattern_momentum * 30
        score += features.treasury_pressure * 25
        if features.volatility > 0.1:
            score += 10
        if features.peak_to_current_ratio < 0.8:
            score += 20
        return score

    def _calculate_confidence(self, features: MLFeatures, base_predictions: Dict) -> float:
        confidence = 0.5
        if len(self.state.accuracy_window) > 10:
            recent_accuracy = sum(self.state.accuracy_window) / len(self.state.accuracy_window)
            confidence = 0.3 + (recent_accuracy * 0.6)
        feature_quality = 0.0
        rsi_confidence = abs(features.rsi - 50) / 50
        feature_quality += rsi_confidence * 0.2
        feature_quality += features.pattern_momentum * 0.3
        vol_confidence = min(1.0, features.volatility * 5)
        feature_quality += vol_confidence * 0.2
        feature_quality += abs(features.treasury_pressure - 0.5) * 0.3
        confidence = min(0.95, confidence + feature_quality * 0.2)
        return max(0.1, confidence)

    def _get_important_features(self, features: MLFeatures) -> Dict[str, float]:
        return {
            'rsi': features.rsi,
            'pattern_momentum': features.pattern_momentum,
            'treasury_pressure': features.treasury_pressure,
            'volatility': features.volatility,
            'bb_position': features.bb_position,
            'peak_ratio': features.peak_to_current_ratio
        }

    def update_weights(self, prediction_result: Dict, actual_outcome: float):
        try:
            prediction = prediction_result.get('prediction', 0)
            tolerance = 50.0
            self.state.update_accuracy(prediction, actual_outcome, tolerance)
            error = abs(prediction - actual_outcome)
            is_correct = error <= tolerance
            lr = self.state.learning_rate
            if 'pattern_weights' in prediction_result:
                for pattern_id, weight in prediction_result['pattern_weights'].items():
                    if is_correct:
                        self.state.pattern_weights[pattern_id] = min(2.0, weight + lr * 0.1)
                    else:
                        self.state.pattern_weights[pattern_id] = max(0.1, weight - lr * 0.05)
            self.performance_tracker.append({
                'prediction': prediction,
                'actual': actual_outcome,
                'error': error,
                'correct': is_correct,
                'timestamp': datetime.now(),
                'learning_rate': lr
            })
            logger.info(f"📈 ML weights updated: accuracy={self.state.get_accuracy():.3f}, error={error:.1f}, lr={lr:.4f}")
        except Exception as e:
            logger.error(f"Error updating weights: {e}")

    def get_performance_metrics(self) -> Dict:
        return {
            'overall_accuracy': self.state.get_accuracy(),
            'recent_accuracy': sum(self.state.accuracy_window) / len(self.state.accuracy_window) if self.state.accuracy_window else 0.0,
            'total_predictions': self.state.total_predictions,
            'current_learning_rate': self.state.learning_rate,
            'pattern_weights': dict(self.state.pattern_weights),
            'predictions_in_window': len(self.state.prediction_history)
        }

class MLEnhancedPatternEngine:
    """Main engine that combines statistical patterns with ML enhancement"""
    def __init__(self, base_pattern_engine):
        self.base_engine = base_pattern_engine
        self.feature_extractor = SmartFeatureExtractor()
        self.online_learner = OnlineLearningEngine()
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
        self.feature_extractor.update_price_history(price, tick)

    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -> Dict:
        try:
            base_prediction = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            if not self.ml_enabled:
                self._last_prediction = base_prediction
                return base_prediction
            current_game_state = {
                'currentTick': current_tick,
                'currentPrice': current_price,
                'peak_price': peak_price
            }
            pattern_states = self.base_engine.pattern_states
            game_history = self.base_engine.game_history
            features = self.feature_extractor.extract_features(current_game_state, pattern_states, game_history)
            base_predictions = {
                'statistical': base_prediction.get('predicted_tick', 200),
                'pattern1': current_tick + 50 if pattern_states.get('pattern1', {}).get('status') == 'TRIGGERED' else current_tick + 25,
                'pattern2': 10 if pattern_states.get('pattern2', {}).get('current_game_probability', 0) > 0.15 else current_tick + 30,
                'pattern3': int(current_tick * 1.3) if peak_price >= 8 else current_tick + 20
            }
            ml_result = self.online_learner.predict_with_features(features, base_predictions)
            ml_weight = min(0.7, self.online_learner.state.get_accuracy())
            base_weight = 1.0 - ml_weight
            final_prediction = (ml_result['prediction'] * ml_weight + base_prediction['predicted_tick'] * base_weight)
            enhanced_result = {
                'predicted_tick': int(final_prediction),
                'confidence': ml_result['confidence'],
                'tolerance': base_prediction.get('tolerance', 50),
                'based_on_patterns': base_prediction.get('based_on_patterns', []) + ['ml_features'],
                'ml_enhancement': {
                    'ml_prediction': ml_result['prediction'],
                    'base_prediction': base_prediction['predicted_tick'],
                    'ml_weight': ml_weight,
                    'feature_score': ml_result.get('feature_score', 0),
                    'ml_adjustment': ml_result.get('ml_adjustment', 0),
                    'key_features': ml_result.get('features_used', {}),
                    'pattern_weights': ml_result.get('pattern_weights', {})
                },
                'performance': self.online_learner.get_performance_metrics()
            }
            self._last_prediction = enhanced_result
            return enhanced_result
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Error in ML-enhanced prediction: {e}")
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
                self.online_learner.update_weights(self._last_prediction, actual_tick)
                self.performance_comparison['ml_predictions'].append({
                    'predicted': self._last_prediction.get('predicted_tick', 0),
                    'actual': actual_tick,
                    'game_id': completed_game.game_id
                })
                if len(self.performance_comparison['ml_predictions']) > 100:
                    self.performance_comparison['ml_predictions'] = self.performance_comparison['ml_predictions'][-100:]
        except Exception as e:
            self._error_count += 1
            self._last_error = str(e)
            logger.error(f"Error in game analysis: {e}")

    def get_ml_status(self) -> Dict:
        return {
            'ml_enabled': self.ml_enabled,
            'feature_extractor': {
                'price_history_length': len(self.feature_extractor.price_history),
                'last_features': dict(self.feature_extractor.game_features_cache)
            },
            'online_learner': self.online_learner.get_performance_metrics(),
            'performance_comparison': self.performance_comparison,
            'system_health': {
                'errors': getattr(self, '_error_count', 0),
                'last_error': getattr(self, '_last_error', None)
            }
        }