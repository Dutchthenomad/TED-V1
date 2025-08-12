"""
ML-Enhanced Pattern Engine - Simplified and Focused
Only uses validated patterns, no trading indicators
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import statistics

logger = logging.getLogger(__name__)

# VALIDATED CONSTANTS
TICK_DURATION_MS = 250
MEDIAN_DURATION = 205
ULTRA_SHORT_THRESHOLD = 10

@dataclass
class ValidatedFeatures:
    """Only features validated in knowledge base"""
    # Pattern 1 features
    pattern1_triggered: bool = False
    games_since_pattern1: int = 999
    
    # Pattern 2 features
    last_game_ultra_short: bool = False
    last_game_end_price: float = 0.0
    ultra_short_cluster_count: int = 0
    
    # Pattern 3 features
    current_peak: float = 1.0
    crossed_8x: bool = False
    crossed_12x: bool = False
    crossed_20x: bool = False
    games_since_moonshot: int = 999
    
    # Basic game state
    current_tick: int = 0
    current_multiplier: float = 1.0
    tick_percentile: float = 0.5

@dataclass
class SimpleLearningState:
    """Simplified learning without complex ML"""
    pattern_weights: Dict[str, float] = field(default_factory=lambda: {
        'pattern1': 0.85,  # High confidence from validation
        'pattern2': 0.78,  # Medium-high confidence
        'pattern3': 0.91,  # Highest confidence
        'baseline': 0.5    # Default weight
    })
    
    prediction_history: deque = field(default_factory=lambda: deque(maxlen=100))
    accuracy_window: deque = field(default_factory=lambda: deque(maxlen=50))
    total_predictions: int = 0
    correct_predictions: int = 0
    
    def update_accuracy(self, prediction: float, actual: float, tolerance: float = 50.0):
        """Track prediction accuracy"""
        is_correct = abs(prediction - actual) <= tolerance
        self.accuracy_window.append(is_correct)
        self.total_predictions += 1
        if is_correct:
            self.correct_predictions += 1
        
        # Simple weight adjustment based on recent performance
        if len(self.accuracy_window) &gt;= 20:
            recent_accuracy = sum(self.accuracy_window) / len(self.accuracy_window)
            # Adjust pattern weights slightly based on performance
            if recent_accuracy &gt; 0.7:
                # Performing well, slightly increase weights
                for key in self.pattern_weights:
                    if key != 'baseline':
                        self.pattern_weights[key] = min(0.95, self.pattern_weights[key] * 1.01)
            elif recent_accuracy < 0.5:
                # Underperforming, slightly decrease weights
                for key in self.pattern_weights:
                    if key != 'baseline':
                        self.pattern_weights[key] = max(0.5, self.pattern_weights[key] * 0.99)
    
    def get_accuracy(self) -&gt; float:
        if self.total_predictions == 0:
            return 0.5
        return self.correct_predictions / self.total_predictions

class ValidatedFeatureExtractor:
    """Extract only validated features from game data"""
    
    def __init__(self):
        self.game_history = deque(maxlen=100)
        self.tick_history = deque(maxlen=100)
    
    def extract_features(self, current_game_state: Dict, pattern_states: Dict, 
                        game_history: List) -&gt; ValidatedFeatures:
        """Extract only validated features"""
        features = ValidatedFeatures()
        
        # Basic game state
        features.current_tick = current_game_state.get('currentTick', 0)
        features.current_multiplier = current_game_state.get('currentPrice', 1.0)
        features.current_peak = current_game_state.get('peak_price', 1.0)
        
        # Pattern 1 features
        pattern1_state = pattern_states.get('pattern1', {})
        features.games_since_pattern1 = pattern1_state.get('games_since_max_payout', 999)
        features.pattern1_triggered = features.games_since_pattern1 &lt;= 1
        
        # Pattern 2 features
        pattern2_state = pattern_states.get('pattern2', {})
        features.last_game_end_price = pattern2_state.get('last_end_price', 0.0)
        recent_ultra_shorts = pattern2_state.get('recent_ultra_shorts', [])
        features.ultra_short_cluster_count = len(recent_ultra_shorts)
        features.last_game_ultra_short = len(recent_ultra_shorts) &gt; 0
        
        # Pattern 3 features
        features.crossed_8x = features.current_peak &gt;= 8
        features.crossed_12x = features.current_peak &gt;= 12
        features.crossed_20x = features.current_peak &gt;= 20
        pattern3_state = pattern_states.get('pattern3', {})
        features.games_since_moonshot = pattern3_state.get('games_since_moonshot', 999)
        
        # Calculate tick percentile
        if game_history and len(game_history) &gt; 10:
            final_ticks = [getattr(g, 'final_tick', 0) for g in game_history[-100:]]
            final_ticks = [t for t in final_ticks if t &gt; 0]
            if final_ticks:
                below_count = sum(1 for t in final_ticks if t &lt; features.current_tick)
                features.tick_percentile = below_count / len(final_ticks)
        
        return features

class SimpleLearningEngine:
    """Simplified learning focused on pattern combination"""
    
    def __init__(self):
        self.state = SimpleLearningState()
        self.performance_tracker = deque(maxlen=200)
    
    def predict_with_features(self, features: ValidatedFeatures, base_predictions: Dict[str, float]) -&gt; Dict:
        """Combine pattern predictions with simple weighting"""
        try:
            # Calculate pattern-based adjustments
            adjustments = self._calculate_pattern_adjustments(features)
            
            # Weight base predictions
            weighted_prediction = 0.0
            total_weight = 0.0
            
            for pattern_id, prediction in base_predictions.items():
                weight = self.state.pattern_weights.get(pattern_id, 0.5)
                weighted_prediction += prediction * weight
                total_weight += weight
            
            if total_weight &gt; 0:
                weighted_prediction /= total_weight
            
            # Apply pattern adjustments
            final_prediction = weighted_prediction + adjustments
            
            # Calculate confidence based on active patterns
            confidence = self._calculate_confidence(features)
            
            return {
                'prediction': max(0, final_prediction),
                'confidence': confidence,
                'base_prediction': weighted_prediction,
                'adjustments': adjustments,
                'pattern_weights': dict(self.state.pattern_weights),
                'active_patterns': self._get_active_patterns(features)
            }
            
        except Exception as e:
            logger.error(f"Error in prediction: {e}")
            # Fallback to median duration
            return {
                'prediction': MEDIAN_DURATION,
                'confidence': 0.5,
                'error': str(e),
                'fallback_used': True
            }
    
    def _calculate_pattern_adjustments(self, features: ValidatedFeatures) -&gt; float:
        """Calculate adjustments based on validated patterns"""
        adjustment = 0.0
        
        # Pattern 1: Post-max-payout recovery
        if features.pattern1_triggered:
            # Expect 24.4% longer games
            adjustment += MEDIAN_DURATION * 0.244
        
        # Pattern 2: Ultra-short clustering
        if features.ultra_short_cluster_count &gt;= 2:
            # High clustering, expect more ultra-shorts
            adjustment -= (features.current_tick * 0.5)  # Predict shorter
        elif features.last_game_end_price &gt;= 0.015:
            # Post-high-payout, slight ultra-short boost
            adjustment -= 20
        
        # Pattern 3: Momentum thresholds
        if features.crossed_20x:
            # 50% chance of continuation
            adjustment += features.current_tick * 0.5
        elif features.crossed_12x:
            # 23% chance of reaching 100x
            adjustment += features.current_tick * 0.3
        elif features.crossed_8x:
            # 24.4% chance of reaching 50x
            adjustment += features.current_tick * 0.2
        
        # Drought effect
        if features.games_since_moonshot &gt; 84:
            adjustment *= 1.5  # Extreme drought multiplier
        elif features.games_since_moonshot &gt; 63:
            adjustment *= 1.3  # High drought
        elif features.games_since_moonshot &gt; 42:
            adjustment *= 1.1  # Elevated drought
        
        return adjustment
    
    def _calculate_confidence(self, features: ValidatedFeatures) -&gt; float:
        """Calculate confidence based on active patterns"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for active patterns
        if features.pattern1_triggered:
            confidence += 0.15
        
        if features.ultra_short_cluster_count &gt;= 2:
            confidence += 0.1
        
        if features.crossed_8x or features.crossed_12x or features.crossed_20x:
            confidence += 0.2
        
        # Adjust for accuracy
        if self.state.total_predictions &gt; 20:
            accuracy_bonus = (self.state.get_accuracy() - 0.5) * 0.3
            confidence += accuracy_bonus
        
        return max(0.1, min(0.95, confidence))
    
    def _get_active_patterns(self, features: ValidatedFeatures) -&gt; List[str]:
        """Identify active patterns"""
        active = []
        
        if features.pattern1_triggered:
            active.append("pattern1_recovery")
        
        if features.ultra_short_cluster_count &gt;= 2:
            active.append("pattern2_clustering")
        elif features.last_game_end_price &gt;= 0.015:
            active.append("pattern2_post_high_payout")
        
        if features.crossed_20x:
            active.append("pattern3_20x_momentum")
        elif features.crossed_12x:
            active.append("pattern3_12x_momentum")
        elif features.crossed_8x:
            active.append("pattern3_8x_momentum")
        
        if not active:
            active.append("baseline")
        
        return active
    
    def update_weights(self, prediction_result: Dict, actual_outcome: float):
        """Update weights based on prediction accuracy"""
        try:
            prediction = prediction_result.get('prediction', 0)
            self.state.update_accuracy(prediction, actual_outcome)
            
            # Track performance
            error = abs(prediction - actual_outcome)
            self.performance_tracker.append({
                'prediction': prediction,
                'actual': actual_outcome,
                'error': error,
                'timestamp': datetime.now()
            })
            
            logger.info(f"📈 Accuracy updated: {self.state.get_accuracy():.3f}, Error: {error:.1f}")
            
        except Exception as e:
            logger.error(f"Error updating weights: {e}")
    
    def get_performance_metrics(self) -&gt; Dict:
        """Get current performance metrics"""
        return {
            'overall_accuracy': self.state.get_accuracy(),
            'recent_accuracy': sum(self.state.accuracy_window) / len(self.state.accuracy_window) 
                              if self.state.accuracy_window else 0.0,
            'total_predictions': self.state.total_predictions,
            'pattern_weights': dict(self.state.pattern_weights),
            'predictions_in_window': len(self.state.prediction_history)
        }

