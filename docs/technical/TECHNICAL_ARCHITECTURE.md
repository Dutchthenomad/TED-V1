# TED System - Technical Architecture & ML Methods

*Comprehensive technical documentation for developers and data scientists*

## Table of Contents
1. [Statistical Foundation](#statistical-foundation)
2. [Machine Learning Architecture](#machine-learning-architecture)
3. [Algorithm Specifications](#algorithm-specifications)
4. [Performance Metrics](#performance-metrics)
5. [Implementation Details](#implementation-details)
6. [Optimization Techniques](#optimization-techniques)

---

## Statistical Foundation

### Core Probability Model

#### Discrete-Time Hazard Function
The system models game termination using a discrete-time survival analysis framework:

```python
h(t) = P(T = t | T ≥ t)  # Hazard at tick t
S(t) = ∏(1 - h(i)) for i=1 to t  # Survival function
F(t) = 1 - S(t)  # Cumulative distribution function
```

**Parameters:**
- Base hazard rate: `p = 0.005` (per-tick rug probability)
- Mean game duration: `E[T] = 1/p ≈ 200 ticks` (theoretical)
- Observed mean: `~280 ticks` (empirical, suggesting `p ≈ 0.00357`)

#### Conditional Probability Windows
For side bet calculations (40-tick windows):

```python
P(rug in next 40 | alive at t) = 1 - ∏(1 - h(t+i)) for i=1 to 40
```

**Break-even analysis:**
- Payout ratio: 5:1 (gross), 4:1 (net)
- Break-even probability: `p* = 1/5 = 0.20`
- Required hazard for positive EV: `h* ≈ 0.005563`

### Bayesian Updates

#### Prior Distribution
```python
# Beta prior for hazard rate
α₀ = 1.0  # Prior successes
β₀ = 199.0  # Prior failures
Prior ~ Beta(α₀, β₀)
```

#### Posterior Updates
```python
# After observing n games with durations d₁, d₂, ..., dₙ
α_post = α₀ + n  # Add number of rug events
β_post = β₀ + Σ(dᵢ)  # Add total ticks survived
Posterior ~ Beta(α_post, β_post)
```

---

## Machine Learning Architecture

### 1. Enhanced Pattern Recognition Engine

#### Feature Extraction Pipeline
```python
class FeatureExtractor:
    # Price-based features
    - log_returns: log(pₜ/pₜ₋₁)
    - volatility_10: std(returns[-10:])
    - volatility_40: std(returns[-40:])
    - momentum: EMA(price, α=0.1) - EMA(price, α=0.05)
    
    # Statistical features
    - skewness: third moment of returns
    - kurtosis: fourth moment of returns
    - hurst_exponent: long-range dependence
    
    # Technical indicators
    - RSI(14): Relative Strength Index
    - MACD: Moving Average Convergence Divergence
    - Bollinger_position: (price - μ) / (2σ)
```

#### Pattern Detection Algorithms

**Pattern 1: Post-Max Payout Recovery**
```python
def detect_max_payout_pattern(peak_price, current_price, tick):
    if peak_price >= MAX_PAYOUT_THRESHOLD:  # 50x
        recovery_rate = (peak_price - current_price) / peak_price
        if recovery_rate > 0.1 and tick > peak_tick + 10:
            confidence = sigmoid(recovery_rate * 10)
            return PatternSignal(confidence, status="TRIGGERED")
```

**Pattern 2: Ultra-Short Game Detection**
```python
def detect_ultra_short(tick, price_trajectory):
    if tick <= 25:
        features = extract_early_features(price_trajectory)
        prob = logistic_model.predict_proba(features)[0, 1]
        if prob > 0.7:
            return PatternSignal(prob, status="TRIGGERED")
```

**Pattern 3: Momentum Thresholds**
```python
def detect_momentum_pattern(returns_window):
    momentum_score = np.abs(np.mean(returns_window))
    volatility = np.std(returns_window)
    
    if momentum_score > MOMENTUM_THRESHOLD:
        danger_score = momentum_score * volatility
        confidence = 1 - exp(-danger_score)
        return PatternSignal(confidence, status=get_status(confidence))
```

### 2. Hazard Head Architecture

#### Logit Stream Generation
```python
def build_hazard_logits(horizon=80):
    """Generate per-tick hazard logits for survival analysis"""
    logits = []
    
    for t in range(horizon):
        # Base hazard
        z_base = logit(BASE_HAZARD)  # logit(0.005) ≈ -5.293
        
        # Feature modulation
        z_feat = sum([
            β₁ * volatility_factor(t),
            β₂ * momentum_factor(t),
            β₃ * pattern_factor(t),
            β₄ * tick_decay_factor(t)
        ])
        
        # EPR scaling (Early Peak Regime)
        z_epr = log(epr_scale) if epr_active else 0
        
        # Stream scaling (tick features)
        z_stream = log(stream_scale) if stream_enabled else 0
        
        logits.append(z_base + z_feat + z_epr + z_stream)
    
    return logits
```

#### Survival Folding
```python
def fold_survival_stream(logits):
    """Convert hazard logits to survival statistics"""
    S = 1.0  # Initial survival
    pmf = []
    cdf = []
    
    for t, logit in enumerate(logits, 1):
        h = sigmoid(logit)  # Hazard at tick t
        p = h * S  # Probability mass
        S *= (1 - h)  # Update survival
        
        pmf.append(p)
        cdf.append(1 - S)
    
    # Calculate quantiles
    quantiles = {}
    for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
        quantiles[f'q{int(q*100)}'] = find_quantile(cdf, q)
    
    # Expected value
    E_T = sum(t * p for t, p in enumerate(pmf, 1))
    
    return {
        'expected': E_T,
        'quantiles': quantiles,
        'pmf': pmf,
        'cdf': cdf,
        'survival_tail': S
    }
```

### 3. Conformal Prediction Wrapper

#### Prediction Intervals
```python
class ConformalPID:
    """Conformal prediction with PID control for coverage"""
    
    def __init__(self, target_coverage=0.85):
        self.target = target_coverage
        self.alpha = 1 - target_coverage
        self.scores = deque(maxlen=100)
        
        # PID parameters
        self.Kp = 0.1  # Proportional gain
        self.Ki = 0.01  # Integral gain
        self.Kd = 0.05  # Derivative gain
        
    def calibrate(self, prediction, actual):
        """Update conformal scores"""
        score = abs(prediction - actual)
        self.scores.append(score)
        
    def get_interval(self, prediction):
        """Get prediction interval with target coverage"""
        if len(self.scores) < 20:
            # Bootstrap phase
            width = 50  # Default width
        else:
            # Quantile of scores
            q = np.quantile(self.scores, self.target)
            
            # PID adjustment
            coverage = self.compute_coverage()
            error = self.target - coverage
            
            adjustment = (
                self.Kp * error +
                self.Ki * sum(self.errors) +
                self.Kd * (error - self.last_error)
            )
            
            width = q * (1 + adjustment)
        
        return [prediction - width, prediction + width]
```

### 4. Drift Detection

#### Page-Hinkley Test
```python
class PageHinkley:
    """Detect concept drift in prediction errors"""
    
    def __init__(self, delta=0.005, lambda_=50):
        self.delta = delta  # Minimum change to detect
        self.lambda_ = lambda_  # Threshold
        self.sum = 0
        self.min_sum = 0
        
    def update(self, error):
        """Update drift detector with new error"""
        self.sum += error - self.delta
        self.min_sum = min(self.min_sum, self.sum)
        
        # Page-Hinkley statistic
        PH = self.sum - self.min_sum
        
        if PH > self.lambda_:
            return "DRIFT_DETECTED"
        return "NO_DRIFT"
```

### 5. Ultra-Short Gate

#### Gating Mechanism
```python
class UltraShortGate:
    """Specialized handling for ultra-short games"""
    
    def __init__(self, threshold=100):
        self.threshold = threshold
        self.short_game_model = self.train_short_game_model()
        
    def apply(self, prediction, tick, features):
        """Gate predictions for potential ultra-short games"""
        if tick <= 25:
            # Early game - check for ultra-short signals
            p_short = self.short_game_model.predict_proba(features)[0, 1]
            
            if p_short > 0.6:
                # Apply conservative adjustment
                gated = min(prediction, self.threshold)
                confidence_penalty = 0.8
                return gated, confidence_penalty
        
        return prediction, 1.0
```

---

## Algorithm Specifications

### 1. Early Peak Regime (EPR) Detection

```python
class EPRDetector:
    """Detect and handle early peak regimes"""
    
    config = {
        'early_tick_max': 120,      # Window for "early"
        'ratio_threshold': 2.8,      # Peak/baseline ratio
        'sustain_min': 10,          # Ticks to confirm
        'hazard_scale': 0.70,       # Hazard reduction
        'decay_tau': 120,           # Decay time constant
        'quantile_override': 0.70   # Use q70 when active
    }
    
    def update(self, tick, current_mult, peak_mult):
        # Update baseline EMA
        self.baseline_ema = 0.9 * self.baseline_ema + 0.1 * current_mult
        
        # Check activation criteria
        ratio = peak_mult / self.baseline_ema
        
        if tick <= self.config['early_tick_max'] and ratio >= self.config['ratio_threshold']:
            self.sustain_ticks += 1
            
            if self.sustain_ticks >= self.config['sustain_min']:
                self.active = True
                self.activation_tick = tick
        
        # Calculate hazard scale with decay
        if self.active:
            dt = tick - self.activation_tick
            scale = self.config['hazard_scale'] + \
                   (1 - self.config['hazard_scale']) * exp(-dt / self.config['decay_tau'])
            return scale
        
        return 1.0
```

### 2. Dynamic Quantile Adjustment

```python
class DynamicQuantileSelector:
    """Adjust prediction quantiles based on directional bias"""
    
    def __init__(self, window=50, dead_zone=0.1, alpha=0.3):
        self.window = window
        self.dead_zone = dead_zone
        self.alpha = alpha
        self.history = deque(maxlen=window)
        
    def update(self, predicted, actual):
        """Record prediction error"""
        signed_error = predicted - actual
        E40 = signed_error / 40.0  # Window-normalized
        self.history.append(E40)
        
    def get_quantile(self, base_quantile=0.5):
        """Calculate adjusted quantile"""
        if len(self.history) < 20:
            return base_quantile
        
        # Median error in windows
        median_E40 = np.median(self.history)
        
        # Apply dead zone
        if abs(median_E40) <= self.dead_zone:
            return base_quantile
        
        # Adjustment formula: qt = 0.5 + clip(medE40, -0.3, 0.3) * α
        adjustment = np.clip(median_E40, -0.3, 0.3) * self.alpha
        adjusted = base_quantile + adjustment
        
        # Bound between reasonable limits
        return np.clip(adjusted, 0.3, 0.8)
```

### 3. Tick Feature Engine

```python
class TickFeatureEngine:
    """O(1) streaming feature calculation"""
    
    def update(self, tick, price, peak, epr_active):
        # Log return
        r = log(price / self.last_price) if self.last_price else 0
        self.return_buffer.append(r)
        
        # Exponential moving averages
        self.ema10 = 0.8 * self.ema10 + 0.2 * price
        self.ema40 = 0.95 * self.ema40 + 0.05 * price
        
        # Return statistics (rolling 40 ticks)
        r_mean = np.mean(self.return_buffer)
        r_std = np.std(self.return_buffer)
        
        # Streak tracking
        if r > 0:
            self.up_streak += 1
            self.down_streak = 0
        elif r < 0:
            self.down_streak += 1
            self.up_streak = 0
        
        # Drawdown metrics
        drawdown = (peak - price) / peak
        dist_to_peak = peak / price
        since_peak = tick - self.peak_tick if peak == price else tick - self.peak_tick
        
        # Calculate hazard scale
        scale = 1.0
        scale *= 0.85 if epr_active else 1.0
        scale *= 0.90 if since_peak > 120 and r_std < 0.02 else 1.0
        scale *= 0.92 if self.up_streak >= 8 else 1.0
        scale *= 1.08 if self.down_streak >= 8 else 1.0
        
        return TickSnapshot(
            tick=tick, price=price, peak=peak,
            ema10=self.ema10, ema40=self.ema40,
            r_mean40=r_mean, r_std40=r_std,
            up_streak=self.up_streak, down_streak=self.down_streak,
            drawdown=drawdown, dist_to_peak=dist_to_peak,
            since_peak=since_peak, hazard_scale=np.clip(scale, 0.6, 1.5),
            epr_active=epr_active
        )
```

---

## Performance Metrics

### 1. Directional Error Metrics

```python
class DirectionalMetrics:
    """Track prediction bias and calibration"""
    
    @staticmethod
    def calculate(predictions, actuals):
        # Signed error
        signed_errors = predictions - actuals
        
        # Window-normalized error (40-tick windows)
        E40 = signed_errors / 40.0
        
        # Spread-normalized error
        spreads = [p['q90'] - p['q10'] for p in predictions]
        Ez = signed_errors / np.maximum(40, spreads)
        
        return {
            'median_E40': np.median(E40),
            'mean_E40': np.mean(E40),
            'early_rate': np.mean(signed_errors < 0),
            'late_rate': np.mean(signed_errors > 0),
            'within_1_window': np.mean(np.abs(E40) <= 1),
            'within_2_windows': np.mean(np.abs(E40) <= 2),
            'within_3_windows': np.mean(np.abs(E40) <= 3),
            'MAE': np.mean(np.abs(signed_errors)),
            'RMSE': np.sqrt(np.mean(signed_errors ** 2)),
            'coverage_rate': np.mean(in_band),  # Actual in prediction interval
            'early_skew': np.mean(signed_errors < 0) - np.mean(signed_errors > 0)
        }
```

### 2. Calibration Metrics

```python
def calculate_calibration(predictions, actuals):
    """Assess probability calibration"""
    
    # Bin predictions by confidence
    bins = np.linspace(0, 1, 11)
    calibration_data = []
    
    for i in range(len(bins) - 1):
        mask = (predictions['confidence'] >= bins[i]) & \
               (predictions['confidence'] < bins[i + 1])
        
        if mask.sum() > 0:
            predicted_prob = predictions['confidence'][mask].mean()
            actual_rate = actuals['within_tolerance'][mask].mean()
            
            calibration_data.append({
                'bin': f'{bins[i]:.1f}-{bins[i+1]:.1f}',
                'predicted': predicted_prob,
                'actual': actual_rate,
                'count': mask.sum()
            })
    
    # Expected Calibration Error (ECE)
    ECE = sum(abs(d['predicted'] - d['actual']) * d['count'] 
              for d in calibration_data) / len(predictions)
    
    return {
        'calibration_data': calibration_data,
        'ECE': ECE,
        'well_calibrated': ECE < 0.1
    }
```

### 3. Side Bet Performance

```python
def analyze_sidebet_performance(recommendations, outcomes):
    """Analyze side bet recommendation quality"""
    
    placed_bets = recommendations[recommendations['action'] == 'PLACE_SIDE_BET']
    
    metrics = {
        'total_recommendations': len(placed_bets),
        'win_rate': outcomes['won'].mean(),
        'expected_win_rate': placed_bets['p_win_40'].mean(),
        'actual_ev': outcomes['pnl'].sum() / placed_bets['amount'].sum(),
        'expected_ev': placed_bets['expected_value'].mean(),
        'sharpe_ratio': outcomes['pnl'].mean() / outcomes['pnl'].std(),
        'max_drawdown': calculate_max_drawdown(outcomes['cumulative_pnl']),
        'kelly_fraction': calculate_kelly(
            placed_bets['p_win_40'].mean(), 
            payout=5
        )
    }
    
    return metrics
```

---

## Implementation Details

### System Architecture

```yaml
Backend Stack:
  Language: Python 3.10+
  Framework: FastAPI
  Async: asyncio
  WebSocket: python-socketio
  Database: MongoDB (Motor async driver)
  Cache: In-memory deque structures
  
Frontend Stack:
  Language: TypeScript/JavaScript
  Framework: React 18
  State: React hooks
  WebSocket: socket.io-client
  Styling: Tailwind CSS
  Build: Create React App with CRACO

Infrastructure:
  Containerization: Docker
  Orchestration: Docker Compose
  Monitoring: Prometheus + custom metrics
  Deployment: Kubernetes-ready
```

### Data Pipeline

```python
# Real-time processing flow
1. WebSocket ingestion (rugs.fun) → 
2. Event parsing & validation →
3. Feature extraction (O(1)) →
4. Pattern detection (parallel) →
5. Hazard calculation →
6. Prediction generation →
7. Confidence calibration →
8. WebSocket broadcast →
9. Frontend rendering

# Latency targets
- Ingestion to prediction: <30ms
- Prediction to UI: <20ms
- Total end-to-end: <50ms
```

### Memory Management

```python
class CircularBufferManager:
    """Efficient memory management for streaming data"""
    
    buffers = {
        'price_history': deque(maxlen=500),
        'prediction_history': deque(maxlen=200),
        'tick_features': deque(maxlen=1200),
        'pattern_signals': deque(maxlen=100),
        'sidebet_history': deque(maxlen=200)
    }
    
    # Memory footprint per game: ~50KB
    # Maximum concurrent games: 10
    # Total memory usage: <1MB
```

---

## Optimization Techniques

### 1. Computational Optimization

```python
# Vectorized operations
prices_array = np.array(price_history)
returns = np.diff(np.log(prices_array))  # Vectorized log returns

# Numba JIT compilation for hot paths
@numba.jit(nopython=True)
def calculate_hazard_logits(features, weights):
    return features @ weights  # Matrix multiplication

# Cython for critical sections
# See: backend/core/fast_math.pyx
```

### 2. Latency Optimization

```python
# Async/await patterns
async def process_tick(tick_data):
    # Parallel processing
    tasks = [
        extract_features(tick_data),
        detect_patterns(tick_data),
        calculate_hazard(tick_data)
    ]
    
    features, patterns, hazard = await asyncio.gather(*tasks)
    return combine_predictions(features, patterns, hazard)

# Connection pooling
mongo_client = AsyncIOMotorClient(
    max_pool_size=10,
    min_pool_size=2
)
```

### 3. Accuracy Optimization

```python
# Ensemble methods
predictions = [
    hazard_model.predict(features) * 0.4,
    pattern_model.predict(features) * 0.3,
    ml_model.predict(features) * 0.3
]
final_prediction = np.average(predictions, weights=[0.4, 0.3, 0.3])

# Online learning
def update_model(prediction, actual):
    error = prediction - actual
    # Gradient descent update
    model.weights -= learning_rate * error * features
```

---

## Configuration Parameters

```python
# Environment variables for tuning
ENV_CONFIG = {
    # Hazard parameters
    'BASE_HAZARD': 0.005,
    'HAZARD_DECAY': 0.001,
    
    # EPR parameters
    'EPR_RATIO_THRESHOLD': 2.8,
    'EPR_HAZARD_SCALE': 0.70,
    'EPR_DECAY_TAU': 120,
    
    # Quantile adjustment
    'QUANTILE_ADJUSTMENT_ENABLED': True,
    'QUANTILE_DEAD_ZONE': 0.1,
    'QUANTILE_ALPHA': 0.3,
    
    # Side bet thresholds
    'SIDEBET_PWIN_THRESHOLD': 0.20,
    'SIDEBET_COOLDOWN_TICKS': 4,
    
    # Tick features
    'STREAM_FEATURES_ENABLED': False,
    'STREAM_INFLUENCE_ENABLED': False,
    'STREAM_RING_SIZE': 1200,
    'STREAM_MAX_CPU_MS': 3,
    
    # Model parameters
    'CONFIDENCE_FLOOR': 0.3,
    'CONFIDENCE_CEILING': 0.95,
    'TOLERANCE_MIN': 20,
    'TOLERANCE_MAX': 100
}
```

---

## References & Theory

### Academic Foundations
1. **Survival Analysis**: Klein, J.P. & Moeschberger, M.L. (2003). *Survival Analysis: Techniques for Censored and Truncated Data*
2. **Conformal Prediction**: Vovk, V., Gammerman, A., & Shafer, G. (2005). *Algorithmic Learning in a Random World*
3. **Concept Drift**: Gama, J., et al. (2014). "A survey on concept drift adaptation"
4. **Hazard Models**: Cox, D.R. (1972). "Regression models and life tables"

### Implementation References
1. **FastAPI WebSockets**: https://fastapi.tiangolo.com/advanced/websockets/
2. **Survival Analysis in Python**: lifelines library documentation
3. **Online Learning**: River library for incremental learning
4. **Conformal Prediction**: MAPIE library implementation

---

*This document represents the complete technical specification of the TED system as of August 2024. For implementation updates, see CHANGELOG.md.*