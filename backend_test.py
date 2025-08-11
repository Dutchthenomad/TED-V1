#!/usr/bin/env python3
"""
Backend API Testing for Rugs Pattern Tracker
Tests all endpoints and WebSocket functionality
"""

import requests
import websocket
import json
import sys
import time
import threading
from datetime import datetime

class RugsPatternAPITester:
    def __init__(self, base_url="https://b1c1de50-2b1c-474e-957d-d21bed1c5e3e.preview.emergentagent.com"):
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

    def test_health_endpoint(self):
        """Test /api/health endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['status', 'rugs_connected', 'timestamp', 'version']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Health Endpoint", False, f"Missing keys: {missing_keys}")
                
                details = f"Status: {data.get('status')}, Rugs Connected: {data.get('rugs_connected')}"
                return self.log_test("Health Endpoint", True, details)
            else:
                return self.log_test("Health Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Health Endpoint", False, f"Error: {str(e)}")

    def test_patterns_endpoint(self):
        """Test /api/patterns endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'patterns' in data:
                    patterns = data['patterns']
                    pattern_keys = ['pattern1', 'pattern2', 'pattern3']
                    found_patterns = [key for key in pattern_keys if key in patterns]
                    details = f"Found patterns: {found_patterns}"
                    return self.log_test("Patterns Endpoint", len(found_patterns) > 0, details)
                else:
                    return self.log_test("Patterns Endpoint", False, "No 'patterns' key in response")
            else:
                return self.log_test("Patterns Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Patterns Endpoint", False, f"Error: {str(e)}")

    def test_status_endpoint(self):
        """Test /api/status endpoint"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_sections = ['system', 'connections', 'statistics']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    return self.log_test("Status Endpoint", False, f"Missing sections: {missing_sections}")
                
                details = f"System status: {data.get('system', {}).get('status')}"
                return self.log_test("Status Endpoint", True, details)
            else:
                return self.log_test("Status Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Status Endpoint", False, f"Error: {str(e)}")

    def on_ws_message(self, ws, message):
        """WebSocket message handler"""
        try:
            data = json.loads(message)
            self.ws_messages.append(data)
            print(f"📨 WebSocket received: {data.get('type', 'unknown')} message")
        except json.JSONDecodeError:
            self.ws_messages.append(message)
            print(f"📨 WebSocket received raw: {message}")

    def on_ws_error(self, ws, error):
        """WebSocket error handler"""
        self.ws_error = str(error)
        print(f"❌ WebSocket error: {error}")

    def on_ws_close(self, ws, close_status_code, close_msg):
        """WebSocket close handler"""
        print(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")

    def on_ws_open(self, ws):
        """WebSocket open handler"""
        self.ws_connected = True
        print("🔗 WebSocket connected")
        
        # Send ping after connection
        def send_ping():
            time.sleep(1)
            ws.send('ping')
            print("📤 Sent ping")
        
        threading.Thread(target=send_ping).start()

    def test_websocket_connection(self):
        """Test WebSocket connection and ping/pong"""
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
            timeout = 30
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.ws_error:
                    return self.log_test("WebSocket Connection", False, f"Connection error: {self.ws_error}")
                
                if self.ws_connected and self.ws_messages:
                    # Check for pong or keepalive response
                    for msg in self.ws_messages:
                        if isinstance(msg, dict):
                            if msg.get('type') in ['pong', 'keepalive']:
                                ws.close()
                                return self.log_test("WebSocket Connection", True, f"Received {msg.get('type')} response")
                
                time.sleep(0.5)
            
            ws.close()
            
            if not self.ws_connected:
                return self.log_test("WebSocket Connection", False, "Failed to connect within timeout")
            elif not self.ws_messages:
                return self.log_test("WebSocket Connection", False, "No messages received within timeout")
            else:
                return self.log_test("WebSocket Connection", False, "No ping response received within timeout")
                
        except Exception as e:
            return self.log_test("WebSocket Connection", False, f"Error: {str(e)}")

    def test_additional_endpoints(self):
        """Test additional endpoints"""
        endpoints = [
            ('/api/history', 'History'),
            ('/api/metrics', 'Metrics'),
            ('/api/', 'Root API')
        ]
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                success = response.status_code == 200
                details = f"Status: {response.status_code}"
                if success:
                    try:
                        data = response.json()
                        details += f", Keys: {list(data.keys())[:3]}"
                    except:
                        details += ", Non-JSON response"
                self.log_test(f"{name} Endpoint", success, details)
            except Exception as e:
                self.log_test(f"{name} Endpoint", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting Backend API Tests")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 60)
        
        # Core endpoint tests
        self.test_health_endpoint()
        self.test_patterns_endpoint()
        self.test_status_endpoint()
        
        # WebSocket test
        self.test_websocket_connection()
        
        # Additional endpoints
        self.test_additional_endpoints()
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    """Main test runner"""
    tester = RugsPatternAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())