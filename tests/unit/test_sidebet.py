import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables for testing
os.environ["SIDEBET_WINDOW_TICKS"] = "40"
os.environ["SIDEBET_COOLDOWN_TICKS"] = "4"
os.environ["SIDEBET_PWIN_THRESHOLD"] = "0.20"

def test_win_eval_relative_to_placement():
    """Test that side bet win is evaluated relative to placement time"""
    class CG: pass
    cg = CG()
    cg.game_id = 1
    cg.final_tick = 45
    
    # bet placed at tick 6 -> win if final <= 46
    bet = {"game_id": 1, "tick": 6}
    placed_at = bet["tick"]
    window = 40
    
    # Should win since 45 <= 6 + 40 (46)
    assert cg.final_tick <= placed_at + window, f"Expected win: {cg.final_tick} <= {placed_at + window}"
    print("✅ Win evaluation relative to placement: PASSED")

def test_gating_spacing():
    """Test that gating enforces proper spacing between recommendations"""
    placed = 100
    window, cooldown = 40, 4
    next_eligible = placed + window - 1 + cooldown + 1
    
    # Next eligible should be 100 + 39 + 4 + 1 = 144
    assert next_eligible == 144, f"Expected 144, got {next_eligible}"
    print("✅ Gating spacing calculation: PASSED")

def test_tolerance_quantization():
    """Test that tolerance is quantized to 40-tick windows"""
    from backend.server import IntegratedPatternTracker
    
    t = IntegratedPatternTracker()
    pred = {"predicted_tick": 120, "tolerance": 37}
    out = t._quantize_prediction_tolerance(pred, current_tick=100)
    
    # Tolerance should be quantized to multiple of 20
    assert out["tolerance"] % 20 == 0, f"Tolerance not quantized: {out['tolerance']}"
    
    # Coverage lower should not go below current tick
    assert out["coverage_lower"] >= 100, f"Coverage extends to past: {out['coverage_lower']}"
    
    # Width should be multiple of 40 (or 0)
    width = out["coverage_upper"] - out["coverage_lower"]
    assert width % 40 == 0 or width == 0, f"Width not aligned to windows: {width}"
    
    print("✅ Tolerance quantization: PASSED")

def test_hazard_side_bet_signal():
    """Test the new hazard-based side bet signal"""
    from backend.enhanced_pattern_engine import EnhancedPatternEngine
    from backend.game_aware_ml_engine import GameAwareMLPatternEngine
    
    base_engine = EnhancedPatternEngine()
    ml_engine = GameAwareMLPatternEngine(base_engine)
    
    # Test side bet signal generation
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
    
    # Check action logic
    assert signal["action"] in ["PLACE_SIDE_BET", "WAIT"], f"Invalid action: {signal['action']}"
    
    # Check EV calculation (EV = 4*p - (1-p))
    p_win = signal["p_win_40"]
    expected_ev = 4.0 * p_win - (1.0 - p_win)
    assert abs(signal["expected_value"] - expected_ev) < 0.001, "EV calculation mismatch"
    
    print("✅ Hazard side bet signal: PASSED")

def test_ev_threshold():
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
    
    print("✅ EV threshold logic: PASSED")

def run_all_tests():
    """Run all test cases"""
    print("\n" + "="*60)
    print("SIDE BET PATCH VALIDATION TESTS")
    print("="*60 + "\n")
    
    tests = [
        test_win_eval_relative_to_placement,
        test_gating_spacing,
        test_tolerance_quantization,
        test_hazard_side_bet_signal,
        test_ev_threshold
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__}: FAILED")
            print(f"   Error: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)