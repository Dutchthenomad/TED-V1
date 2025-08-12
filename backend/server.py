from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime
import asyncio
import json
import socketio
from collections import deque

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection - use only env MONGO_URL
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Rugs Pattern Tracker",
    description="Treasury pattern detection and rug timing prediction system",
    version="1.0.0",
    docs_url="/api/docs"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router with /api prefix for sample endpoints
api_router = APIRouter(prefix="/api")

# Pydantic models for sample collection
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class StatusCheckCreate(BaseModel):
    client_name: str

@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.post("/status-checks", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_obj = StatusCheck(**input.dict())
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status-checks", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(100)
    return [
        StatusCheck(
            id=str(doc.get("id") or uuid.uuid4()),
            client_name=doc.get("client_name", "unknown"),
            timestamp=doc.get("timestamp", datetime.utcnow())
        )
        for doc in status_checks
    ]

app.include_router(api_router)

# Import base enhanced engine and ML layer
from enhanced_pattern_engine import EnhancedPatternEngine, GameRecord
from game_aware_ml_engine import GameAwareMLPatternEngine

# Global state: ML-integrated tracker
class MLIntegratedTracker:
    def __init__(self):
        self.enhanced_engine = EnhancedPatternEngine()
        self.ml_engine = GameAwareMLPatternEngine(self.enhanced_engine)
        self.current_game = None
        self.prediction_history = deque(maxlen=200)

    def process_game_update(self, data):
        game_id = data.get('gameId', 0)
        current_tick = data.get('tickCount', 0)
        current_price = data.get('price', 1.0)
        is_active = data.get('active', True)
        is_rugged = data.get('rugged', False)
        if not self.current_game or self.current_game['gameId'] != game_id:
            if self.current_game:
                completed_game = GameRecord(
                    game_id=self.current_game['gameId'],
                    start_time=self.current_game['startTime'],
                    end_time=datetime.now(),
                    final_tick=self.current_game.get('currentTick', 0),
                    end_price=self.current_game.get('currentPrice', 0.0),
                    peak_price=self.current_game.get('peak_price', 1.0)
                )
                # Record prediction vs actual before updating ML
                last_pred = getattr(self.ml_engine, '_last_prediction', None)
                try:
                    if last_pred:
                        predicted_tick = int(last_pred.get('predicted_tick') or last_pred.get('prediction') or 0)
                        actual_tick = int(completed_game.final_tick)
                        diff = abs(predicted_tick - actual_tick)
                        record = {
                            'game_id': completed_game.game_id,
                            'predicted_tick': predicted_tick,
                            'actual_tick': actual_tick,
                            'diff': diff,
                            'peak_price': completed_game.peak_price,
                            'end_price': completed_game.end_price,
                            'timestamp': datetime.now().isoformat()
                        }
                        self.prediction_history.append(record)
                except Exception as e:
                    logger.error(f"Failed to append prediction history: {e}")
                # Update ML engine with completed game
                self.ml_engine.complete_game_analysis(completed_game)
            # Start new game
            self.current_game = {
                'gameId': game_id,
                'startTime': datetime.now(),
                'peak_price': current_price
            }
            self.enhanced_engine.pattern_states['pattern3']['current_peak'] = current_price
            self.enhanced_engine.pattern_states['pattern3']['threshold_alerts'] = []
        # Update current game state
        self.current_game.update({
            'currentTick': current_tick,
            'currentPrice': current_price,
            'isActive': is_active,
            'isRugged': is_rugged
        })
        if current_price > self.current_game['peak_price']:
            self.current_game['peak_price'] = current_price
        # Update engines
        self.enhanced_engine.update_current_game(current_tick, current_price)
        self.ml_engine.update_current_game(current_tick, current_price)
        prediction = self.ml_engine.predict_rug_timing(current_tick, current_price, self.current_game['peak_price'])
        patterns = self.enhanced_engine.get_pattern_dashboard_data()
        return {
            'game_state': {
                'gameId': game_id,
                'currentTick': current_tick,
                'currentPrice': current_price,
                'isActive': is_active,
                'isRugged': is_rugged
            },
            'patterns': patterns,
            'prediction': prediction,
            'ml_status': self.ml_engine.get_ml_status(),
            'prediction_history': list(self.prediction_history)[-20:],
            'timestamp': datetime.now().isoformat(),
            'enhanced': True
        }

pattern_tracker = MLIntegratedTracker()
connected_clients: List[WebSocket] = []
system_stats = {
    'start_time': datetime.now(),
    'total_connections': 0,
    'total_game_updates': 0,
    'total_errors': 0,
    'last_error': None
}

class RugsWebSocketClient:
    """Connects to Rugs.fun Socket.IO and forwards game updates"""
    def __init__(self):
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False)
        self.connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = int(os.getenv('MAX_RECONNECT_ATTEMPTS', '10'))
        self.reconnect_delay = int(os.getenv('RECONNECT_DELAY', '5'))
        self._setup_handlers()

    def _setup_handlers(self):
        @self.sio.event
        async def connect():
            logger.info("🔗 Connected to Rugs.fun backend")
            self.connected = True
            self.reconnect_attempts = 0

        @self.sio.event
        async def disconnect():
            logger.warning("💔 Disconnected from Rugs.fun backend")
            self.connected = False

        @self.sio.event
        async def connect_error(data):
            logger.error(f"❌ Connection error: {data}")
            system_stats['total_errors'] += 1
            system_stats['last_error'] = f"Connection error: {data}"

        @self.sio.on('gameStateUpdate')
        async def on_game_state_update(data):
            try:
                dashboard_data = pattern_tracker.process_game_update(data)
                system_stats['total_game_updates'] += 1
                if connected_clients:
                    disconnected = []
                    message = json.dumps(dashboard_data)
                    for ws in connected_clients:
                        try:
                            await ws.send_text(message)
                        except Exception as e:
                            logger.warning(f"Failed to send to client: {e}")
                            disconnected.append(ws)
                    for ws in disconnected:
                        if ws in connected_clients:
                            connected_clients.remove(ws)
                if data.get('rugged'):
                    logger.info(f"🚨 GAME RUGGED: #{data.get('gameId')} at tick {data.get('tickCount')}")
            except Exception as e:
                logger.error(f"❌ Error processing game update: {e}")
                system_stats['total_errors'] += 1
                system_stats['last_error'] = f"Game update error: {str(e)}"

    async def connect_to_rugs(self):
        rugs_url = os.getenv('RUGS_BACKEND_URL', 'https://backend.rugs.fun?frontend-version=1.0')
        try:
            await self.sio.connect(rugs_url, transports=['websocket', 'polling'], wait_timeout=10)
            return True
        except Exception as e:
            self.reconnect_attempts += 1
            logger.error(f"❌ Failed to connect (attempt {self.reconnect_attempts}): {e}")
            system_stats['total_errors'] += 1
            system_stats['last_error'] = f"Connection failed: {str(e)}"
            return False

    async def disconnect(self):
        if self.connected:
            await self.sio.disconnect()
            self.connected = False

