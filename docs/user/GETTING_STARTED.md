# Getting Started with TED

*Your step-by-step guide to using the Treasury Exploitation & Detection system*

## Quick Setup (5 minutes)

### Step 1: Access TED
Open your web browser and navigate to:
```
[Your TED URL will be provided by the beta coordinator]
```

### Step 2: Initial Connection
When TED loads, you should see:
- ✅ Green "CONNECTED" status in the top bar
- 📊 Live game data starting to populate
- 🔄 Update counter incrementing

If you see a red "DISCONNECTED" status:
1. Refresh the page
2. Check your internet connection
3. Try a different browser
4. Contact support if issues persist

### Step 3: Verify Data Flow
Within 10-30 seconds, you should see:
- Current game ID updating
- Tick counter advancing
- Price changes reflecting live game
- Predictions appearing

## Understanding the Interface

### Reading Predictions

The **Prediction Panel** shows:
```
Predicted Tick: 285
Tolerance: ±50
Confidence: 72%
Remaining: 142
```

This means:
- Game likely ends around tick 285
- Could be 50 ticks earlier or later (235-335)
- System is 72% confident
- 142 ticks remain until predicted end

### Interpreting Side Bet Signals

When you see:
```
Action: PLACE_SIDE_BET
P(win 40): 0.24
EV: +0.20
```

This means:
- ✅ System recommends placing a side bet
- 24% chance of winning (rug within 40 ticks)
- Expected value is positive (+20% over time)

When you see:
```
Action: WAIT
P(win 40): 0.15
EV: -0.25
```

This means:
- ❌ Don't place a side bet now
- Only 15% chance of winning
- Expected value is negative (-25% loss over time)

### Pattern Indicators

Watch the pattern status colors:
- 🟢 **Green (NORMAL)**: Safe, no concerning patterns
- 🟡 **Yellow (MONITORING)**: Pattern emerging, stay alert
- 🟠 **Orange (APPROACHING)**: Risk increasing, consider position
- 🔴 **Red (TRIGGERED)**: High risk detected, extreme caution

## Your First Session

### Warm-Up Phase (Recommended)

**Games 1-5: Observation Only**
- Don't place any bets yet
- Watch how predictions evolve
- Note when TED is right vs wrong
- Get familiar with the patterns

**Games 6-10: Paper Trading**
- Write down what you *would* bet
- Track hypothetical results
- Compare to actual outcomes
- Build confidence in the system

**Games 11+: Start Small**
- Begin with minimum bets
- Follow high-confidence signals only
- Gradually increase as you learn

## Optimal Usage Strategies

### Strategy 1: Conservative Side Betting
Best for: Steady, lower-risk play

1. Only bet when:
   - Action = PLACE_SIDE_BET
   - P(win) > 0.22
   - EV > 0.10

2. Bet sizing:
   - Use 1-2% of bankroll per bet
   - Never chase losses
   - Take breaks after 3 losses

### Strategy 2: Prediction-Based Trading
Best for: Active traders

1. Watch for:
   - High confidence (>75%)
   - Narrow tolerance (±40 or less)
   - Pattern convergence (multiple triggers)

2. Exit positions when:
   - Approaching predicted tick minus tolerance
   - Confidence drops below 60%
   - New patterns emerge

### Strategy 3: Pattern Trading
Best for: Experienced players

1. Focus on pattern transitions:
   - MONITORING → APPROACHING: Consider reducing position
   - APPROACHING → TRIGGERED: Strong exit signal
   - TRIGGERED → NORMAL: Potential re-entry

2. Combine patterns:
   - 1 pattern triggered: Caution
   - 2 patterns triggered: Reduce exposure
   - 3 patterns triggered: Exit immediately

## Common Scenarios

### Scenario: "Predictions Keep Changing"
**Why it happens**: New data refines predictions
**What to do**: Focus on trend direction, not exact numbers

### Scenario: "Wrong Prediction"
**Why it happens**: ~30-35% of predictions miss
**What to do**: This is normal - focus on long-term accuracy

### Scenario: "Conflicting Signals"
**Example**: High confidence but WAIT signal
**What to do**: Trust the side bet signal - it factors in everything

### Scenario: "System Lag"
**Signs**: Tick counter not updating smoothly
**What to do**: Refresh page, check connection

## Best Practices

### ✅ DO:
- Start small and scale gradually
- Keep a trading journal
- Set daily loss limits
- Take regular breaks
- Focus on EV-positive bets
- Trust the math over emotions

### ❌ DON'T:
- Bet more than 5% on any single game
- Chase losses with bigger bets
- Ignore WAIT signals
- Trade when tired or emotional
- Expect 100% accuracy
- Override signals based on "gut feeling"

## Tracking Your Performance

Keep a simple log:
```
Game #1234
- TED Prediction: 280 ±50
- Actual: 265
- Result: ✅ Hit (within range)
- Side Bet: PLACE @ 0.23
- Outcome: Won
- Notes: Pattern 1 triggered at tick 250
```

After 50 games, calculate:
- Win rate on side bets
- Accuracy of predictions
- Profit/loss ratio
- Best performing patterns

## Troubleshooting

### Problem: "No predictions showing"
1. Check connection status
2. Wait 30 seconds for initialization
3. Refresh browser
4. Clear cache and cookies

### Problem: "Predictions seem off"
1. Check if you're in an unusual game (very high multiplier)
2. Note the confidence level
3. Look for active patterns affecting predictions
4. Remember: 30-35% of predictions will miss

### Problem: "Side bet signal not updating"
1. Signals update every 2 seconds
2. Check if within cooldown (4 ticks after last bet)
3. Verify game is active
4. Refresh if stuck

## Advanced Features

### Metrics Dashboard
After several games, check the metrics:
- **Median E40**: Should be near 0 (perfect calibration)
- **Within 2w**: Target is >50% accuracy
- **Coverage**: Should be 83-87%

### Historical Analysis
The prediction history table shows:
- Past predictions vs actual results
- Accuracy trends
- Pattern performance
- Helps identify system strengths/weaknesses

## Getting Help

### Quick Reference
- 🟢 Connected = Good
- High confidence = More reliable
- Positive EV = Favorable bet
- Multiple patterns = Higher risk

### Need Support?
1. Screenshot the issue (include game ID)
2. Note the exact time
3. Describe what you expected vs what happened
4. Send to beta support channel

## Ready to Start?

Remember:
1. **Start slow** - Observe first, bet small
2. **Trust the math** - EV is your friend
3. **Stay disciplined** - Follow your strategy
4. **Have fun** - It's still a game!

---

[← Back to Overview](README_BETA.md) | [How It Works →](HOW_IT_WORKS.md)

*Good luck, and may the odds be ever (slightly more) in your favor!*