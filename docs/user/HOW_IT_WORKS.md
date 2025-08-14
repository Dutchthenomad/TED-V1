# How TED Works

*Understanding the intelligence behind the predictions*

## The Big Picture

TED operates like a weather forecasting system for Rugs.fun games. Just as meteorologists use atmospheric data to predict storms, TED uses game data to predict when games will end. The more data it has, and the clearer the patterns, the better its predictions become.

## Core Components

### 1. Data Collection Layer
Every 250 milliseconds (one "tick"), TED captures:
- Current game price/multiplier
- Time elapsed (tick count)
- Peak price reached
- Recent price movements
- Player activity patterns

This creates a continuous stream of information, like a heartbeat monitor for the game.

### 2. Pattern Recognition Engine

TED watches for three proven patterns that often precede game endings:

#### **Pattern 1: Post-Max Payout Recovery**
*What it means in plain English:*
- Games that hit extreme multipliers (like 50x+) rarely sustain them
- Think of it like a rubber band - the further it stretches, the more likely it snaps back
- When detected: ~72.7% more accurate than random guessing

#### **Pattern 2: Ultra-Short Game Detection**
*What it means in plain English:*
- Some games show early signs they'll end quickly
- Like recognizing a sprinter vs marathon runner at the starting line
- Useful for avoiding games that might end before you can profit

#### **Pattern 3: Momentum Thresholds**
*What it means in plain English:*
- Rapid price movements in either direction increase instability
- Like driving fast on a winding road - higher chance of crashes
- Helps identify when games become too volatile to sustain

### 3. The Prediction Model

TED uses multiple approaches simultaneously:

#### **Statistical Analysis**
- Examines thousands of historical games
- Identifies common ending patterns
- Calculates probability distributions
- Updates continuously with new data

#### **Hazard Modeling**
Think of this like actuarial science (insurance math):
- Calculates the "risk of ending" at each moment
- Risk compounds over time
- Adjusts for current game conditions
- Produces a survival curve (like life expectancy tables)

#### **Machine Learning Enhancement**
- Learns from prediction successes and failures
- Adapts to changing game dynamics
- Recognizes complex pattern combinations
- Improves accuracy over time

### 4. Confidence Calibration

TED doesn't just make predictions - it tells you how certain it is:

#### **Confidence Factors**
- **High (>75%)**: Strong pattern alignment, consistent signals
- **Medium (50-75%)**: Good indicators, some uncertainty
- **Low (<50%)**: Mixed signals, proceed with caution

#### **Tolerance Windows**
Instead of saying "tick 285 exactly", TED says "285 ±50" because:
- Games have inherent randomness
- Patterns provide ranges, not exact points
- Wider tolerance = more uncertainty
- Narrower tolerance = higher precision

## The Side Bet Algorithm

Side bets are special - you're betting the game ends within exactly 40 ticks. TED calculates this separately:

### Step 1: Window Probability
Calculates the exact probability of ending in the next 40 ticks using:
- Current hazard rate
- Recent game behavior
- Active patterns
- Historical data for similar situations

### Step 2: Expected Value (EV) Calculation
```
If you bet $1:
- Win (5x payout): Get $5 back = +$4 profit
- Lose: Lose $1 = -$1 loss

EV = (Win Probability × $4) - (Lose Probability × $1)
```

### Step 3: Decision Threshold
- If probability > 20% → Positive EV → PLACE_SIDE_BET
- If probability < 20% → Negative EV → WAIT

*Why 20%? Because 20% × 5x payout = 100% (break-even)*

## Adaptation Mechanisms

### Real-Time Learning
TED continuously adjusts based on:
- Recent prediction accuracy
- Detected "drift" in game behavior
- Pattern effectiveness
- Market conditions

### Early Peak Regime (EPR)
When games hit high multipliers early:
- Normal patterns become less reliable
- TED shifts to conservative predictions
- Adjusts hazard calculations
- Increases tolerance windows

### Directional Bias Correction
TED tracks whether it tends to predict too early or too late:
- Measures error in "windows" (40-tick units)
- Adjusts future predictions accordingly
- Aims for zero median error
- Self-corrects over time

## Why Predictions Change

You'll notice predictions updating constantly. This is intentional:

### New Information
Each tick provides new data that can:
- Confirm existing patterns
- Reveal new patterns
- Invalidate previous assumptions
- Refine probability calculations

### Analogy: GPS Navigation
Think of it like your GPS recalculating:
- Initial route based on normal traffic
- Traffic jam detected → new route
- Accident cleared → route updates again
- Always showing best current estimate

## Understanding Accuracy

### What 70% Accuracy Means
- 7 out of 10 predictions within tolerance
- NOT "exactly right 70% of the time"
- Statistical edge, not certainty
- Profitable over many games, not guaranteed each game

### Why Not 100% Accurate?
1. **True Randomness**: Games use cryptographic randomness
2. **Black Swan Events**: Rare, unpredictable occurrences
3. **Limited Information**: Some factors we can't observe
4. **Chaos Theory**: Small changes → big differences

## The Technology Stack

*For the technically curious:*

### Backend (Python)
- **FastAPI**: High-performance web framework
- **WebSockets**: Real-time bidirectional communication
- **NumPy/Pandas**: Statistical computing
- **AsyncIO**: Concurrent processing

### Frontend (React)
- **Real-time Dashboard**: Live data visualization
- **WebSocket Client**: Server communication
- **Responsive Design**: Works on all devices

### Infrastructure
- **Docker**: Containerized deployment
- **MongoDB**: Historical data storage
- **Prometheus**: Performance monitoring

## Ethical Considerations

### What TED Does ✅
- Analyzes public information
- Provides statistical insights
- Helps informed decision-making
- Operates transparently

### What TED Doesn't Do ❌
- Exploit bugs or vulnerabilities
- Guarantee profits
- Manipulate game outcomes
- Access private information

## Performance Optimization

TED is optimized for:
- **Low Latency**: <50ms prediction updates
- **High Throughput**: 1000+ events/second
- **Accuracy**: Continuous improvement algorithms
- **Reliability**: 99.9% uptime target

## Future Improvements

The beta version is just the beginning. Planned enhancements:

### Short Term (1-3 months)
- More pattern types
- Improved accuracy for extreme games
- Better visualization tools
- Mobile optimization

### Medium Term (3-6 months)
- Custom strategy builders
- Historical backtesting tools
- Advanced risk management
- API for automated trading

### Long Term (6+ months)
- AI-powered pattern discovery
- Multi-game correlation analysis
- Predictive portfolio management
- Community-driven improvements

## The Human Element

Remember: TED is a tool, not a replacement for judgment:

### TED Provides
- Statistical analysis
- Pattern recognition
- Probability calculations
- Risk assessments

### You Provide
- Risk tolerance decisions
- Bankroll management
- Strategic thinking
- Emotional control

## In Summary

TED works by:
1. **Collecting** real-time game data
2. **Analyzing** patterns and probabilities
3. **Predicting** likely outcomes with confidence levels
4. **Adapting** to new information continuously
5. **Presenting** actionable insights clearly

It's sophisticated technology made simple to use. You don't need to understand every detail - just trust that behind every prediction is solid math, proven patterns, and continuous improvement.

Think of TED as your analytical partner: it does the heavy mathematical lifting so you can focus on strategy and decision-making.

---

[← Back to Overview](README_BETA.md) | [← Getting Started](GETTING_STARTED.md)

*Questions about how TED works? We'd love to hear them - they help us improve our documentation!*