import asyncio
import json
import logging
from datetime import datetime
from typing import Set, Dict, Optional, Any
from fastapi import WebSocket
from collections import deque
import time

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Thread-safe WebSocket connection manager with basic monitoring"""
    
    def __init__(self, max_connections: int = 100, message_queue_size: int = 1000):
        self._connections: Set[WebSocket] = set()
        self._connection_info: Dict[WebSocket, Dict] = {}
        self._lock = asyncio.Lock()
        self.max_connections = max_connections
        self.message_queue = deque(maxlen=message_queue_size)
        self.metrics = {
            'total_connections': 0,
            'messages_sent': 0,
            'messages_failed': 0,
            'current_connections': 0
        }
        self._broadcast_semaphore = asyncio.Semaphore(50)
    
    async def connect(self, websocket: WebSocket, client_info: Optional[Dict[str, Any]] = None) -> bool:
        """Accept a new WebSocket connection with limits"""
        async with self._lock:
            if len(self._connections) >= self.max_connections:
                logger.warning(f"Connection rejected: max connections ({self.max_connections}) reached")
                return False
            try:
                await websocket.accept()
                self._connections.add(websocket)
                self._connection_info[websocket] = {
                    'connected_at': datetime.now(),
                    'client_ip': websocket.client.host if websocket.client else 'unknown',
                    'last_heartbeat': time.time(),
                    **(client_info or {})
                }
                self.metrics['total_connections'] += 1
                self.metrics['current_connections'] = len(self._connections)
                logger.info(f"Client connected from {self._connection_info[websocket]['client_ip']}")
                return True
            except Exception as e:
                logger.error(f"Failed to accept connection: {e}")
                return False
    
    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self._connections:
                info = self._connection_info.get(websocket, {})
                self._connections.discard(websocket)
                self._connection_info.pop(websocket, None)
                self.metrics['current_connections'] = len(self._connections)
                logger.info(f"Client disconnected from {info.get('client_ip', 'unknown')}")
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> bool:
        try:
            await websocket.send_text(json.dumps(message, default=str))
            self.metrics['messages_sent'] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")
            self.metrics['messages_failed'] += 1
            await self.disconnect(websocket)
            return False
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[Set[WebSocket]] = None):
        exclude = exclude or set()
        message_str = json.dumps(message, default=str)
        
        # enqueue for replay
        self.message_queue.append({'timestamp': datetime.now(), 'message': message})
        
        async with self._lock:
            connections = list(self._connections - exclude)
        
        tasks = [self._send_with_semaphore(ws, message_str) for ws in connections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        failed = [ws for ws, res in zip(connections, results) if isinstance(res, Exception) or res is False]
        for ws in failed:
            await self.disconnect(ws)
    
    async def _send_with_semaphore(self, websocket: WebSocket, message: str) -> bool:
        async with self._broadcast_semaphore:
            try:
                await websocket.send_text(message)
                self.metrics['messages_sent'] += 1
                return True
            except Exception as e:
                logger.debug(f"Failed to send to client: {e}")
                self.metrics['messages_failed'] += 1
                return False
    
    async def heartbeat_check(self):
        while True:
            try:
                now = time.time()
                stale = []
                async with self._lock:
                    for ws, info in list(self._connection_info.items()):
                        if now - info.get('last_heartbeat', now) > 60:
                            stale.append(ws)
                for ws in stale:
                    logger.info("Removing stale connection")
                    await self.disconnect(ws)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(30)
    
    async def update_heartbeat(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self._connection_info:
                self._connection_info[websocket]['last_heartbeat'] = time.time()
    
    def get_metrics(self) -> Dict[str, Any]:
        return {**self.metrics, 'message_queue_size': len(self.message_queue), 'max_connections': self.max_connections}