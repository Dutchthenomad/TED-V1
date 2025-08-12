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
    def __init__(self, base_url="https://4c0451c0-fea0-470b-9160-6db670847956.preview.emergentagent.com"):
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
        """Test GET /api/health - should return status healthy and version 2.0.0"""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['status', 'rugs_connected', 'timestamp', 'version']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Health Endpoint", False, f"Missing keys: {missing_keys}")
                
                # Check specific values as per review request
                if data.get('status') != 'healthy':
                    return self.log_test("Health Endpoint", False, f"Status is '{data.get('status')}', expected 'healthy'")
                
                if data.get('version') != '2.0.0':
                    return self.log_test("Health Endpoint", False, f"Version is '{data.get('version')}', expected '2.0.0'")
                
                details = f"Status: {data.get('status')}, Version: {data.get('version')}, Rugs Connected: {data.get('rugs_connected')}"
                return self.log_test("Health Endpoint", True, details)
            else:
                return self.log_test("Health Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Health Endpoint", False, f"Error: {str(e)}")

    def test_status_endpoint(self):
        """Test GET /api/status - should return keys: system, connections, statistics, ml, side_bet_performance"""
        try:
            response = requests.get(f"{self.base_url}/api/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_sections = ['system', 'connections', 'statistics', 'ml', 'side_bet_performance']
                missing_sections = [section for section in required_sections if section not in data]
                
                if missing_sections:
                    return self.log_test("Status Endpoint", False, f"Missing sections: {missing_sections}")
                
                # Verify it's not the status-checks list anymore
                if isinstance(data, list):
                    return self.log_test("Status Endpoint", False, "Returns array instead of system status object")
                
                details = f"System status: {data.get('system', {}).get('status')}, ML enabled: {data.get('ml', {}).get('ml_enabled')}"
                return self.log_test("Status Endpoint", True, details)
            else:
                return self.log_test("Status Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Status Endpoint", False, f"Error: {str(e)}")

    def test_patterns_endpoint(self):
        """Test GET /api/patterns - should return patterns, prediction, side_bet_recommendation, ml_status"""
        try:
            response = requests.get(f"{self.base_url}/api/patterns", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['patterns', 'prediction', 'side_bet_recommendation', 'ml_status']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Patterns Endpoint", False, f"Missing keys: {missing_keys}")
                
                # side_bet_recommendation may be null depending on tick
                side_bet_status = "present" if data.get('side_bet_recommendation') else "null"
                details = f"Patterns: {type(data.get('patterns'))}, Prediction: {type(data.get('prediction'))}, Side bet: {side_bet_status}"
                return self.log_test("Patterns Endpoint", True, details)
            else:
                return self.log_test("Patterns Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Patterns Endpoint", False, f"Error: {str(e)}")

    def test_side_bet_endpoint(self):
        """Test GET /api/side-bet - should return recommendation + performance + history"""
        try:
            response = requests.get(f"{self.base_url}/api/side-bet", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['recommendation', 'performance', 'history']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Side-Bet Endpoint", False, f"Missing keys: {missing_keys}")
                
                details = f"Recommendation: {type(data.get('recommendation'))}, Performance: {type(data.get('performance'))}, History count: {len(data.get('history', []))}"
                return self.log_test("Side-Bet Endpoint", True, details)
            else:
                return self.log_test("Side-Bet Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Side-Bet Endpoint", False, f"Error: {str(e)}")

    def test_prediction_history_endpoint(self):
        """Test GET /api/prediction-history - should return records + metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/prediction-history", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['records', 'metrics']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Prediction History Endpoint", False, f"Missing keys: {missing_keys}")
                
                details = f"Records count: {len(data.get('records', []))}, Metrics: {type(data.get('metrics'))}"
                return self.log_test("Prediction History Endpoint", True, details)
            else:
                return self.log_test("Prediction History Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Prediction History Endpoint", False, f"Error: {str(e)}")

    def test_history_endpoint(self):
        """Test GET /api/history - should return games array structure"""
        try:
            response = requests.get(f"{self.base_url}/api/history", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['games']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("History Endpoint", False, f"Missing keys: {missing_keys}")
                
                if not isinstance(data.get('games'), list):
                    return self.log_test("History Endpoint", False, f"Games is not an array: {type(data.get('games'))}")
                
                details = f"Games count: {len(data.get('games', []))}, Total games: {data.get('total_games', 0)}"
                return self.log_test("History Endpoint", True, details)
            else:
                return self.log_test("History Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("History Endpoint", False, f"Error: {str(e)}")

    def test_metrics_endpoint(self):
        """Test GET /api/metrics - should return pattern_statistics, side_bet_metrics, system_performance, constants"""
        try:
            response = requests.get(f"{self.base_url}/api/metrics", timeout=10)
            if response.status_code == 200:
                data = response.json()
                required_keys = ['pattern_statistics', 'side_bet_metrics', 'system_performance', 'constants']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    return self.log_test("Metrics Endpoint", False, f"Missing keys: {missing_keys}")
                
                details = f"Pattern stats: {type(data.get('pattern_statistics'))}, Constants: {type(data.get('constants'))}"
                return self.log_test("Metrics Endpoint", True, details)
            else:
                return self.log_test("Metrics Endpoint", False, f"Status code: {response.status_code}")
        except Exception as e:
            return self.log_test("Metrics Endpoint", False, f"Error: {str(e)}")
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
            msg_type = data.get('type', 'unknown')
            print(f"📨 WebSocket received: {msg_type} message")
            # Debug: show first few keys for unknown messages
            if msg_type == 'unknown' and isinstance(data, dict):
                keys = list(data.keys())[:3]
                print(f"   Keys: {keys}")
        except json.JSONDecodeError:
            self.ws_messages.append(message)
            print(f"📨 WebSocket received raw: {message[:100]}...")

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
        def send_commands():
            time.sleep(1)
            ws.send('ping')
            print("📤 Sent ping")
            time.sleep(1)
            ws.send('status')
            print("📤 Sent status")
            time.sleep(1)
            ws.send('side_bet')
            print("📤 Sent side_bet")
        
        threading.Thread(target=send_commands).start()

    def test_websocket_connection(self):
        """Test WebSocket: connect, receive initial payload with game_state/patterns/prediction/ml_status, test ping/status/side_bet commands"""
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
            status_response_received = False
            side_bet_response_received = False
            
            while time.time() - start_time < timeout:
                if self.ws_error:
                    ws.close()
                    return self.log_test("WebSocket Connection", False, f"Connection error: {self.ws_error}")
                
                if self.ws_connected and self.ws_messages:
                    # Check for initial JSON message with required keys
                    if not initial_json_received:
                        for msg in self.ws_messages:
                            if isinstance(msg, dict) and msg.get('type') != 'pong':
                                # Check for required keys in initial payload
                                required_keys = ['game_state', 'patterns', 'prediction', 'ml_status']
                                if any(key in msg for key in required_keys):
                                    initial_json_received = True
                                    print("📨 Received initial JSON state with required keys")
                                    break
                    
                    # Check for command responses
                    for msg in self.ws_messages:
                        if isinstance(msg, dict):
                            if msg.get('type') == 'pong':
                                ping_response_received = True
                                print("📨 Received pong response")
                            elif msg.get('type') == 'side_bet_recommendation':
                                side_bet_response_received = True
                                print("📨 Received side_bet_recommendation response")
                            elif 'system' in msg or 'connections' in msg:  # status response
                                status_response_received = True
                                print("📨 Received status response")
                
                # Check if we have all responses
                if ping_response_received and status_response_received and side_bet_response_received:
                    ws.close()
                    details = f"All commands responded: ping✓, status✓, side_bet✓"
                    if initial_json_received:
                        details += ", Initial JSON✓"
                    return self.log_test("WebSocket Connection", True, details)
                
                time.sleep(0.5)
            
            ws.close()
            
            if not self.ws_connected:
                return self.log_test("WebSocket Connection", False, "Failed to connect within timeout")
            elif not initial_json_received:
                return self.log_test("WebSocket Connection", False, "No initial JSON with required keys received")
            elif not ping_response_received:
                return self.log_test("WebSocket Connection", False, "No pong response received")
            elif not status_response_received:
                return self.log_test("WebSocket Connection", False, "No status response received")
            elif not side_bet_response_received:
                return self.log_test("WebSocket Connection", False, "No side_bet response received")
            else:
                return self.log_test("WebSocket Connection", False, "Timeout waiting for all responses")
                
        except Exception as e:
            return self.log_test("WebSocket Connection", False, f"Error: {str(e)}")

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
        
        print("\n3) Testing GET /api/patterns...")
        self.test_patterns_endpoint()
        
        print("\n4) Testing GET /api/side-bet...")
        self.test_side_bet_endpoint()
        
        print("\n5) Testing GET /api/prediction-history...")
        self.test_prediction_history_endpoint()
        
        print("\n6) Testing GET /api/history...")
        self.test_history_endpoint()
        
        print("\n7) Testing GET /api/metrics...")
        self.test_metrics_endpoint()
        
        print("\n8) Testing WebSocket /api/ws...")
        self.test_websocket_connection()
        
        # Legacy endpoints for completeness
        print("\n   Testing GET /api/status-checks...")
        self.test_status_checks_get()
        
        print("\n   Testing POST /api/status-checks...")
        self.test_status_checks_post()
        
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