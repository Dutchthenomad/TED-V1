"""
Game-Aware ML Engine - Focused on Validated Game Patterns Only
No trading indicators, only proven patterns from knowledge base
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

# VALIDATED GAME CONSTANTS
TICK_DURATION_MS = 250
MEDIAN_DURATION = 205
ULTRA_SHORT_THRESHOLD = 10
MAX_PAYOUT_THRESHOLD = 0.019

@dataclass
class GameAwareFeatures:
    """Features specific to validated game patterns"""
    # Pattern 1: Post-Max-Payout
    is_post_max_payout: bool = False
    games_since_max_payout: int = 999
    
    # Pattern 2: Ultra-Short Dynamics
    ultra_short_probability: float = 0.064
    recent_ultra_short_count: int = 0
    last_end_price: float = 0.0
    is_high_payout_recovery: bool = False
    
    # Pattern 3: Momentum Levels
    current_momentum_threshold: Optional[int] = None  # 8, 12, or 20
    continuation_probability: float = 0.0
    games_since_moonshot: int = 999
    drought_multiplier: float = 1.0
    
    # Game State
    current_tick: int = 0
    current_multiplier: float = 1.0
    peak_multiplier: float = 1.0
    
    # Derived features
    duration_category: str = "normal"  # ultra_short, short, normal, extended, moonshot
    expected_duration_multiplier: float = 1.0

class GamePatternAnalyzer:
    """Analyze game patterns based on validated findings"""
    
    def __init__(self):
        self.pattern_confidence = {
            'pattern1': 0.85,  # 72.7% improvement validated
            'pattern2': 0.78,  # 25.1% improvement validated  
            'pattern3': 0.91   # Up to 50% improvement validated
        }
        
        # Validated thresholds
        self.momentum_thresholds = {
            8: 0.244,   # 24.4% to reach 50x
            12: 0.230,  # 23.0% to reach 100x
            20: 0.500   # 50.0% to continue
        }
    
    def analyze_game_state(self, game_state: Dict, pattern_states: Dict, 
                          game_history: List) -> GameAwareFeatures:
        """Extract game-aware features from current state"""
        features = GameAwareFeatures()
        
        # Basic game state
        features.current_tick = game_state.get('currentTick', 0)
        features.current_multiplier = game_state.get('currentPrice', 1.0)
        features.peak_multiplier = game_state.get('peak_price', 1.0)
        
        # Pattern 1 analysis
        pattern1 = pattern_states.get('pattern1', {})
        features.games_since_max_payout = pattern1.get('games_since_max_payout', 999)
        features.is_post_max_payout = features.games_since_max_payout <= 1
        if features.is_post_max_payout:
            features.expected_duration_multiplier = 1.244  # 24.4% longer
        
        # Pattern 2 analysis
        pattern2 = pattern_states.get('pattern2', {})
        features.last_end_price = pattern2.get('last_end_price', 0.0)
        features.recent_ultra_short_count = len(pattern2.get('recent_ultra_shorts', []))
        
        # Calculate ultra-short probability
        if features.last_end_price &gt;= 0.015:
            features.ultra_short_probability = 0.081  # 8.1% after high payout
            features.is_high_payout_recovery = True
        elif features.recent_ultra_short_count &gt;= 2:
            features.ultra_short_probability = 0.096  # Clustering effect
        else:
            features.ultra_short_probability = 0.064  # Baseline
        
        # Pattern 3 analysis
        pattern3 = pattern_states.get('pattern3', {})
        features.games_since_moonshot = pattern3.get('games_since_moonshot', 999)
        
        # Determine momentum threshold
        if features.peak_multiplier &gt;= 20:
            features.current_momentum_threshold = 20
            features.continuation_probability = 0.500
        elif features.peak_multiplier &gt;= 12:
            features.current_momentum_threshold = 12
            features.continuation_probability = 0.230
        elif features.peak_multiplier &gt;= 8:
            features.current_momentum_threshold = 8
            features.continuation_probability = 0.244
        
        # Calculate drought multiplier
        if features.games_since_moonshot &lt; 42:
            features.drought_multiplier = 1.0
        elif features.games_since_moonshot &lt; 63:
            features.drought_multiplier = 1.2
        elif features.games_since_moonshot &lt; 84:
            features.drought_multiplier = 1.5
        else:
            features.drought_multiplier = 2.0
        
        # Classify duration category
        if features.current_tick &lt;= 10:
            features.duration_category = "ultra_short"
        elif features.current_tick &lt;= 50:
            features.duration_category = "short"
        elif features.current_tick &lt;= 300:
            features.duration_category = "normal"
        elif features.current_tick &lt;= 500:
            features.duration_category = "extended"
        else:
            features.duration_category = "moonshot"
        
        return features

class GameAwarePredictionEngine:
    """Prediction engine using only validated game patterns"""
    
    def __init__(self):
        self.analyzer = GamePatternAnalyzer()
        self.prediction_history = deque(maxlen=100)
        self.accuracy_tracker = deque(maxlen=50)
    
    def generate_prediction(self, features: GameAwareFeatures) -&gt; Dict:
        """Generate prediction based on game-aware features"""
        predictions = []
        weights = []
        patterns_used = []
        
        # Pattern 1: Post-Max-Payout Recovery
        if features.is_post_max_payout:
            # Expect 24.4% longer duration
            prediction = MEDIAN_DURATION * 1.244
            predictions.append(prediction)
            weights.append(self.analyzer.pattern_confidence['pattern1'])
            patterns_used.append("post_max_payout_recovery")
        
        # Pattern 2: Ultra-Short Prediction
        if features.ultra_short_probability &gt; 0.07:  # Above baseline
            if features.current_tick &lt;= 5:  # Early in game
                # Predict ultra-short
                predictions.append(8)
                weights.append(features.ultra_short_probability * 10)  # Scale probability
                patterns_used.append("ultra_short_prediction")
        
        # Pattern 3: Momentum Continuation
        if features.current_momentum_threshold is not None:
            prob = features.continuation_probability * features.drought_multiplier
            if prob &gt; 0.3:  # Significant probability
                if features.current_momentum_threshold == 20:
                    prediction = features.current_tick * 1.5
                elif features.current_momentum_threshold == 12:
                    prediction = features.current_tick * 1.3
                else:
                    prediction = features.current_tick * 1.2
                
                predictions.append(prediction)
                weights.append(prob)
                patterns_used.append(f"momentum_{features.current_momentum_threshold}x")
        
        # Combine predictions
        if predictions:
            total_weight = sum(weights)
            weighted_prediction = sum(p * w for p, w in zip(predictions, weights)) / total_weight
            confidence = min(0.95, sum(weights) / len(weights))
        else:
            # Default prediction
            weighted_prediction = MEDIAN_DURATION
            confidence = 0.5
            patterns_used = ["baseline"]
        
        return {
            'predicted_tick': int(weighted_prediction),
            'confidence': confidence,
            'patterns_used': patterns_used,
            'features': {
                'ultra_short_prob': features.ultra_short_probability,
                'momentum_threshold': features.current_momentum_threshold,
                'drought_multiplier': features.drought_multiplier,
                'is_post_max_payout': features.is_post_max_payout
            }
        }
    
    def calculate_side_bet_value(self, features: GameAwareFeatures) -&gt; Dict:
        """Calculate expected value of side bet"""
        # Side bet wins if game ends within 40 ticks
        # Pays 5:1 (400% profit)
        
        # Focus on ultra-short probability (≤10 ticks)
        win_probability = features.ultra_short_probability
        
        # Boost probability if clustering or post-high-payout
        if features.recent_ultra_short_count &gt;= 2:
            win_probability *= 1.3  # Clustering boost
        if features.is_high_payout_recovery:
            win_probability *= 1.1  # Recovery boost
        
        # Cap at reasonable maximum
        win_probability = min(0.15, win_probability)
        
        # Calculate expected value
        # EV = P(win) * 4.0 - P(lose) * 1.0
        expected_value = (win_probability * 4.0) - ((1 - win_probability) * 1.0)
        
        return {
            'should_bet': expected_value &gt; 0,
            'win_probability': win_probability,
            'expected_value': expected_value,
            'confidence': win_probability,
            'recommendation': self._get_recommendation(expected_value, win_probability)
        }
    
    def _get_recommendation(self, ev: float, prob: float) -&gt; str:
        """Generate bet recommendation"""
        if ev &gt; 0.2:
            return f"STRONG BET: {prob:.1%} win probability, EV: {ev:.3f}"
        elif ev &gt; 0:
            return f"POSITIVE EV: {prob:.1%} win probability, EV: {ev:.3f}"
        else:
            return f"WAIT: {prob:.1%} win probability, EV: {ev:.3f}"
    
    def update_accuracy(self, predicted: float, actual: float):
        """Track prediction accuracy"""
        error = abs(predicted - actual)
        is_correct = error &lt;= 50  # Within tolerance
        self.accuracy_tracker.append(is_correct)
        
        self.prediction_history.append({
            'predicted': predicted,
            'actual': actual,
            'error': error,
            'correct': is_correct,
            'timestamp': datetime.now()
        })
    
    def get_performance_metrics(self) -&gt; Dict:
        """Get current performance metrics"""
        if not self.accuracy_tracker:
            return {'accuracy': 0.5, 'predictions': 0}
        
        return {
            'accuracy': sum(self.accuracy_tracker) / len(self.accuracy_tracker),
            'predictions': len(self.prediction_history),
            'recent_errors': [p['error'] for p in list(self.prediction_history)[-10:]]
        }

class GameAwareMLPatternEngine:
    """Main engine for game-aware pattern prediction"""
    
    def __init__(self, base_pattern_engine):
        self.base_engine = base_pattern_engine
        self.analyzer = GamePatternAnalyzer()
        self.predictor = GameAwarePredictionEngine()
        self._last_prediction = None
    
    def update_current_game(self, tick: int, price: float):
        """Update current game state"""
        self.base_engine.update_current_game(tick, price)
    
    def predict_rug_timing(self, current_tick: int, current_price: float, peak_price: float) -&gt; Dict:
        """Generate game-aware prediction"""
        try:
            # Get base prediction
            base_prediction = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            
            # Prepare game state
            game_state = {
                'currentTick': current_tick,
                'currentPrice': current_price,
                'peak_price': peak_price
            }
            
            # Analyze game features
            features = self.analyzer.analyze_game_state(
                game_state,
                self.base_engine.pattern_states,
                self.base_engine.game_history
            )
            
            # Generate prediction
            game_prediction = self.predictor.generate_prediction(features)
            
            # Calculate side bet value
            side_bet = self.predictor.calculate_side_bet_value(features)
            
            # Combine predictions (60% game-aware, 40% base)
            final_prediction = int(
                game_prediction['predicted_tick'] * 0.6 +
                base_prediction['predicted_tick'] * 0.4
            )
            
            result = {
                'predicted_tick': final_prediction,
                'confidence': game_prediction['confidence'],
                'tolerance': 50,
                'based_on_patterns': game_prediction['patterns_used'],
                'side_bet_recommendation': side_bet,
                'game_features': game_prediction['features'],
                'performance': self.predictor.get_performance_metrics()
            }
            
            self._last_prediction = result
            return result
            
        except Exception as e:
            logger.error(f"Error in game-aware prediction: {e}")
            # Fallback
            fallback = self.base_engine.predict_rug_timing(current_tick, current_price, peak_price)
            self._last_prediction = fallback
            return fallback
    
    def complete_game_analysis(self, completed_game):
        """Analyze completed game"""
        try:
            # Update base engine
            self.base_engine.add_completed_game(completed_game)
            
            # Update accuracy if we made a prediction
            if self._last_prediction:
                self.predictor.update_accuracy(
                    self._last_prediction['predicted_tick'],
                    completed_game.final_tick
                )
                
        except Exception as e:
            logger.error(f"Error in game analysis: {e}")
    
    def get_ml_status(self) -&gt; Dict:
        """Get current status"""
        return {
            'performance': self.predictor.get_performance_metrics(),
            'last_prediction': self._last_prediction
        }