#!/usr/bin/env python3
"""
WebSocket System Status Test
Specifically tests that WS clients receive payload with system_status as requested
"""

import websocket
import json
import time
import threading

class WebSocketSystemStatusTester:
    def __init__(self, base_url="https://pattern-prophet-2.preview.emergentagent.com"):
        self.base_url = base_url
        self.ws_messages = []
        self.ws_connected = False
        self.ws_error = None
        self.system_status_received = False

    def on_ws_message(self, ws, message):
        """WebSocket message handler"""
        try:
            data = json.loads(message)
            self.ws_messages.append(data)
            
            # Check for system_status in the payload
            if 'system_status' in data:
                self.system_status_received = True
                print(f"✅ Received system_status payload:")
                system_status = data['system_status']
                print(f"   - rugs_connected: {system_status.get('rugs_connected')}")
                print(f"   - uptime_seconds: {system_status.get('uptime_seconds')}")
                print(f"   - total_games: {system_status.get('total_games')}")
                print(f"   - version: {system_status.get('version')}")
            else:
                # Check what keys are present
                keys = list(data.keys()) if isinstance(data, dict) else []
                print(f"📨 Received message with keys: {keys[:5]}...")
                
        except json.JSONDecodeError:
            print(f"📨 Received raw message: {message[:100]}...")

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
        print("🔗 WebSocket connected - waiting for initial payload...")

    def test_system_status_payload(self):
        """Test that WebSocket receives payload with system_status"""
        try:
            ws_url = self.base_url.replace('https://', 'wss://').replace('http://', 'ws://') + '/api/ws'
            print(f"🔌 Connecting to WebSocket: {ws_url}")
            print("🎯 Looking for system_status in initial payload...")
            
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
            
            # Wait for connection and system_status
            timeout = 15
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if self.ws_error:
                    ws.close()
                    print(f"❌ Connection error: {self.ws_error}")
                    return False
                
                if self.system_status_received:
                    ws.close()
                    print("✅ SUCCESS: system_status payload received!")
                    return True
                
                time.sleep(0.5)
            
            ws.close()
            
            if not self.ws_connected:
                print("❌ FAILED: Could not connect to WebSocket")
                return False
            elif not self.system_status_received:
                print("❌ FAILED: No system_status found in initial payload")
                print(f"   Received {len(self.ws_messages)} messages total")
                if self.ws_messages:
                    print("   First message keys:", list(self.ws_messages[0].keys()) if isinstance(self.ws_messages[0], dict) else "Not a dict")
                return False
                
        except Exception as e:
            print(f"❌ FAILED: Error during test: {str(e)}")
            return False

def main():
    """Main test runner"""
    print("🚀 Testing WebSocket system_status payload...")
    print("=" * 50)
    
    tester = WebSocketSystemStatusTester()
    success = tester.test_system_status_payload()
    
    print("=" * 50)
    if success:
        print("🎉 TEST PASSED: WebSocket clients receive system_status payload")
        return 0
    else:
        print("⚠️ TEST FAILED: system_status payload not received")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())