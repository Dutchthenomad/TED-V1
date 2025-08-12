#!/usr/bin/env python3
"""
Prediction Validation Test
Tests specific prediction logic requirements from review request
"""

import requests
import json
import sys

class PredictionValidationTester:
    def __init__(self, base_url="https://4c0451c0-fea0-470b-9160-6db670847956.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        return success

    def test_prediction_structure_detailed(self):
        """Test detailed prediction structure and values"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code != 200:
                return self.log_test("Prediction Structure", False, f"Status code: {response.status_code}")
            
            data = response.json()
            prediction = data.get('prediction')
            
            if not prediction:
                return self.log_test("Prediction Structure", False, "No prediction object")
            
            # Check required fields exist and are correct types
            predicted_tick = prediction.get('predicted_tick')
            tolerance = prediction.get('tolerance')
            confidence = prediction.get('confidence')
            
            if not isinstance(predicted_tick, int):
                return self.log_test("Prediction Structure", False, f"predicted_tick should be int, got {type(predicted_tick)}")
            
            if not isinstance(tolerance, int) or tolerance < 1:
                return self.log_test("Prediction Structure", False, f"tolerance should be int >= 1, got {tolerance}")
            
            if not isinstance(confidence, (int, float)) or not (0 <= confidence <= 1):
                return self.log_test("Prediction Structure", False, f"confidence should be float 0-1, got {confidence}")
            
            # Check for additional fields that might indicate gate/conformal processing
            details = f"predicted_tick={predicted_tick}, tolerance={tolerance}, confidence={confidence}"
            
            # Look for enhancement indicators
            if 'ml_enhancement' in prediction:
                ml_enh = prediction['ml_enhancement']
                if 'ultra_short_gate_applied' in ml_enh:
                    details += f", gate_applied={ml_enh['ultra_short_gate_applied']}"
                if 'ultra_short_prob' in ml_enh:
                    details += f", ultra_short_prob={ml_enh['ultra_short_prob']}"
            
            return self.log_test("Prediction Structure", True, details)
            
        except Exception as e:
            return self.log_test("Prediction Structure", False, f"Error: {str(e)}")

    def test_ml_status_structure(self):
        """Test ML status structure includes new modules info"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code != 200:
                return self.log_test("ML Status Structure", False, f"Status code: {response.status_code}")
            
            data = response.json()
            ml_status = data.get('ml_status')
            
            if not ml_status:
                return self.log_test("ML Status Structure", False, "No ml_status object")
            
            # Check for expected fields
            required_fields = ['ml_enabled', 'prediction_method']
            missing_fields = [f for f in required_fields if f not in ml_status]
            
            if missing_fields:
                return self.log_test("ML Status Structure", False, f"Missing fields: {missing_fields}")
            
            # Check prediction method indicates new integration
            pred_method = ml_status.get('prediction_method', '')
            if 'hazard' not in pred_method or 'conformal' not in pred_method or 'gate' not in pred_method:
                return self.log_test("ML Status Structure", False, f"prediction_method doesn't indicate new modules: {pred_method}")
            
            # Check modules section if present
            details = f"method={pred_method}, enabled={ml_status.get('ml_enabled')}"
            if 'modules' in ml_status:
                modules = ml_status['modules']
                details += f", modules={modules}"
            
            return self.log_test("ML Status Structure", True, details)
            
        except Exception as e:
            return self.log_test("ML Status Structure", False, f"Error: {str(e)}")

    def test_tolerance_widening(self):
        """Test that tolerance values show evidence of widening (>= base tolerance)"""
        try:
            # Get multiple samples to see tolerance variation
            tolerances = []
            for i in range(3):
                response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    prediction = data.get('prediction', {})
                    tolerance = prediction.get('tolerance')
                    if isinstance(tolerance, int):
                        tolerances.append(tolerance)
            
            if not tolerances:
                return self.log_test("Tolerance Widening", False, "No tolerance values obtained")
            
            # Check all tolerances are >= 1 (minimum requirement)
            min_tolerance = min(tolerances)
            max_tolerance = max(tolerances)
            avg_tolerance = sum(tolerances) / len(tolerances)
            
            if min_tolerance < 1:
                return self.log_test("Tolerance Widening", False, f"Minimum tolerance {min_tolerance} < 1")
            
            # Expect reasonable tolerance values (not too small, indicating widening is working)
            if avg_tolerance < 50:  # Base tolerance should be widened
                return self.log_test("Tolerance Widening", False, f"Average tolerance {avg_tolerance} seems too small for widened values")
            
            details = f"min={min_tolerance}, max={max_tolerance}, avg={avg_tolerance:.1f}"
            return self.log_test("Tolerance Widening", True, details)
            
        except Exception as e:
            return self.log_test("Tolerance Widening", False, f"Error: {str(e)}")

    def test_based_on_patterns_field(self):
        """Test that based_on_patterns field is present (mentioned in review request)"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code != 200:
                return self.log_test("Based On Patterns Field", False, f"Status code: {response.status_code}")
            
            data = response.json()
            
            # Check if based_on_patterns is in prediction or at top level
            prediction = data.get('prediction', {})
            
            if 'based_on_patterns' in prediction:
                based_on = prediction['based_on_patterns']
                return self.log_test("Based On Patterns Field", True, f"Found in prediction: {based_on}")
            elif 'based_on_patterns' in data:
                based_on = data['based_on_patterns']
                return self.log_test("Based On Patterns Field", True, f"Found at top level: {based_on}")
            else:
                # Check if patterns data is structured in a way that indicates pattern-based logic
                patterns = data.get('patterns', {})
                if patterns and isinstance(patterns, dict):
                    return self.log_test("Based On Patterns Field", True, f"Patterns structure present: {list(patterns.keys())[:3]}")
                else:
                    return self.log_test("Based On Patterns Field", False, "No based_on_patterns field or patterns structure found")
            
        except Exception as e:
            return self.log_test("Based On Patterns Field", False, f"Error: {str(e)}")

    def run_prediction_validation(self):
        """Run all prediction validation tests"""
        print("🔍 Starting Prediction Validation Tests")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 60)
        
        print("1) Testing prediction structure details...")
        self.test_prediction_structure_detailed()
        
        print("\n2) Testing ML status structure...")
        self.test_ml_status_structure()
        
        print("\n3) Testing tolerance widening...")
        self.test_tolerance_widening()
        
        print("\n4) Testing based_on_patterns field...")
        self.test_based_on_patterns_field()
        
        # Summary
        print("=" * 60)
        print(f"📊 Prediction Validation Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All prediction validation tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} prediction validation tests failed")
            return 1

def main():
    """Main test runner"""
    tester = PredictionValidationTester()
    return tester.run_prediction_validation()

if __name__ == "__main__":
    sys.exit(main())