rugs_client = RugsWebSocketClient()

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting Rugs Pattern Tracker v1.0.0")
    async def connection_manager():
        while True:
            if not rugs_client.connected and rugs_client.reconnect_attempts < rugs_client.max_reconnect_attempts:
                logger.info(f"🔄 Attempting to connect to Rugs.fun (attempt {rugs_client.reconnect_attempts + 1})")
                success = await rugs_client.connect_to_rugs()
                if not success:
                    delay = min(rugs_client.reconnect_delay * (2 ** rugs_client.reconnect_attempts), 60)
                    logger.info(f"⏳ Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.info("✅ Successfully connected to Rugs.fun")
            elif rugs_client.reconnect_attempts >= rugs_client.max_reconnect_attempts:
                logger.error("💀 Max reconnection attempts reached. Waiting...")
                await asyncio.sleep(60)
                rugs_client.reconnect_attempts = 0
            else:
                await asyncio.sleep(rugs_client.reconnect_delay)
    asyncio.create_task(connection_manager())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down Rugs Pattern Tracker")
    await rugs_client.disconnect()
    for ws in connected_clients:
        try:
            await ws.close()
        except Exception:
            pass

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    system_stats['total_connections'] += 1
    client_ip = websocket.client.host if websocket.client else "unknown"
    logger.info(f"📱 Client connected from {client_ip}. Total: {len(connected_clients)}")
    try:
        if pattern_tracker.current_game:
            initial_state = {
                'game_state': pattern_tracker.current_game,
                'patterns': pattern_tracker.enhanced_engine.get_pattern_dashboard_data(),
                'prediction': pattern_tracker.ml_engine.predict_rug_timing(
                    pattern_tracker.current_game.get('currentTick', 0),
                    pattern_tracker.current_game.get('currentPrice', 1.0),
                    pattern_tracker.current_game.get('peak_price', 1.0)
                ),
                'ml_status': pattern_tracker.ml_engine.get_ml_status(),
                'prediction_history': list(pattern_tracker.prediction_history)[-20:],
                'system_status': {
                    'rugs_connected': rugs_client.connected,
                    'uptime_seconds': int((datetime.now() - system_stats['start_time']).total_seconds()),
                    'total_games': len(pattern_tracker.enhanced_engine.game_history)
                }
            }
            def _default(o):
                if isinstance(o, datetime):
                    return o.isoformat()
                return str(o)
            await websocket.send_text(json.dumps(initial_state, default=_default))
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                if msg == 'ping':
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                elif msg == 'status':
                    status = await get_system_status()
                    await websocket.send_text(json.dumps(status))
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "keepalive"}))
    except WebSocketDisconnect:
        logger.info(f"📱 Client disconnected from {client_ip}. Total: {len(connected_clients) - 1}")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {client_ip}: {e}")
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "rugs_connected": rugs_client.connected,
        "version": "1.0.0",
    }