class MLEnhancedPatternEngine:
    """Main engine combining base patterns with simple ML enhancement"""
    
    def __init__(self, base_pattern_engine):
        self.base_engine = base_pattern_engine
        self.feature_extractor = ValidatedFeatureExtractor()
        self.learning_engine = SimpleLearningEngine()
        self.ml_enabled = True
        self._last_prediction = None
    
    def update_current_game(self, tick: int, price: float):
        """Update current game state"""
        self.base_engine.update_current_game(tick, price)
    
    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -&gt; Dict:
        """Generate enhanced prediction"""
        try:
            # Get base prediction
            base_prediction = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            
            if not self.ml_enabled:
                self._last_prediction = base_prediction
                return base_prediction
            
            # Prepare game state
            current_game_state = {
                'currentTick': current_tick,
                'currentPrice': current_price,
                'peak_price': peak_price
            }
            
            # Extract validated features
            features = self.feature_extractor.extract_features(
                current_game_state,
                self.base_engine.pattern_states,
                self.base_engine.game_history
            )
            
            # Prepare base predictions for combination
            base_predictions = {
                'baseline': base_prediction.get('predicted_tick', MEDIAN_DURATION),
                'pattern1': MEDIAN_DURATION * 1.244 if features.pattern1_triggered else MEDIAN_DURATION,
                'pattern2': 8 if features.ultra_short_cluster_count &gt;= 2 else current_tick + 30,
                'pattern3': int(current_tick * 1.3) if features.crossed_8x else current_tick + 20
            }
            
            # Get ML-enhanced prediction
            ml_result = self.learning_engine.predict_with_features(features, base_predictions)
            
            # Combine base and ML predictions
            ml_weight = min(0.6, self.learning_engine.state.get_accuracy())
            base_weight = 1.0 - ml_weight
            
            final_prediction = (
                ml_result['prediction'] * ml_weight + 
                base_prediction['predicted_tick'] * base_weight
            )
            
            # Build enhanced result
            enhanced_result = {
                'predicted_tick': int(final_prediction),
                'confidence': ml_result['confidence'],
                'tolerance': base_prediction.get('tolerance', 50),
                'based_on_patterns': ml_result['active_patterns'],
                'ml_enhancement': {
                    'ml_prediction': ml_result['prediction'],
                    'base_prediction': base_prediction['predicted_tick'],
                    'ml_weight': ml_weight,
                    'adjustments': ml_result.get('adjustments', 0)
                },
                'performance': self.learning_engine.get_performance_metrics()
            }
            
            self._last_prediction = enhanced_result
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error in ML-enhanced prediction: {e}")
            # Fallback to base prediction
            fallback = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            fallback['ml_error'] = str(e)
            self._last_prediction = fallback
            return fallback
    
    def complete_game_analysis(self, completed_game):
        """Analyze completed game and update learning"""
        try:
            # Update base engine
            self.base_engine.add_completed_game(completed_game)
            
            # Update ML learning if we made a prediction
            if self._last_prediction:
                actual_tick = completed_game.final_tick
                self.learning_engine.update_weights(self._last_prediction, actual_tick)
                
        except Exception as e:
            logger.error(f"Error in game analysis: {e}")
    
    def get_ml_status(self) -&gt; Dict:
        """Get current ML status"""
        return {
            'ml_enabled': self.ml_enabled,
            'learning_metrics': self.learning_engine.get_performance_metrics(),
            'last_prediction': self._last_prediction
        }