#!/usr/bin/env python3
"""
Smoke test for side-bet patch - verifies the patch was applied correctly
by checking for the presence of new functions and constants.
"""

import os
import re

def check_file_contains(filepath, pattern, description):
    """Check if a file contains a specific pattern"""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if re.search(pattern, content):
                print(f"✅ {description}: FOUND")
                return True
            else:
                print(f"❌ {description}: NOT FOUND")
                return False
    except Exception as e:
        print(f"❌ {description}: ERROR - {e}")
        return False

def main():
    print("\n" + "="*60)
    print("SIDE BET PATCH SMOKE TEST")
    print("="*60 + "\n")
    
    checks = [
        # Check game_aware_ml_engine.py for side_bet_signal method
        ("backend/game_aware_ml_engine.py", 
         r"def side_bet_signal\(self.*current_tick.*current_price.*peak_price",
         "Hazard-based side_bet_signal method"),
        
        # Check server.py for environment constants
        ("backend/server.py",
         r"SIDEBET_WINDOW_TICKS.*=.*int\(os\.getenv",
         "SIDEBET_WINDOW_TICKS constant"),
        
        ("backend/server.py",
         r"SIDEBET_COOLDOWN_TICKS.*=.*int\(os\.getenv",
         "SIDEBET_COOLDOWN_TICKS constant"),
        
        ("backend/server.py",
         r"SIDEBET_PWIN_THRESHOLD.*=.*float\(os\.getenv",
         "SIDEBET_PWIN_THRESHOLD constant"),
        
        # Check for tolerance quantization
        ("backend/server.py",
         r"def _quantize_prediction_tolerance\(self.*prediction.*current_tick",
         "Tolerance quantization helper"),
        
        # Check for gating state
        ("backend/server.py",
         r"self\.last_side_bet_tick.*=.*None",
         "Gating state: last_side_bet_tick"),
        
        ("backend/server.py",
         r"self\.last_side_bet_active_until.*=.*None",
         "Gating state: last_side_bet_active_until"),
        
        # Check for updated side bet history size
        ("backend/server.py",
         r"self\.side_bet_history.*=.*deque\(maxlen=200\)",
         "Side bet history increased to 200"),
        
        # Check for new side bet logic in process_game_update
        ("backend/server.py",
         r"side_bet.*=.*self\.ml_engine\.side_bet_signal",
         "New hazard-based side bet call"),
        
        # Check for corrected win evaluation
        ("backend/server.py",
         r"placed_at.*=.*bet\.get\('tick'",
         "Relative placement time for win evaluation"),
        
        # Check for updated REST endpoint
        ("backend/server.py",
         r"side_bet.*=.*pattern_tracker\.ml_engine\.side_bet_signal",
         "Updated REST endpoint to use new signal"),
        
        # Check for coverage fields in tolerance
        ("backend/server.py",
         r'prediction\["coverage_lower"\].*=.*lower',
         "Coverage lower bound calculation"),
        
        ("backend/server.py",
         r'prediction\["coverage_windows"\].*=.*windows',
         "Coverage windows calculation"),
    ]
    
    passed = 0
    failed = 0
    
    for filepath, pattern, description in checks:
        if check_file_contains(filepath, pattern, description):
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*60)
    print(f"RESULTS: {passed}/{len(checks)} checks passed")
    if failed == 0:
        print("🎉 All patch components verified successfully!")
    else:
        print(f"⚠️  {failed} checks failed - patch may be incomplete")
    print("="*60)
    
    return failed == 0

if __name__ == "__main__":
    import sys
    os.chdir("/mnt/c/Users/nomad/OneDrive/Desktop/GRAD_STUDIES/TED-V1")
    success = main()
    sys.exit(0 if success else 1)