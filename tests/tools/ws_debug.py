#!/usr/bin/env python3
"""
Simple WebSocket test for debugging
"""

import websocket
import json
import time
import threading

def on_message(ws, message):
    print(f"📨 Received: {message}")
    try:
        data = json.loads(message)
        print(f"📨 Parsed JSON: {data}")
    except:
        print(f"📨 Raw message: {message}")

def on_error(ws, error):
    print(f"❌ Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"🔌 Closed: {close_status_code} - {close_msg}")

def on_open(ws):
    print("🔗 Connected!")
    
    def send_messages():
        time.sleep(1)
        print("📤 Sending ping...")
        ws.send('ping')
        
        time.sleep(2)
        print("📤 Sending status...")
        ws.send('status')
        
        time.sleep(5)
        print("📤 Closing connection...")
        ws.close()
    
    threading.Thread(target=send_messages).start()

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws_url = "wss://b1c1de50-2b1c-474e-957d-d21bed1c5e3e.preview.emergentagent.com/api/ws"
    print(f"🔌 Connecting to: {ws_url}")
    
    ws = websocket.WebSocketApp(
        ws_url,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever()