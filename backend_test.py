#!/usr/bin/env python3
"""
Backend API Testing for Rugs Pattern Tracker
Tests all endpoints and WebSocket functionality as per review request
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
        """Test GET /api/health - should return 200 JSON with keys: status, rugs_connected, timestamp, version"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['status', 'rugs_connected', 'timestamp', 'version']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Health Endpoint", False, f"Missing keys: {missing_keys}")
                
                details = f"Status: {data.get('status')}, Rugs Connected: {data.get('rugs_connected')}, Version: {data.get('version')}"
                return self.log_test("Health Endpoint", True, details)
            else:
                return self.log_test("Health Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Health Endpoint", False, f"Error: {str(e)}")

    def test_status_endpoint(self):
        """Test GET /api/status - should return system status JSON with keys: system, connections, statistics"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_sections = ['system', 'connections', 'statistics']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    return self.log_test("Status Endpoint", False, f"Missing sections: {missing_sections}")
                
                # Verify it's not the status-checks list anymore
                if isinstance(data, list):
                    return self.log_test("Status Endpoint", False, "Returns array instead of system status object")
                
                details = f"System status: {data.get('system', {}).get('status')}, Frontend clients: {data.get('connections', {}).get('frontend_clients')}"
                return self.log_test("Status Endpoint", True, details)
            else:
                return self.log_test("Status Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Status Endpoint", False, f"Error: {str(e)}")

    def test_status_checks_get(self):
        """Test GET /api/status-checks - should return an array (can be empty)"""
        try:
            response = requests.get(f"{self.base_url}/api/status-checks", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    details = f"Array with {len(data)} items"
                    return self.log_test("Status-Checks GET", True, details)
                else:
                    return self.log_test("Status-Checks GET", False, f"Expected array, got {type(data)}")
            else:
                return self.log_test("Status-Checks GET", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Status-Checks GET", False, f"Error: {str(e)}")

    def test_status_checks_post(self):
        """Test POST /api/status-checks with {"client_name":"test"} - should return 200 with object including id and timestamp"""
        try:
            payload = {"client_name": "test"}
            response = requests.post(f"{self.base_url}/api/status-checks", json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['id', 'timestamp']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Status-Checks POST", False, f"Missing keys: {missing_keys}")
                
                details = f"ID: {data.get('id')[:8]}..., Client: {data.get('client_name')}"
                return self.log_test("Status-Checks POST", True, details)
            else:
                return self.log_test("Status-Checks POST", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Status-Checks POST", False, f"Error: {str(e)}")

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
        """Test WebSocket: connect to ws://localhost:8001/api/ws, await initial JSON, then send 'ping' to receive 'pong' or receive periodic keepalive within 30s"""
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
            initial_json_received = False
            ping_response_received = False
            
            while time.time() - start_time < timeout:
                if self.ws_error:
                    ws.close()
                    return self.log_test("WebSocket Connection", False, f"Connection error: {self.ws_error}")
                
                if self.ws_connected and self.ws_messages:
                    # Check for initial JSON message
                    if not initial_json_received:
                        for msg in self.ws_messages:
                            if isinstance(msg, dict) and msg.get('type') != 'pong':
                                initial_json_received = True
                                print("📨 Received initial JSON state")
                                break
                    
                    # Check for pong or keepalive response
                    for msg in self.ws_messages:
                        if isinstance(msg, dict):
                            if msg.get('type') in ['pong', 'keepalive']:
                                ping_response_received = True
                                ws.close()
                                details = f"Received {msg.get('type')} response"
                                if initial_json_received:
                                    details += ", Initial JSON received"
                                return self.log_test("WebSocket Connection", True, details)
                
                time.sleep(0.5)
            
            ws.close()
            
            if not self.ws_connected:
                return self.log_test("WebSocket Connection", False, "Failed to connect within timeout")
            elif not initial_json_received:
                return self.log_test("WebSocket Connection", False, "No initial JSON received within timeout")
            elif not ping_response_received:
                return self.log_test("WebSocket Connection", False, "No ping response or keepalive received within timeout")
            else:
                return self.log_test("WebSocket Connection", False, "Timeout waiting for response")
                
        except Exception as e:
            return self.log_test("WebSocket Connection", False, f"Error: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests as per review request"""
        print("🚀 Starting Backend API Tests - Review Request Verification")
        print(f"🎯 Target URL: {self.base_url}")
        print("=" * 60)
        
        # Test specific endpoints as requested
        print("1) Testing GET /api/health...")
        self.test_health_endpoint()
        
        print("\n2) Testing GET /api/status...")
        self.test_status_endpoint()
        
        print("\n3) Testing GET /api/status-checks...")
        self.test_status_checks_get()
        
        print("\n   Testing POST /api/status-checks...")
        self.test_status_checks_post()
        
        print("\n4) Testing WebSocket connection...")
        self.test_websocket_connection()
        
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