@app.get("/api/status")
async def get_system_status():
    uptime = datetime.now() - system_stats['start_time']
    return {
        "system": {
            "status": "running",
            "version": "1.0.0",
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "uptime_seconds": int(uptime.total_seconds()),
            "start_time": system_stats['start_time'].isoformat(),
        },
        "connections": {
            "rugs_backend": rugs_client.connected,
            "frontend_clients": len(connected_clients),
            "total_connections": system_stats['total_connections'],
            "reconnect_attempts": rugs_client.reconnect_attempts,
        },
        "statistics": {
            "total_game_updates": system_stats['total_game_updates'],
            "total_errors": system_stats['total_errors'],
            "games_analyzed": len(pattern_tracker.enhanced_engine.game_history),
            "pattern_accuracy": {
                "pattern1": pattern_tracker.enhanced_engine.pattern_stats['pattern1'].accuracy,
                "pattern2": pattern_tracker.enhanced_engine.pattern_stats['pattern2'].accuracy,
                "pattern3": pattern_tracker.enhanced_engine.pattern_stats['pattern3'].accuracy,
            },
        },
        "ml": pattern_tracker.ml_engine.get_ml_status(),
        "last_error": system_stats['last_error'],
        "current_game": pattern_tracker.current_game,
    }

@app.get("/api/patterns")
async def get_current_patterns():
    try:
        patterns = pattern_tracker.enhanced_engine.get_pattern_dashboard_data()
        prediction = None
        if pattern_tracker.current_game:
            prediction = pattern_tracker.ml_engine.predict_rug_timing(
                pattern_tracker.current_game.get('currentTick', 0),
                pattern_tracker.current_game.get('currentPrice', 1.0),
                pattern_tracker.current_game.get('peak_price', 1.0)
            )
        return {
            "patterns": patterns,
            "prediction": prediction,
            "ml_status": pattern_tracker.ml_engine.get_ml_status(),
            "prediction_history": list(pattern_tracker.prediction_history)[-20:],
            "current_game": pattern_tracker.current_game,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_game_history(limit: int = 100):
    try:
        recent = pattern_tracker.enhanced_engine.game_history[-limit:]
        return {
            "games": [
                {
                    "game_id": g.game_id,
                    "final_tick": g.final_tick,
                    "end_price": g.end_price,
                    "peak_price": g.peak_price,
                    "is_ultra_short": g.is_ultra_short,
                    "is_max_payout": g.is_max_payout,
                    "is_moonshot": g.is_moonshot,
                    "start_time": g.start_time.isoformat() if g.start_time else None,
                    "end_time": g.end_time.isoformat() if g.end_time else None,
                }
                for g in recent
            ],
            "total_games": len(pattern_tracker.enhanced_engine.game_history),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prediction-history")
async def get_prediction_history(limit: int = 50):
    try:
        records = list(pattern_tracker.prediction_history)[-limit:]
        return {"records": records, "total": len(pattern_tracker.prediction_history), "limit": limit}
    except Exception as e:
        logger.error(f"Error getting prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    stats = pattern_tracker.enhanced_engine.pattern_stats
    return {
        "pattern_statistics": {
            "pattern1": {
                "accuracy": stats['pattern1'].accuracy,
                "total_predictions": stats['pattern1'].successful_predictions + stats['pattern1'].failed_predictions,
                "successful_predictions": stats['pattern1'].successful_predictions,
                "confidence_interval": stats['pattern1'].confidence_interval,
                "last_updated": stats['pattern1'].last_updated.isoformat(),
            },
            "pattern2": {
                "accuracy": stats['pattern2'].accuracy,
                "total_predictions": stats['pattern2'].successful_predictions + stats['pattern2'].failed_predictions,
                "successful_predictions": stats['pattern2'].successful_predictions,
                "confidence_interval": stats['pattern2'].confidence_interval,
                "last_updated": stats['pattern2'].last_updated.isoformat(),
            },
            "pattern3": {
                "accuracy": stats['pattern3'].accuracy,
                "total_predictions": stats['pattern3'].successful_predictions + stats['pattern3'].failed_predictions,
                "successful_predictions": stats['pattern3'].successful_predictions,
                "confidence_interval": stats['pattern3'].confidence_interval,
                "last_updated": stats['pattern3'].last_updated.isoformat(),
            },
        },
        "system_performance": {
            "uptime_seconds": int((datetime.now() - system_stats['start_time']).total_seconds()),
            "total_game_updates": system_stats['total_game_updates'],
            "error_rate": system_stats['total_errors'] / max(system_stats['total_game_updates'], 1),
            "connected_clients": len(connected_clients),
        },
    }

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()