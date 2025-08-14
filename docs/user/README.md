# TED System - Treasury Exploitation & Detection for Rugs.fun

*Smart predictions for smarter gameplay*

## What is TED?

TED is an advanced prediction system designed specifically for Rugs.fun players. It analyzes game patterns in real-time and provides intelligent predictions about when games might end ("rug"), helping you make more informed decisions about your trades and side bets.

Think of TED as your co-pilot - it watches the game data, recognizes patterns that human eyes might miss, and gives you actionable insights based on statistical analysis of thousands of previous games.

## Key Features

### 🎯 **Rug Timing Predictions**
TED predicts when a game is likely to end, giving you:
- **Predicted tick**: The most likely ending point
- **Confidence level**: How certain the system is (0-100%)
- **Tolerance window**: A range where the rug is most probable

### 📊 **Side Bet Recommendations**
Get real-time advice on side bets with:
- **Action signals**: Clear "PLACE" or "WAIT" recommendations
- **Win probability**: Your chances in the next 40-tick window
- **Expected value**: Whether the bet is mathematically favorable

### 📈 **Pattern Recognition**
TED monitors three key patterns:
1. **Post-Max Payout Recovery**: Games often end shortly after hitting extreme multipliers
2. **Ultra-Short Detection**: Identifies games likely to end very quickly
3. **Momentum Tracking**: Watches for dangerous price movements

### 🔄 **Real-Time Adaptation**
- Updates predictions every tick (250ms)
- Learns from recent games to improve accuracy
- Adjusts for current market conditions

## Performance Metrics

Based on extensive testing:
- **Prediction Accuracy**: ~65-70% within 2 betting windows
- **Side Bet Performance**: Positive expected value in favorable conditions
- **Pattern Detection**: 72.7% improvement over baseline for key patterns

*Note: Past performance doesn't guarantee future results. The system is probabilistic, not deterministic.*

## Important Disclaimers

### ⚠️ **This is a Beta System**
- TED is under active development
- Predictions are statistical estimates, not guarantees
- Always use your own judgment alongside TED's recommendations

### 💰 **Risk Management**
- Never bet more than you can afford to lose
- TED provides information, not financial advice
- The house always has an edge - manage your bankroll carefully

### 🎲 **Understanding Randomness**
Rugs.fun uses provably fair randomness. TED doesn't "crack" or "beat" the system - it identifies statistical patterns that can shift probabilities slightly in your favor over many games.

## The Dashboard Explained

When you open TED, you'll see several information panels:

### **Connection Status** (Top Bar)
- Green = Connected and receiving data
- Red = Disconnected (check your connection)
- Shows update count and uptime

### **Prediction Panel** (Left)
- **Predicted Tick**: When we think the game will end
- **Remaining**: Ticks until predicted end
- **Confidence**: How sure we are (higher = better)
- **Tolerance**: The ± window of uncertainty

### **Pattern Status** (Center)
Shows three patterns being monitored:
- **NORMAL**: Pattern not detected
- **MONITORING**: Pattern developing
- **APPROACHING**: Pattern strengthening
- **TRIGGERED**: Pattern active (high risk)

### **Side Bet Signal** (Right)
- **Action**: PLACE_SIDE_BET or WAIT
- **P(win)**: Probability of winning in next 40 ticks
- **EV**: Expected value (positive = favorable)
- **Threshold**: Minimum probability needed to bet

### **ML Insights** (Bottom)
Technical details about the prediction model:
- Which patterns influenced the prediction
- System modules currently active
- Accuracy tracking

### **Performance Metrics** (New!)
- **Median E40**: How early/late our predictions are (in 40-tick windows)
- **Within 2w**: % of predictions accurate within 2 windows
- **Coverage**: How often the actual result falls in our predicted range
- **Early Skew**: Whether we tend to predict too early or too late

## Quick Start Tips

1. **Start by Observing**: Watch TED for a few games before betting to understand its patterns
2. **Focus on High Confidence**: Pay more attention when confidence is >70%
3. **Use Side Bet Signals**: They're calculated for optimal expected value
4. **Watch the Patterns**: When multiple patterns trigger, risk is elevated
5. **Track Your Results**: Keep notes on when TED helps and when it doesn't

## Feedback & Support

As a beta tester, your feedback is invaluable:

- **Bug Reports**: Note the game ID and what went wrong
- **Accuracy Feedback**: Tell us when predictions are way off
- **Feature Requests**: What would make TED more useful?
- **General Impressions**: How's the user experience?

## Technical Requirements

- Modern web browser (Chrome, Firefox, Edge recommended)
- Stable internet connection
- JavaScript enabled
- Cookies enabled for session persistence

## FAQ

**Q: Can TED guarantee I'll win?**
A: No. TED provides statistical analysis to inform your decisions, but gambling always involves risk.

**Q: How accurate is TED?**
A: Currently achieving 65-70% accuracy within 2 betting windows, with ongoing improvements.

**Q: Does TED work for all game types?**
A: TED is optimized for standard Rugs.fun games. Extreme outliers may reduce accuracy.

**Q: Why do predictions change during the game?**
A: TED continuously updates based on new information, like how weather forecasts improve as storms approach.

**Q: Is TED legal to use?**
A: Yes. TED only analyzes publicly available game data, similar to any statistical tool.

---

*Remember: Gamble responsibly. TED is a tool to enhance your gameplay, not a magic solution. The excitement is in the game, and TED is here to make it more interesting, not to remove the uncertainty that makes it fun.*

**Version**: Beta 2.0.0  
**Last Updated**: August 2024

---

[Get Started →](GETTING_STARTED.md) | [How It Works →](HOW_IT_WORKS.md)