#!/usr/bin/env python3
"""
Detailed Backend Testing for Review Request
Tests specific requirements from the hazard/conformal/gate wrapper integration
"""

import requests
import json
import sys
import time
import websocket
import threading
from datetime import datetime

class DetailedBackendTester:
    def __init__(self, base_url="https://pattern-prophet-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        return success

    def test_import_new_modules(self):
        """Test that new modules can be imported without errors"""
        try:
            # Test importing the new modules
            import sys
            sys.path.append('/app/backend')
            
            import hazard_head
            import conformal_wrapper
            import drift_detectors
            import ultra_short_gate
            
            # Test basic functionality
            hazard = hazard_head.DiscreteHazardHead()
            conformal = conformal_wrapper.ConformalPID()
            drift = drift_detectors.SimplePageHinkley()
            gate = ultra_short_gate.UltraShortGate()
            
            return self.log_test("Import New Modules", True, "All new modules imported successfully")
        except Exception as e:
            return self.log_test("Import New Modules", False, f"Import error: {str(e)}")

    def test_patterns_prediction_keys(self):
        """Test /api/patterns returns required prediction dict keys used by frontend"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code != 200:
                return self.log_test("Patterns Prediction Keys", False, f"Status code: {response.status_code}")
            
            data = response.json()
            
            # Check top-level keys
            required_top_keys = ['patterns', 'prediction', 'ml_status']
            missing_top = [k for k in required_top_keys if k not in data]
            if missing_top:
                return self.log_test("Patterns Prediction Keys", False, f"Missing top-level keys: {missing_top}")
            
            # Check prediction dict has required keys
            prediction = data.get('prediction')
            if prediction is None:
                return self.log_test("Patterns Prediction Keys", False, "Prediction is null")
            
            required_pred_keys = ['predicted_tick', 'tolerance', 'confidence']
            missing_pred = [k for k in required_pred_keys if k not in prediction]
            if missing_pred:
                return self.log_test("Patterns Prediction Keys", False, f"Missing prediction keys: {missing_pred}")
            
            # Check ml_status is present
            ml_status = data.get('ml_status')
            if ml_status is None:
                return self.log_test("Patterns Prediction Keys", False, "ml_status is null")
            
            # Verify tolerance is >= 1 (widened tolerance requirement)
            tolerance = prediction.get('tolerance', 0)
            if not isinstance(tolerance, int) or tolerance < 1:
                return self.log_test("Patterns Prediction Keys", False, f"Tolerance should be int >= 1, got: {tolerance}")
            
            details = f"predicted_tick: {prediction.get('predicted_tick')}, tolerance: {tolerance}, confidence: {prediction.get('confidence')}"
            return self.log_test("Patterns Prediction Keys", True, details)
            
        except Exception as e:
            return self.log_test("Patterns Prediction Keys", False, f"Error: {str(e)}")

    def test_websocket_initial_payload(self):
        """Test WebSocket /api/ws initial payload includes prediction and ml_status"""
        try:
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws'
            
            initial_payload_received = False
            payload_data = None
            
            def on_message(ws, message):
                nonlocal initial_payload_received, payload_data
                try:
                    data = json.loads(message)
                    if not initial_payload_received and isinstance(data, dict):
                        # Check if this looks like initial payload (not pong/keepalive)
                        if 'prediction' in data and 'ml_status' in data:
                            initial_payload_received = True
                            payload_data = data
                            self.ws_messages.append(data)
                except:
                    pass
            
            def on_open(ws):
                self.ws_connected = True
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
            
            ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message, on_error=on_error)
            
            # Run WebSocket in thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for initial payload
            timeout = 15
            start_time = time.time()
            while time.time() - start_time < timeout:
                if initial_payload_received:
                    break
                time.sleep(0.5)
            
            ws.close()
            
            if not initial_payload_received:
                return self.log_test("WebSocket Initial Payload", False, "No initial payload with prediction and ml_status received")
            
            # Verify payload structure
            if 'prediction' not in payload_data:
                return self.log_test("WebSocket Initial Payload", False, "Initial payload missing 'prediction'")
            
            if 'ml_status' not in payload_data:
                return self.log_test("WebSocket Initial Payload", False, "Initial payload missing 'ml_status'")
            
            return self.log_test("WebSocket Initial Payload", True, "Initial payload contains prediction and ml_status")
            
        except Exception as e:
            return self.log_test("WebSocket Initial Payload", False, f"Error: {str(e)}")

    def test_websocket_commands(self):
        """Test WebSocket ping and status commands still work"""
        try:
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws'
            
            ping_received = False
            status_received = False
            
            def on_message(ws, message):
                nonlocal ping_received, status_received
                try:
                    data = json.loads(message)
                    if data.get('type') == 'pong':
                        ping_received = True
                    elif 'system' in data or 'connections' in data:
                        status_received = True
                except:
                    pass
            
            def on_open(ws):
                self.ws_connected = True
                # Send commands after connection
                def send_commands():
                    time.sleep(1)
                    ws.send('ping')
                    time.sleep(1)
                    ws.send('status')
                threading.Thread(target=send_commands).start()
            
            ws = websocket.WebSocketApp(ws_url, on_open=on_open, on_message=on_message)
            
            # Run WebSocket in thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for responses
            timeout = 15
            start_time = time.time()
            while time.time() - start_time < timeout:
                if ping_received:  # At minimum, ping should work
                    break
                time.sleep(0.5)
            
            ws.close()
            
            if not ping_received:
                return self.log_test("WebSocket Commands", False, "Ping command did not receive pong response")
            
            details = f"Ping: ✓"
            if status_received:
                details += ", Status: ✓"
            
            return self.log_test("WebSocket Commands", True, details)
            
        except Exception as e:
            return self.log_test("WebSocket Commands", False, f"Error: {str(e)}")

    def test_complete_game_analysis(self):
        """Test complete_game_analysis runs without exception by checking /api/status after updates"""
        try:
            # Get initial status
            response1 = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response1.status_code != 200:
                return self.log_test("Complete Game Analysis", False, f"Initial status check failed: {response1.status_code}")
            
            initial_data = response1.json()
            
            # Wait a moment for any background processing
            time.sleep(2)
            
            # Get status again
            response2 = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response2.status_code != 200:
                return self.log_test("Complete Game Analysis", False, f"Second status check failed: {response2.status_code}")
            
            final_data = response2.json()
            
            # Check system is still running and no errors
            if final_data.get('system', {}).get('status') != 'running':
                return self.log_test("Complete Game Analysis", False, f"System status not running: {final_data.get('system', {}).get('status')}")
            
            # Check ML status is still present and functional
            if 'ml' not in final_data:
                return self.log_test("Complete Game Analysis", False, "ML status missing from system status")
            
            return self.log_test("Complete Game Analysis", True, "System remains stable, complete_game_analysis functioning")
            
        except Exception as e:
            return self.log_test("Complete Game Analysis", False, f"Error: {str(e)}")

    def test_side_bet_endpoints_unchanged(self):
        """Test side-bet endpoints are unchanged"""
        try:
            response = requests.get(f"{self.base_url}/api/side-bet", timeout=10)
            if response.status_code != 200:
                return self.log_test("Side-Bet Endpoints Unchanged", False, f"Status code: {response.status_code}")
            
            data = response.json()
            required_keys = ['recommendation', 'performance', 'history']
            missing_keys = [k for k in required_keys if k not in data]
            
            if missing_keys:
                return self.log_test("Side-Bet Endpoints Unchanged", False, f"Missing keys: {missing_keys}")
            
            return self.log_test("Side-Bet Endpoints Unchanged", True, "All required keys present")
            
        except Exception as e:
            return self.log_test("Side-Bet Endpoints Unchanged", False, f"Error: {str(e)}")

    def run_detailed_tests(self):
        """Run all detailed tests for the review request"""
        print("🔬 Starting Detailed Backend Tests - Review Request Validation")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 70)
        
        print("1) Testing import of new modules...")
        self.test_import_new_modules()
        
        print("\n2) Testing /api/patterns prediction dict keys...")
        self.test_patterns_prediction_keys()
        
        print("\n3) Testing WebSocket initial payload...")
        self.test_websocket_initial_payload()
        
        print("\n4) Testing WebSocket ping/status commands...")
        self.test_websocket_commands()
        
        print("\n5) Testing complete_game_analysis stability...")
        self.test_complete_game_analysis()
        
        print("\n6) Testing side-bet endpoints unchanged...")
        self.test_side_bet_endpoints_unchanged()
        
        # Summary
        print("=" * 70)
        print(f"📊 Detailed Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All detailed tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} detailed tests failed")
            return 1

def main():
    """Main test runner"""
    tester = DetailedBackendTester()
    return tester.run_detailed_tests()

if __name__ == "__main__":
    sys.exit(main())