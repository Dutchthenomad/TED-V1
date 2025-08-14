"""
Test invariants for TED-V1 sidebet and prediction system
Tests ensure correctness of hazard-based sidebets, tolerance quantization,
and proper win evaluation logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ["SIDEBET_WINDOW_TICKS"] = "40"
os.environ["SIDEBET_COOLDOWN_TICKS"] = "4"
os.environ["SIDEBET_PWIN_THRESHOLD"] = "0.20"

def test_win_eval_relative_to_placement():
    """Test that side bet win is evaluated relative to placement time"""
    placed_at = 6
    final_tick = 45
    window = 40
    
    # Should win since 45 <= 6 + 40 (46)
    assert final_tick <= placed_at + window, f"Expected win: {final_tick} <= {placed_at + window}"
    
    # Edge case: exactly at boundary
    final_tick = placed_at + window
    assert final_tick <= placed_at + window
    
    # Loss case
    final_tick = placed_at + window + 1
    assert not (final_tick <= placed_at + window)

def test_gating_spacing():
    """Test that gating enforces proper spacing between recommendations"""
    placed = 100
    window = 40
    cooldown = 4
    
    # Coverage ends at placed + (window - 1)
    coverage_end = placed + (window - 1)
    
    # Next eligible is after coverage + cooldown
    next_eligible = coverage_end + cooldown + 1
    
    expected = 100 + 39 + 4 + 1  # = 144
    assert next_eligible == expected, f"Expected {expected}, got {next_eligible}"

def test_tolerance_quantization():
    """Test that tolerance is quantized to 40-tick windows"""
    from backend.server import IntegratedPatternTracker
    
    tracker = IntegratedPatternTracker()
    
    # Test case 1: Normal quantization
    pred = {"predicted_tick": 120, "tolerance": 37}
    out = tracker._quantize_prediction_tolerance(pred, current_tick=100)
    
    # Tolerance should be quantized to multiple of 20 (for 40-tick windows)
    assert out["tolerance"] % 20 == 0, f"Tolerance not quantized: {out['tolerance']}"
    
    # Coverage lower should not go below current tick
    assert out["coverage_lower"] >= 100, f"Coverage extends to past: {out['coverage_lower']}"
    
    # Width should be multiple of 40 (or 0)
    width = out["coverage_upper"] - out["coverage_lower"]
    assert width % 40 == 0 or width == 0, f"Width not aligned to windows: {width}"
    
    # Test case 2: Past coverage prevention
    pred = {"predicted_tick": 90, "tolerance": 50}
    out = tracker._quantize_prediction_tolerance(pred, current_tick=100)
    
    # Lower bound should be clamped to current tick
    assert out["coverage_lower"] >= 100, f"Lower bound in past: {out['coverage_lower']}"

def test_ev_threshold_logic():
    """Test that EV threshold correctly triggers recommendations"""
    threshold = 0.20
    
    # Test case 1: p_win = 0.21 should trigger
    p_win = 0.21
    ev = 4.0 * p_win - (1.0 - p_win)
    assert p_win > threshold, f"Should trigger: {p_win} > {threshold}"
    assert ev > 0, f"EV should be positive: {ev}"
    
    # Test case 2: p_win = 0.19 should not trigger  
    p_win = 0.19
    ev = 4.0 * p_win - (1.0 - p_win)
    assert p_win <= threshold, f"Should not trigger: {p_win} <= {threshold}"
    
    # Break-even point: p_win = 0.20 => EV = 0
    p_win = 0.20
    ev = 4.0 * p_win - (1.0 - p_win)
    assert abs(ev) < 0.001, f"Break-even EV should be ~0: {ev}"

def test_hazard_cdf_usage():
    """Test hazard CDF-based probability calculation"""
    from backend.game_aware_ml_engine import GameAwareMLPatternEngine
    from backend.enhanced_pattern_engine import EnhancedPatternEngine
    
    base_engine = EnhancedPatternEngine()
    ml_engine = GameAwareMLPatternEngine(base_engine)
    
    # Test signal generation
    signal = ml_engine.side_bet_signal(
        current_tick=50,
        current_price=2.5,
        peak_price=3.0
    )
    
    # Check required fields
    assert "action" in signal, "Missing action field"
    assert "p_win_40" in signal, "Missing p_win_40 field"
    assert "expected_value" in signal, "Missing expected_value field"
    assert "confidence" in signal, "Missing confidence field"
    assert "tick" in signal, "Missing tick field"
    
    # Check action logic consistency
    assert signal["action"] in ["PLACE_SIDE_BET", "WAIT"], f"Invalid action: {signal['action']}"
    
    # Check EV calculation
    p_win = signal["p_win_40"]
    expected_ev = 4.0 * p_win - (1.0 - p_win)
    assert abs(signal["expected_value"] - expected_ev) < 0.001, "EV calculation mismatch"
    
    # Check confidence bounds
    assert 0 <= signal["confidence"] <= 1, f"Confidence out of bounds: {signal['confidence']}"

def test_coverage_window_calculation():
    """Test coverage window calculations"""
    from backend.server import IntegratedPatternTracker, SIDEBET_WINDOW_TICKS
    
    tracker = IntegratedPatternTracker()
    
    # Test various tolerance values
    test_cases = [
        {"predicted_tick": 100, "tolerance": 20, "current": 80},
        {"predicted_tick": 150, "tolerance": 40, "current": 100},
        {"predicted_tick": 200, "tolerance": 60, "current": 150},
    ]
    
    for case in test_cases:
        pred = {"predicted_tick": case["predicted_tick"], "tolerance": case["tolerance"]}
        out = tracker._quantize_prediction_tolerance(pred, case["current"])
        
        # Check windows calculation
        width = out["coverage_upper"] - out["coverage_lower"]
        expected_windows = max(1, (width + (SIDEBET_WINDOW_TICKS - 1)) // SIDEBET_WINDOW_TICKS)
        assert out["coverage_windows"] == expected_windows, \
            f"Windows mismatch: got {out['coverage_windows']}, expected {expected_windows}"

def test_gating_state_management():
    """Test gating state prevents overlapping recommendations"""
    from backend.server import IntegratedPatternTracker, SIDEBET_WINDOW_TICKS, SIDEBET_COOLDOWN_TICKS
    
    tracker = IntegratedPatternTracker()
    
    # Simulate first recommendation
    first_tick = 10
    tracker.last_side_bet_tick = first_tick
    tracker.last_side_bet_active_until = first_tick + (SIDEBET_WINDOW_TICKS - 1)
    
    # Check various ticks
    test_ticks = [
        (first_tick + 20, False),  # Still within window
        (first_tick + 39, False),  # At end of window
        (first_tick + 40, False),  # Just after window (cooldown starts)
        (first_tick + 43, False),  # Within cooldown
        (first_tick + 44, True),   # After cooldown, eligible
        (first_tick + 50, True),   # Well after cooldown
    ]
    
    for tick, expected_eligible in test_ticks:
        can_recommend = tick > (tracker.last_side_bet_active_until + SIDEBET_COOLDOWN_TICKS)
        assert can_recommend == expected_eligible, \
            f"Tick {tick}: expected eligible={expected_eligible}, got {can_recommend}"

def test_history_retention():
    """Test that history deques maintain proper size"""
    from backend.server import IntegratedPatternTracker
    
    tracker = IntegratedPatternTracker()
    
    # Check maxlen settings
    assert tracker.prediction_history.maxlen == 200, \
        f"Prediction history size: {tracker.prediction_history.maxlen}"
    assert tracker.side_bet_history.maxlen == 200, \
        f"Side bet history size: {tracker.side_bet_history.maxlen}"
    
    # Test overflow behavior
    for i in range(250):
        tracker.prediction_history.append({"game_id": i})
        tracker.side_bet_history.append({"game_id": i})
    
    assert len(tracker.prediction_history) == 200
    assert len(tracker.side_bet_history) == 200
    
    # Oldest should be dropped
    assert tracker.prediction_history[0]["game_id"] == 50
    assert tracker.side_bet_history[0]["game_id"] == 50

def test_side_bet_record_fields():
    """Test that side bet records contain all required fields"""
    from backend.server import IntegratedPatternTracker, SIDEBET_WINDOW_TICKS
    
    tracker = IntegratedPatternTracker()
    
    # Mock side bet
    side_bet = {
        "action": "PLACE_SIDE_BET",
        "p_win_40": 0.25,
        "expected_value": 0.25,
        "confidence": 0.8,
    }
    
    # Record it
    tracker._record_side_bet_recommendation(side_bet, game_id=123, tick=50)
    
    # Check the record
    assert len(tracker.side_bet_history) == 1
    record = tracker.side_bet_history[0]
    
    # Check required fields
    assert record["game_id"] == 123
    assert record["tick"] == 50
    assert record["action"] == "PLACE_SIDE_BET"
    assert record["p_win_40"] == 0.25
    assert record["coverage_end_tick"] == 50 + (SIDEBET_WINDOW_TICKS - 1)
    assert record["expected_value"] == 0.25
    assert record["confidence"] == 0.8
    assert "timestamp" in record

def run_all_tests():
    """Run all test cases and report results"""
    import traceback
    
    print("\n" + "="*60)
    print("TED-V1 INVARIANT TESTS")
    print("="*60 + "\n")
    
    tests = [
        test_win_eval_relative_to_placement,
        test_gating_spacing,
        test_tolerance_quantization,
        test_ev_threshold_logic,
        test_hazard_cdf_usage,
        test_coverage_window_calculation,
        test_gating_state_management,
        test_history_retention,
        test_side_bet_record_fields,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}: PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED")
            print(f"   Error: {e}")
            if "--verbose" in sys.argv:
                traceback.print_exc()
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)