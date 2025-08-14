# Future Integration Plan (Listen-Only HUD)

These are optional add-ons designed for a **listen-only HUD**. They do not automate gameplay but improve trust, insight, and iteration speed.

## PR-F1: Session EV & Bankroll Simulation (UI only)

### Purpose
Provide visual bankroll management insights without automation.

### Implementation
**Component**: `SessionSimPanel.jsx` (no API)

**Inputs**:
- Bankroll amount
- Base bet size
- Threshold (raw vs calibrated p)
- Attempts per game
- Games per session

**Logic**:
```javascript
// src/SessionSimPanel.jsx (scaffold)
export function sessionStats({ p, b=4, bets, bankroll, f }) {
  const evPerBet = b*p - (1-p);           // net +4/-1
  const varPerBet = (b**2)*p + (1**2)*(1-p) - evPerBet**2;
  return {
    ev: evPerBet * bets,
    sd: Math.sqrt(varPerBet * bets),
    kelly: Math.max(0, (b*p - (1-p)) / b),
  };
}
```

**Output**:
- Expected session ROI
- Standard deviation
- P(max drawdown ≥ X)
- Probability of ruin under N attempts
- Kelly fraction (advisory only)

**Feature Flag**: `REACT_APP_FEATURE_SESSION_SIM=true`

## PR-F2: Persistent Telemetry

### Purpose
Track predictions, outcomes, and latency for continuous improvement.

### Database Schema
```sql
CREATE TABLE hud_events (
  id SERIAL PRIMARY KEY,
  game_id VARCHAR(100),
  tick INTEGER,
  predicted_tick INTEGER,
  tolerance INTEGER,
  p_win_40_raw FLOAT,
  p_win_40_cal FLOAT,
  action VARCHAR(20),
  final_tick INTEGER,
  sidebet_win BOOLEAN,
  latency_ms INTEGER,
  version VARCHAR(20),
  created_at TIMESTAMP DEFAULT NOW()
);
```

### Endpoints
- `POST /api/telemetry` - Client-side timing intake (optional)
- Internal write on game completion

### Analytics
**Nightly job/notebook**:
- Reliability curves
- EV by decile
- Conformal coverage vs target (0.85)
- Drift episode detection

### Sample Analysis
```python
# backend/analysis/nightly_reliability.py
def analyze_calibration(df):
    # Bucket by p_win_40
    bins = np.linspace(0, 1, 11)
    df['p_bucket'] = pd.cut(df['p_win_40_raw'], bins)
    
    # Compare predicted vs actual
    calibration = df.groupby('p_bucket').agg({
        'sidebet_win': 'mean',
        'p_win_40_raw': 'mean'
    })
    
    return calibration
```

## PR-F3: Probability Calibration Layer

### Purpose
Improve prediction accuracy through isotonic regression calibration.

### Offline Training
```python
# backend/calibration/calibrate_isotonic.py
from sklearn.isotonic import IsotonicRegression
import joblib

# Fit on historical data
X = df['p_win_40_raw'].values
y = df['label_within40'].values
calibrator = IsotonicRegression(out_of_bounds='clip')
calibrator.fit(X, y)

# Save
joblib.dump(calibrator, 'calibrator.joblib')
```

### Runtime Integration
```python
# backend/calibration_service.py
class CalibrationService:
    def __init__(self):
        self.calibrator = None
        if os.getenv("USE_CALIBRATED_P", "false") == "true":
            self.calibrator = joblib.load('calibrator.joblib')
    
    def calibrate(self, p_raw):
        if self.calibrator:
            return float(self.calibrator.predict([p_raw])[0])
        return p_raw
```

### API Response
```json
{
  "p_win_40_raw": 0.23,
  "p_win_40_cal": 0.21,
  "use_calibrated": true
}
```

## PR-F4: A/B Feature Flags (Presentation Only)

### Purpose
Test different thresholds and horizons without automation.

### Implementation

**Backend Cohort Assignment**:
```python
# backend/ab_testing.py
def assign_cohort(client_id):
    variants = os.getenv("SIDEBET_PWIN_THRESHOLD_VARIANTS", "0.20,0.22").split(",")
    hash_val = hashlib.md5(client_id.encode()).hexdigest()
    cohort_idx = int(hash_val, 16) % len(variants)
    return {
        "cohort_id": f"threshold_{variants[cohort_idx]}",
        "threshold": float(variants[cohort_idx])
    }
```

**Frontend Display**:
```javascript
// Show cohort in footer
<div className="text-xs text-gray-500">
  Cohort: {cohortId} | Threshold: {threshold}
</div>
```

**Variants to Test**:
- Threshold: 0.20 vs 0.22
- Horizon: 40 vs 50 ticks
- Display format variations

## PR-F5: Expanded Backend Tests

### Test Coverage Areas

```python
# tests/test_comprehensive.py

def test_hazard_monotonicity():
    """Ensure hazard CDF is monotonic"""
    cdf = hazard.get_cdf()
    for i in range(1, len(cdf)):
        assert cdf[i] >= cdf[i-1], "CDF not monotonic"

def test_conformal_coverage():
    """Test conformal prediction coverage"""
    # Run 1000 predictions
    # Check that ~85% fall within tolerance bands
    
def test_drift_detection_sensitivity():
    """Test drift detector triggers appropriately"""
    # Inject distribution shift
    # Verify detector fires within N samples

def test_side_bet_edge_cases():
    """Test edge cases in side bet logic"""
    # Test at game boundaries (tick 0, tick 1000)
    # Test with extreme probabilities (0.001, 0.999)
    # Test with missing data
```

### CI Integration
```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=backend --cov-report=term
```

## Implementation Timeline

### Phase 1 (Week 1-2)
- [ ] PR-F1: Session EV Simulation
- [ ] PR-F5: Comprehensive Tests

### Phase 2 (Week 3-4)
- [ ] PR-F2: Telemetry Infrastructure
- [ ] Initial data collection

### Phase 3 (Week 5-6)
- [ ] PR-F3: Calibration Layer
- [ ] Validation on collected data

### Phase 4 (Week 7-8)
- [ ] PR-F4: A/B Testing Framework
- [ ] Deploy experiments

## Success Metrics

### Technical
- Test coverage >80%
- API response time <50ms p99
- Calibration error <5%
- Drift detection latency <100 samples

### Business
- Side bet win rate within 2% of predicted
- EV positive over 1000+ games
- User engagement metrics (time on dashboard)

## Risk Mitigation

### Data Quality
- Validate all telemetry entries
- Detect and filter outliers
- Monitor for data drift

### Performance
- Cache calibration models
- Batch telemetry writes
- Use connection pooling

### Privacy
- No PII in telemetry
- Aggregate reporting only
- Data retention policy (90 days)

## Documentation Requirements

Each PR should include:
1. Design document
2. API documentation
3. Test plan
4. Rollback procedure
5. Monitoring setup

## Notes

- All features are **listen-only** (no automation)
- Each PR is independent and can be deployed separately
- Feature flags allow gradual rollout
- Telemetry provides feedback loop for improvements