#!/usr/bin/env python3
"""
Detailed Regression Test for ConnectionManager Integration
Verifies specific requirements from review request
"""

import requests
import websocket
import json
import sys
import time
import threading
from datetime import datetime

class DetailedRegressionTester:
    def __init__(self, base_url="https://treasury-insight-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.ws_messages = []
        self.ws_connected = False
        self.ws_error = None

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        return success

    def test_health_detailed(self):
        """Verify /api/health returns healthy and version 2.0.0"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code != 200:
                return self.log_test("Health Detailed", False, f"Status code: {response.status_code}")
            
            data = response.json()
            
            # Check status is exactly 'healthy'
            if data.get('status') != 'healthy':
                return self.log_test("Health Detailed", False, f"Status is '{data.get('status')}', expected 'healthy'")
            
            # Check version is exactly '2.0.0'
            if data.get('version') != '2.0.0':
                return self.log_test("Health Detailed", False, f"Version is '{data.get('version')}', expected '2.0.0'")
            
            return self.log_test("Health Detailed", True, f"Status: {data.get('status')}, Version: {data.get('version')}")
            
        except Exception as e:
            return self.log_test("Health Detailed", False, f"Error: {str(e)}")

    def test_status_detailed(self):
        """Verify /api/status includes system, connections, statistics, ml, side_bet_performance"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code != 200:
                return self.log_test("Status Detailed", False, f"Status code: {response.status_code}")
            
            data = response.json()
            required_sections = ['system', 'connections', 'statistics', 'ml', 'side_bet_performance']
            missing_sections = [section for section in required_sections if section not in data]
            
            if missing_sections:
                return self.log_test("Status Detailed", False, f"Missing sections: {missing_sections}")
            
            # Verify structure
            details = []
            if 'system' in data and isinstance(data['system'], dict):
                details.append(f"system✓({len(data['system'])} keys)")
            if 'connections' in data and isinstance(data['connections'], dict):
                details.append(f"connections✓({len(data['connections'])} keys)")
            if 'statistics' in data and isinstance(data['statistics'], dict):
                details.append(f"statistics✓({len(data['statistics'])} keys)")
            if 'ml' in data and isinstance(data['ml'], dict):
                details.append(f"ml✓({len(data['ml'])} keys)")
            if 'side_bet_performance' in data and isinstance(data['side_bet_performance'], dict):
                details.append(f"side_bet_performance✓({len(data['side_bet_performance'])} keys)")
            
            return self.log_test("Status Detailed", True, ", ".join(details))
            
        except Exception as e:
            return self.log_test("Status Detailed", False, f"Error: {str(e)}")

    def on_ws_message(self, ws, message):
        """WebSocket message handler"""
        try:
            data = json.loads(message)
            self.ws_messages.append(data)
            msg_type = data.get('type', 'initial_payload')
            print(f"📨 WebSocket received: {msg_type}")
        except json.JSONDecodeError:
            self.ws_messages.append(message)
            print(f"📨 WebSocket received raw: {message[:100]}...")

    def on_ws_error(self, ws, error):
        """WebSocket error handler"""
        self.ws_error = str(error)
        print(f"❌ WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        print(f"🔌 WebSocket closed")

    def on_ws_open(self, ws):
        """WebSocket open handler"""
        self.ws_connected = True
        print("🔗 WebSocket connected")
        
        # Send ping after connection
        def send_ping():
            time.sleep(2)
            ws.send('ping')
            print("📤 Sent ping")
        
        threading.Thread(target=send_ping).start()

    def test_websocket_detailed(self):
        """Test WebSocket: connects, initial payload structure, ping response"""
        try:
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws'
            print(f"🔌 Connecting to WebSocket: {ws_url}")
            
            ws = websocket.WebSocketApp(
                ws_url,
                on_open=self.on_ws_open,
                on_message=self.on_ws_message,
                on_error=self.on_ws_error,
                on_close=self.on_ws_close
            )
            
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            # Wait for connection and messages
            timeout = 15
            start_time = time.time()
            initial_payload_received = False
            ping_response_received = False
            
            while time.time() - start_time < timeout:
                if self.ws_error:
                    ws.close()
                    return self.log_test("WebSocket Detailed", False, f"Connection error: {self.ws_error}")
                
                if self.ws_connected and self.ws_messages:
                    # Check for initial payload with required structure
                    for msg in self.ws_messages:
                        if isinstance(msg, dict):
                            if msg.get('type') == 'pong':
                                ping_response_received = True
                                print("📨 Received pong response")
                            elif not initial_payload_received:
                                # Check for initial payload structure
                                required_keys = ['prediction_history', 'ml_status', 'side_bet_performance']
                                present_keys = [key for key in required_keys if key in msg]
                                
                                if present_keys:
                                    initial_payload_received = True
                                    print(f"📨 Initial payload contains: {present_keys}")
                                    
                                    # Check for prediction_history with end_price and diff
                                    if 'prediction_history' in msg:
                                        history = msg['prediction_history']
                                        if isinstance(history, list) and len(history) > 0:
                                            # Check if records have end_price and diff fields
                                            sample_record = history[0]
                                            has_end_price = 'end_price' in sample_record
                                            has_diff = 'diff' in sample_record
                                            print(f"📊 Prediction history: {len(history)} records, end_price: {has_end_price}, diff: {has_diff}")
                
                # Check if we have both requirements
                if initial_payload_received and ping_response_received:
                    ws.close()
                    return self.log_test("WebSocket Detailed", True, "Initial payload✓, Ping response✓")
                
                time.sleep(0.5)
            
            ws.close()
            
            if not self.ws_connected:
                return self.log_test("WebSocket Detailed", False, "Failed to connect")
            elif not initial_payload_received:
                return self.log_test("WebSocket Detailed", False, "No initial payload with required structure")
            elif not ping_response_received:
                return self.log_test("WebSocket Detailed", False, "No pong response received")
            else:
                return self.log_test("WebSocket Detailed", False, "Timeout")
                
        except Exception as e:
            return self.log_test("WebSocket Detailed", False, f"Error: {str(e)}")

    def test_no_5xx_errors(self):
        """Test all endpoints for 5xx errors"""
        endpoints = [
            '/api/health',
            '/api/status', 
            '/api/patterns',
            '/api/side-bet',
            '/api/prediction-history',
            '/api/history',
            '/api/metrics',
            '/api/status-checks'
        ]
        
        errors_found = []
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if 500 <= response.status_code < 600:
                    errors_found.append(f"{endpoint}: {response.status_code}")
            except Exception as e:
                errors_found.append(f"{endpoint}: Exception - {str(e)}")
        
        if errors_found:
            return self.log_test("No 5xx Errors", False, f"Found errors: {errors_found}")
        else:
            return self.log_test("No 5xx Errors", True, f"All {len(endpoints)} endpoints returned < 500")

    def run_regression_tests(self):
        """Run regression tests as per review request"""
        print("🔍 Starting Detailed Regression Tests - ConnectionManager Integration")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 70)
        
        print("1) Verifying /api/health returns healthy and version 2.0.0...")
        self.test_health_detailed()
        
        print("\n2) Verifying /api/status includes system, connections, statistics, ml, side_bet_performance...")
        self.test_status_detailed()
        
        print("\n3) Testing WebSocket /api/ws connects and initial payload structure...")
        self.test_websocket_detailed()
        
        print("\n4) Checking for 5xx errors across all endpoints...")
        self.test_no_5xx_errors()
        
        # Summary
        print("=" * 70)
        print(f"📊 Regression Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All regression tests passed! ConnectionManager integration successful.")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} regression tests failed")
            return 1

def main():
    """Main test runner"""
    tester = DetailedRegressionTester()
    return tester.run_regression_tests()

if __name__ == "__main__":
    sys.exit(main())