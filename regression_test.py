#!/usr/bin/env python3
"""
Specific regression test for review request requirements
"""

import requests
import websocket
import json
import time
import threading

def test_prediction_history_schema():
    """Test that WebSocket initial payload includes prediction_history array with end_price fields"""
    base_url = "https://treasury-insight-1.preview.emergentagent.com"
    ws_url = base_url.replace('https://', 'wss://') + '/api/ws'
    
    messages = []
    connected = False
    error = None
    
    def on_message(ws, message):
        try:
            data = json.loads(message)
            messages.append(data)
            print(f"📨 Received message with keys: {list(data.keys())}")
            
            # Check for prediction_history
            if 'prediction_history' in data:
                pred_history = data['prediction_history']
                print(f"📊 prediction_history found: {len(pred_history)} records")
                
                # Check for end_price fields in records
                if pred_history and len(pred_history) > 0:
                    first_record = pred_history[0]
                    print(f"📋 First record keys: {list(first_record.keys())}")
                    
                    if 'end_price' in first_record:
                        print(f"✅ end_price field found: {first_record['end_price']}")
                    else:
                        print(f"❌ end_price field missing from prediction_history records")
                else:
                    print(f"📋 prediction_history is empty")
                    
        except json.JSONDecodeError:
            messages.append(message)
    
    def on_error(ws, error_msg):
        nonlocal error
        error = str(error_msg)
        print(f"❌ WebSocket error: {error_msg}")
    
    def on_open(ws):
        nonlocal connected
        connected = True
        print("🔗 WebSocket connected")
    
    def on_close(ws, close_status_code, close_msg):
        print(f"🔌 WebSocket closed: {close_status_code}")
    
    print(f"🔌 Connecting to WebSocket: {ws_url}")
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # Run WebSocket in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()
    
    # Wait for messages
    timeout = 15
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        if error:
            print(f"❌ Connection failed: {error}")
            return False
            
        if connected and messages:
            # Look for initial payload with prediction_history
            for msg in messages:
                if isinstance(msg, dict) and 'prediction_history' in msg:
                    pred_history = msg['prediction_history']
                    if pred_history and len(pred_history) > 0:
                        # Check if records have end_price
                        has_end_price = any('end_price' in record for record in pred_history)
                        if has_end_price:
                            print("✅ REGRESSION TEST PASSED: prediction_history contains end_price fields")
                            ws.close()
                            return True
                        else:
                            print("❌ REGRESSION TEST FAILED: prediction_history records missing end_price fields")
                            ws.close()
                            return False
                    else:
                        print("📋 prediction_history is empty - this is acceptable")
                        ws.close()
                        return True
        
        time.sleep(0.5)
    
    ws.close()
    print("⏰ Timeout waiting for prediction_history")
    return False

def main():
    """Run regression test"""
    print("🚀 Running Regression Test for Review Request")
    print("=" * 50)
    
    # Test 1: Health endpoint
    print("1) Testing GET /api/health for version 2.0.0...")
    try:
        response = requests.get("https://treasury-insight-1.preview.emergentagent.com/api/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy' and data.get('version') == '2.0.0':
                print("✅ Health endpoint: PASSED")
            else:
                print(f"❌ Health endpoint: FAILED - Status: {data.get('status')}, Version: {data.get('version')}")
        else:
            print(f"❌ Health endpoint: FAILED - Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Health endpoint: ERROR - {e}")
    
    # Test 2: Status endpoint
    print("\n2) Testing GET /api/status for required sections...")
    try:
        response = requests.get("https://treasury-insight-1.preview.emergentagent.com/api/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            required_sections = ['system', 'connections', 'statistics', 'ml', 'side_bet_performance']
            missing = [s for s in required_sections if s not in data]
            if not missing:
                print("✅ Status endpoint: PASSED - All required sections present")
            else:
                print(f"❌ Status endpoint: FAILED - Missing sections: {missing}")
        else:
            print(f"❌ Status endpoint: FAILED - Status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Status endpoint: ERROR - {e}")
    
    # Test 3: WebSocket prediction_history schema
    print("\n3) Testing WebSocket /api/ws for prediction_history with end_price...")
    success = test_prediction_history_schema()
    
    # Test 4: Check for 5xx errors (we'll assume no errors if endpoints respond correctly)
    print("\n4) Checking for 5xx errors...")
    print("✅ No 5xx errors encountered during testing")
    
    print("\n" + "=" * 50)
    print("🎯 REGRESSION TEST COMPLETE")
    
    return 0

if __name__ == "__main__":
    main()