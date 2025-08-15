from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import asyncio
import json
import socketio
from collections import deque
from tick_features import TickFeatureEngine

# Load env
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import persistence integration (safe - will be no-op if disabled)
try:
    from persistence_integration import setup_persistence, PersistenceIntegration
    persistence_available = True
except ImportError:
    persistence_available = False
    logger = logging.getLogger(__name__)
    logger.info("Persistence module not available - running in-memory only mode")

# MongoDB connection - with safe fallback
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)

# Use DB_NAME if provided, otherwise fallback to 'rugs_tracker' or extract from URL
if 'DB_NAME' in os.environ:
    db_name = os.environ['DB_NAME']
else:
    # Try to extract DB name from URL, otherwise use default
    if '/' in mongo_url and mongo_url.rstrip('/').split('/')[-1]:
        # MongoDB URLs can have format: mongodb://.../<database_name>
        db_name = mongo_url.rstrip('/').split('/')[-1].split('?')[0]
        if not db_name or db_name == 'test':
            db_name = 'rugs_tracker'
    else:
        db_name = 'rugs_tracker'
    logging.getLogger(__name__).info(f"No DB_NAME env var found, using database: {db_name}")

db = client[db_name]

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
    description="Treasury pattern detection and side bet arbitrage system",
    version="2.0.0",  # Updated version for revised system
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

# API Router
api_router = APIRouter(prefix="/api")

# Pydantic models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class StatusCheckCreate(BaseModel):
    client_name: str

class SideBetRecommendation(BaseModel):
    """Model for side bet recommendations"""
    action: str  # PLACE_SIDE_BET or WAIT
    ultra_short_probability: float
    expected_value: float
    confidence: float
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@api_router.get("/")
async def root():
    return {"message": "Rugs Pattern Tracker v2.0 - Clean Architecture"}

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

# Import revised engines
from enhanced_pattern_engine import EnhancedPatternEngine, GameRecord
from game_aware_ml_engine import GameAwareMLPatternEngine

# Global constants from validated knowledge base
TICK_DURATION_MS = 250  # NOT 271.5
MEDIAN_DURATION = 205
ULTRA_SHORT_THRESHOLD = 10
MAX_PAYOUT_THRESHOLD = 0.019
SIDEBET_WINDOW_TICKS = int(os.getenv("SIDEBET_WINDOW_TICKS", "40"))
SIDEBET_COOLDOWN_TICKS = int(os.getenv("SIDEBET_COOLDOWN_TICKS", "4"))
SIDEBET_PWIN_THRESHOLD = float(os.getenv("SIDEBET_PWIN_THRESHOLD", "0.20"))

# Enhanced tracker with side bet integration
class IntegratedPatternTracker:
    """Main tracker integrating all pattern engines and side bet logic"""
    
    def __init__(self):
        self.enhanced_engine = EnhancedPatternEngine()
        self.ml_engine = GameAwareMLPatternEngine(self.enhanced_engine)
        self.current_game = None
        self.prediction_history = deque(maxlen=200)
        self.side_bet_history = deque(maxlen=200)
        self.side_bet_performance = {
            'total_recommendations': 0,
            'positive_ev_bets': 0,
            'bets_won': 0,
            'bets_lost': 0,
            'total_ev': 0.0
        }
        # gating state
        self.last_side_bet_tick = None
        self.last_side_bet_active_until = None
        
        # Tick feature engine (if enabled)
        self.stream_features_enabled = os.getenv("STREAM_FEATURES_ENABLED", "false").lower() == "true"
        self.stream_influence_enabled = os.getenv("STREAM_INFLUENCE_ENABLED", "false").lower() == "true"
        if self.stream_features_enabled:
            self.tick_feature_engine = TickFeatureEngine()
            self.tick_ring = deque(maxlen=int(os.getenv("STREAM_RING_SIZE", "1200")))
            self.stream_sample_every = int(os.getenv("STREAM_SAMPLE_EVERY_TICKS", "1"))
            self.stream_max_cpu_ms = int(os.getenv("STREAM_MAX_CPU_MS", "3"))
            logger.info("Tick feature engine enabled")
        else:
            self.tick_feature_engine = None
            self.tick_ring = None

    def process_game_update(self, data):
        """Process incoming game update from Rugs.fun"""
        game_id = data.get('gameId', 0)
        current_tick = data.get('tickCount', 0)
        current_price = data.get('price', 1.0)
        is_active = data.get('active', True)
        is_rugged = data.get('rugged', False)
        
        # Handle game transitions
        if not self.current_game or self.current_game['gameId'] != game_id:
            # Complete previous game if exists
            if self.current_game:
                self._complete_game()
            
            # Start new game
            self.current_game = {
                'gameId': game_id,
                'startTime': datetime.now(),
                'peak_price': current_price,
                'startTick': 0,
                'side_bet_evaluated': False
            }
            
            # Persist game start if available
            if persistence and persistence.enabled:
                asyncio.create_task(persistence.on_game_start(
                    game_id=game_id,
                    start_tick=0,
                    initial_price=current_price
                ))
            
            # Reset pattern states for new game
            self.enhanced_engine.pattern_states['pattern3']['current_peak'] = current_price
            self.enhanced_engine.pattern_states['pattern3']['threshold_alerts'] = []
            self.enhanced_engine.pattern_states['pattern3']['active_threshold'] = None
        
        # Update current game state
        self.current_game.update({
            'currentTick': current_tick,
            'currentPrice': current_price,
            'isActive': is_active,
            'isRugged': is_rugged
        })
        
        # Track peak price
        if current_price > self.current_game['peak_price']:
            self.current_game['peak_price'] = current_price
        
        # Update pattern engines
        self.enhanced_engine.update_current_game(current_tick, current_price)
        self.ml_engine.update_current_game(current_tick, current_price)
        
        # Process tick features if enabled
        ml_tick = None
        if self.tick_feature_engine and self.stream_features_enabled:
            import time
            start_time = time.time()
            
            # Get EPR state
            epr_active = False
            try:
                epr_state = getattr(self.ml_engine, "_epr", {})
                epr_active = bool(epr_state.get("active", False))
            except Exception:
                pass
            
            # Update tick features
            ml_tick = self.tick_feature_engine.update(
                game_id, current_tick, current_price, 
                self.current_game['peak_price'], epr_active
            )
            
            # Sample and store in ring buffer
            if current_tick % self.stream_sample_every == 0:
                tick_dict = ml_tick.to_dict()
                self.tick_ring.append(tick_dict)
            
            # Apply influence if enabled
            if self.stream_influence_enabled and hasattr(self.ml_engine, 'register_stream_scale'):
                try:
                    self.ml_engine.register_stream_scale(ml_tick.hazard_scale)
                except Exception as e:
                    logger.debug(f"Failed to register stream scale: {e}")
            
            # Check CPU budget
            elapsed_ms = (time.time() - start_time) * 1000
            if elapsed_ms > self.stream_max_cpu_ms:
                logger.warning(f"Tick feature processing exceeded budget: {elapsed_ms:.1f}ms")
        
        # Get predictions
        prediction = self.ml_engine.predict_rug_timing(
            current_tick, current_price, self.current_game['peak_price']
        )
        
        # Capture EPR state at prediction time
        try:
            epr_state = getattr(self.ml_engine, "_epr", {})
            prediction["epr_active_at_prediction"] = bool(epr_state.get("active", False))
        except Exception:
            prediction["epr_active_at_prediction"] = False
            
        prediction = self._quantize_prediction_tolerance(prediction, current_tick)
        
        # Persist prediction if available
        if persistence and persistence.enabled and prediction:
            predicted_tick = prediction.get('predicted_tick', prediction.get('prediction', 0))
            asyncio.create_task(persistence.on_prediction_made(
                game_id=game_id,
                predicted_at_tick=current_tick,
                predicted_end_tick=int(predicted_tick),
                confidence=prediction.get('confidence', 0.5),
                uncertainty_bounds={
                    'lower': prediction.get('tolerance_lower', predicted_tick - 40),
                    'upper': prediction.get('tolerance_upper', predicted_tick + 40)
                },
                features={
                    'epr_active': prediction.get('epr_active_at_prediction', False),
                    'peak_price': self.current_game['peak_price'],
                    'current_price': current_price
                }
            ))
        
        # Hazard-based side bet recommendation with 40+4 gating
        side_bet = None
        can_recommend = True
        if self.last_side_bet_active_until is not None:
            can_recommend = current_tick > (self.last_side_bet_active_until + SIDEBET_COOLDOWN_TICKS)
        if can_recommend:
            side_bet = self.ml_engine.side_bet_signal(
                current_tick, current_price, self.current_game['peak_price']
            )
            if side_bet and side_bet.get('action') == 'PLACE_SIDE_BET':
                self._record_side_bet_recommendation(side_bet, game_id, current_tick)
                self.last_side_bet_tick = current_tick
                self.last_side_bet_active_until = current_tick + (SIDEBET_WINDOW_TICKS - 1)
        
        # Get pattern dashboard
        patterns = self.enhanced_engine.get_pattern_dashboard_data()
        
        # Build response
        return {
            'game_state': {
                'gameId': game_id,
                'currentTick': current_tick,
                'currentPrice': current_price,
                'peakPrice': self.current_game['peak_price'],
                'isActive': is_active,
                'isRugged': is_rugged
            },
            'patterns': patterns,
            'prediction': prediction,
            'side_bet_recommendation': side_bet,
            'ml_status': self.ml_engine.get_ml_status(),
            'prediction_history': list(self.prediction_history),  # Send full history
            'side_bet_performance': self.side_bet_performance,
            'timestamp': datetime.now().isoformat(),
            'enhanced': True,
            'version': '2.0.0'
        }
    
    def _complete_game(self):
        """Complete a game and update ML models"""
        if not self.current_game:
            return
            
        # Create game record
        completed_game = GameRecord(
            game_id=self.current_game['gameId'],
            start_time=self.current_game['startTime'],
            end_time=datetime.now(),
            final_tick=self.current_game.get('currentTick', 0),
            end_price=self.current_game.get('currentPrice', 0.0),
            peak_price=self.current_game.get('peak_price', 1.0)
        )
        
        # Record prediction accuracy
        self._record_prediction_accuracy(completed_game)
        
        # Update side bet performance if applicable
        self._update_side_bet_performance(completed_game)
        
        # Update ML engine
        self.ml_engine.complete_game_analysis(completed_game)
        
        # Persist game end if available
        if persistence and persistence.enabled:
            asyncio.create_task(persistence.on_game_end(
                game_id=completed_game.game_id,
                end_tick=completed_game.final_tick,
                final_price=completed_game.end_price,
                treasury_remainder=None  # Not available in current data
            ))
        
        # Log game completion
        logger.info(
            f"📊 Game #{completed_game.game_id} completed: "
            f"{completed_game.final_tick}t, "
            f"End: {completed_game.end_price:.3f}, "
            f"Peak: {completed_game.peak_price:.1f}x, "
            f"Ultra-short: {completed_game.is_ultra_short}, "
            f"Max payout: {completed_game.is_max_payout}"
        )
    
    def _record_prediction_accuracy(self, completed_game):
        """Record how accurate our prediction was"""
        last_pred = getattr(self.ml_engine, '_last_prediction', None)
        if last_pred:
            try:
                predicted_tick = int(last_pred.get('predicted_tick', 0))
                actual_tick = int(completed_game.final_tick)
                diff = abs(predicted_tick - actual_tick)
                
                # Get EPR state if available
                epr_active = False
                try:
                    epr_state = getattr(self.ml_engine, "_epr", {})
                    epr_active = bool(epr_state.get("active", False))
                except Exception:
                    pass
                    
                # Calculate directional metrics
                signed_error = predicted_tick - actual_tick  # negative = early, positive = late
                E40 = signed_error / 40.0  # window-normalized error
                
                # Get spread from last prediction for Ez calculation
                spread = 80  # default
                if last_pred and 'quantiles' in last_pred:
                    q10 = last_pred['quantiles'].get('q10', predicted_tick - 40)
                    q90 = last_pred['quantiles'].get('q90', predicted_tick + 40)
                    spread = q90 - q10
                Ez = signed_error / max(40, spread)  # spread-normalized error
                
                # Check if actual was within predicted band
                in_band = False
                if last_pred:
                    coverage_lower = last_pred.get('coverage_lower', predicted_tick - 50)
                    coverage_upper = last_pred.get('coverage_upper', predicted_tick + 50)
                    in_band = coverage_lower <= actual_tick <= coverage_upper
                
                record = {
                    'game_id': completed_game.game_id,
                    'predicted_tick': predicted_tick,
                    'actual_tick': actual_tick,
                    'diff': diff,
                    'signed_error': signed_error,
                    'E40': round(E40, 3),
                    'Ez': round(Ez, 3),
                    'spread': int(spread),
                    'in_band': in_band,
                    'within_tolerance': diff <= 50,
                    'peak_price': completed_game.peak_price,
                    'end_price': completed_game.end_price,
                    'is_ultra_short': completed_game.is_ultra_short,
                    'is_max_payout': completed_game.is_max_payout,
                    'epr_active_at_prediction': epr_active,
                    'timestamp': datetime.now().isoformat()
                }
                self.prediction_history.append(record)
                
                # Update ML engine with rolling median E40 for dynamic quantile adjustment
                if os.getenv("QUANTILE_ADJUSTMENT_ENABLED", "false").lower() == "true":
                    recent_records = list(self.prediction_history)[-50:]  # Last 50 games
                    e40_values = [r.get('E40', 0) for r in recent_records if 'E40' in r]
                    if e40_values:
                        median_e40 = sorted(e40_values)[len(e40_values)//2]
                        self.ml_engine._median_e40 = median_e40
            except Exception as e:
                logger.error(f"Failed to record prediction: {e}")
    
    def _quantize_prediction_tolerance(self, prediction: dict, current_tick: int) -> dict:
        """
        Make ±tolerance future-safe and aligned to 40-tick windows:
        - lower bound never before current_tick
        - total width (2*tol) is a multiple of 40 => tol multiple of 20
        """
        try:
            center = int(prediction.get("predicted_tick", prediction.get("prediction", 0)))
            tol = int(max(0, prediction.get("tolerance", 0)))
            # disallow "past coverage": ensure we don't extend below current tick
            back_limit = max(0, center - current_tick)
            # quantize tol down: tol is multiple of 20 and ≤ back_limit
            new_tol = (min(tol, back_limit) // 20) * 20
            lower = max(current_tick, center - new_tol)
            upper = center + new_tol
            width = max(0, upper - lower)
            windows = max(1, (width + (SIDEBET_WINDOW_TICKS - 1)) // SIDEBET_WINDOW_TICKS)
            prediction["tolerance"] = new_tol
            prediction["coverage_lower"] = lower
            prediction["coverage_upper"] = upper
            prediction["coverage_windows"] = windows
        except Exception as e:
            logger.error(f"Tolerance quantization error: {e}")
        return prediction

    def _record_side_bet_recommendation(self, side_bet, game_id, tick):
        """Record side bet recommendation"""
        if side_bet:
            record = {
                'game_id': game_id,
                'tick': tick,
                'action': side_bet['action'],
                'probability': side_bet.get('p_win_40', side_bet.get('ultra_short_probability', 0)),
                'p_win_40': side_bet.get('p_win_40'),
                'coverage_end_tick': tick + (SIDEBET_WINDOW_TICKS - 1),
                'expected_value': side_bet['expected_value'],
                'confidence': side_bet['confidence'],
                'timestamp': datetime.now().isoformat()
            }
            self.side_bet_history.append(record)
            
            # Persist side bet if available
            if persistence and persistence.enabled:
                asyncio.create_task(persistence.on_side_bet_placed(
                    game_id=game_id,
                    placed_at_tick=tick,
                    probability=record['probability'],
                    expected_value=side_bet['expected_value'],
                    confidence=side_bet['confidence'],
                    recommendation=side_bet['action']
                ))
            
            self.side_bet_performance['total_recommendations'] += 1
            if side_bet['expected_value'] > 0:
                self.side_bet_performance['positive_ev_bets'] += 1
                self.side_bet_performance['total_ev'] += side_bet['expected_value']
    
    def _update_side_bet_performance(self, completed_game):
        """Update side bet performance based on game outcome"""
        # Check if we made a side bet recommendation for this game
        for bet in list(self.side_bet_history)[-10:]:
            if bet['game_id'] == completed_game.game_id:
                placed_at = bet.get('tick', 0)
                # Side bet wins if game ended within placement + window ticks
                if completed_game.final_tick <= placed_at + SIDEBET_WINDOW_TICKS:
                    self.side_bet_performance['bets_won'] += 1
                    logger.info(f"✅ Side bet WON for game {completed_game.game_id} (ended at {completed_game.final_tick})")
                else:
                    self.side_bet_performance['bets_lost'] += 1
                    logger.info(f"❌ Side bet lost for game {completed_game.game_id} (ended at {completed_game.final_tick})")
                break

# Initialize tracker
pattern_tracker = IntegratedPatternTracker()

# Initialize persistence if available
persistence = None
if persistence_available:
    try:
        persistence = setup_persistence(app, db, pattern_tracker)
        logger.info(f"Persistence system initialized. Enabled: {persistence.enabled}")
    except Exception as e:
        logger.warning(f"Could not initialize persistence: {e}. Running in-memory only mode.")
        persistence = None

# Use enhanced connection manager
try:
    from core.connection_manager import ConnectionManager
    connection_manager = ConnectionManager(max_connections=int(os.getenv('MAX_WEBSOCKET_CONNECTIONS', '100')), message_queue_size=int(os.getenv('WS_MESSAGE_QUEUE_SIZE', '1000')))
except Exception:
    connection_manager = None

connected_clients: List[WebSocket] = []  # Legacy list retained for compatibility
system_stats = {
    'start_time': datetime.now(),
    'total_connections': 0,
    'total_game_updates': 0,
    'total_errors': 0,
    'last_error': None,
    'version': '2.0.0'
}

class RugsWebSocketClient:
    """Connects to Rugs.fun Socket.IO and forwards game updates"""
    def __init__(self):
        self.sio = socketio.AsyncClient(logger=False, engineio_logger=False, reconnection=True, reconnection_attempts=5)
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
                # Process update through pattern tracker
                dashboard_data = pattern_tracker.process_game_update(data)
                system_stats['total_game_updates'] += 1
                
                # Broadcast to connected clients
                if connection_manager and connection_manager.metrics['current_connections'] > 0:
                    logger.debug(f"Broadcasting game update to {connection_manager.metrics['current_connections']} clients - tick: {data.get('tickCount')}")
                    await connection_manager.broadcast(dashboard_data)
                elif connected_clients:
                    disconnected = []
                    message = json.dumps(dashboard_data)
                    logger.debug(f"Broadcasting to {len(connected_clients)} legacy clients")
                    for ws in connected_clients:
                        try:
                            await ws.send_text(message)
                        except Exception as e:
                            logger.warning(f"Failed to send to client: {e}")
                            disconnected.append(ws)
                    # Clean up disconnected clients
                    for ws in disconnected:
                        if ws in connected_clients:
                            connected_clients.remove(ws)
                else:
                    logger.debug("No clients connected to broadcast to")
                
                # Log game completion
                if data.get('rugged'):
                    logger.info(
                        f"🚨 GAME RUGGED: #{data.get('gameId')} "
                        f"at tick {data.get('tickCount')}, "
                        f"price: {data.get('price', 0):.3f}"
                    )
                    
            except Exception as e:
                logger.error(f"❌ Error processing game update: {e}")
                system_stats['total_errors'] += 1
                system_stats['last_error'] = f"Game update error: {str(e)}"

        @self.sio.event
        async def message(data):
            # Do nothing (listen-only)
            pass

    async def connect_to_rugs(self):
        """Connect to Rugs.fun backend"""
        rugs_url = os.getenv('RUGS_BACKEND_URL') or 'https://backend.rugs.fun?frontend-version=1.0'
        try:
            await self.sio.connect(
                rugs_url, 
                transports=['websocket', 'polling'], 
                wait_timeout=10
            )
            return True
        except Exception as e:
            self.reconnect_attempts += 1
            logger.error(f"❌ Failed to connect (attempt {self.reconnect_attempts}): {e}")
            system_stats['total_errors'] += 1
            system_stats['last_error'] = f"Connection failed: {str(e)}"
            return False

    async def disconnect(self):
        """Disconnect from Rugs.fun"""
        if self.connected:
            await self.sio.disconnect()
            self.connected = False

# Initialize Rugs client (can be disabled by env)
rugs_client = None
# Enable external Rugs.fun connection by default (listen-only). Set DISABLE_EXTERNAL_RUGS=true to turn off.
EXTERNAL_FEED_ENABLED = os.getenv('DISABLE_EXTERNAL_RUGS', 'false').lower() not in ['1','true','yes']
if EXTERNAL_FEED_ENABLED:
    rugs_client = RugsWebSocketClient()

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting Rugs Pattern Tracker v2.0.0 - Clean Architecture")
    
    # Connection manager task (only if external feed enabled)
    if rugs_client is not None:
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
    else:
        logger.info("🛑 External Rugs backend connection disabled (EXTERNAL_FEED_ENABLED=false)")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Shutting down Rugs Pattern Tracker")
    if rugs_client:
        await rugs_client.disconnect()
    
    # Close all websocket connections
    for ws in connected_clients:
        try:
            await ws.close()
        except Exception:
            pass
    
    # Close MongoDB connection
    client.close()

@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates (compat + ConnectionManager)"""
    client_ip = websocket.client.host if websocket.client else "unknown"

    # If ConnectionManager available, use it; else fallback to legacy list
    if connection_manager:
        accepted = await connection_manager.connect(websocket, {"client_ip": client_ip})
        if not accepted:
            await websocket.close(code=1008, reason="Max connections reached")
            return
        system_stats['total_connections'] += 1
        logger.info(f"📱 Client connected from {client_ip}. Total: {connection_manager.metrics['current_connections']}")
    else:
        await websocket.accept()
        connected_clients.append(websocket)
        system_stats['total_connections'] += 1
        logger.info(f"📱 Client connected from {client_ip}. Total: {len(connected_clients)}")
    
    try:
        # Send initial state if available
        if pattern_tracker.current_game:
            initial_state = {
                'game_state': pattern_tracker.current_game,
                'patterns': pattern_tracker.enhanced_engine.get_pattern_dashboard_data(),
                'prediction': pattern_tracker.ml_engine.predict_rug_timing(
                    pattern_tracker.current_game.get('currentTick', 0),
                    pattern_tracker.current_game.get('currentPrice', 1.0),
                    pattern_tracker.current_game.get('peak_price', 1.0)
                ),
                'side_bet_recommendation': pattern_tracker.enhanced_engine.get_side_bet_recommendation()
                    if pattern_tracker.current_game.get('currentTick', 0) <= 5 else None,
                'ml_status': pattern_tracker.ml_engine.get_ml_status(),
                'prediction_history': list(pattern_tracker.prediction_history),  # Send full history
                'side_bet_performance': pattern_tracker.side_bet_performance,
                'system_status': {
                    'rugs_connected': bool(rugs_client and rugs_client.connected),
                    'uptime_seconds': int((datetime.now() - system_stats['start_time']).total_seconds()),
                    'total_games': len(pattern_tracker.enhanced_engine.game_history),
                    'version': '2.0.0'
                }
            }
            
            def _default(o):
                if isinstance(o, datetime):
                    return o.isoformat()
                return str(o)
            
            if connection_manager:
                await connection_manager.send_personal(websocket, initial_state)
            else:
                await websocket.send_text(json.dumps(initial_state, default=_default))
        
        # Handle incoming messages
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                if msg == 'ping':
                    payload = {"type": "pong", "timestamp": datetime.now().isoformat()}
                    if connection_manager:
                        await connection_manager.update_heartbeat(websocket)
                        await connection_manager.send_personal(websocket, payload)
                    else:
                        await websocket.send_text(json.dumps(payload))
                elif msg == 'status':
                    status = await get_system_status()
                    if connection_manager:
                        await connection_manager.send_personal(websocket, status)
                    else:
                        await websocket.send_text(json.dumps(status))
                elif msg == 'side_bet':
                    cg = pattern_tracker.current_game or {}
                    side_bet = pattern_tracker.ml_engine.side_bet_signal(
                        cg.get('currentTick', 0),
                        cg.get('currentPrice', 1.0),
                        cg.get('peak_price', 1.0),
                    )
                    payload = {"type": "side_bet_recommendation", "data": side_bet, "timestamp": datetime.now().isoformat()}
                    if connection_manager:
                        await connection_manager.send_personal(websocket, payload)
                    else:
                        await websocket.send_text(json.dumps(payload))
            except asyncio.TimeoutError:
                keepalive = {"type": "keepalive"}
                if connection_manager:
                    await connection_manager.send_personal(websocket, keepalive)
                    await connection_manager.update_heartbeat(websocket)
                else:
                    await websocket.send_text(json.dumps(keepalive))
                
    except WebSocketDisconnect:
        logger.info(f"📱 Client disconnected from {client_ip}.")
    except Exception as e:
        logger.error(f"❌ WebSocket error for {client_ip}: {e}")
    finally:
        if connection_manager:
            await connection_manager.disconnect(websocket)
        else:
            if websocket in connected_clients:
                connected_clients.remove(websocket)

# API Endpoints

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "rugs_connected": bool(rugs_client and rugs_client.connected),
        "version": "2.0.0",
    }

@app.get("/api/status")
async def get_system_status():
    """Get comprehensive system status"""
    uptime = datetime.now() - system_stats['start_time']
    
    return {
        "system": {
            "status": "running",
            "version": "2.0.0",
            "environment": os.getenv('ENVIRONMENT', 'development'),
            "uptime_seconds": int(uptime.total_seconds()),
            "start_time": system_stats['start_time'].isoformat(),
        },
        "connections": {
            "rugs_backend": bool(rugs_client and rugs_client.connected),
            "frontend_clients": len(connected_clients),
            "total_connections": system_stats['total_connections'],
            "reconnect_attempts": (rugs_client.reconnect_attempts if rugs_client else 0),
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
        "side_bet_performance": pattern_tracker.side_bet_performance,
        "last_error": system_stats['last_error'],
        "current_game": pattern_tracker.current_game,
    }

@app.get("/api/patterns")
async def get_current_patterns():
    """Get current pattern states and predictions"""
    try:
        patterns = pattern_tracker.enhanced_engine.get_pattern_dashboard_data()
        prediction = None
        side_bet = None
        
        if pattern_tracker.current_game:
            tick = pattern_tracker.current_game.get('currentTick', 0)
            price = pattern_tracker.current_game.get('currentPrice', 1.0)
            peak = pattern_tracker.current_game.get('peak_price', 1.0)
            
            prediction = pattern_tracker.ml_engine.predict_rug_timing(tick, price, peak)
            
            # Only recommend side bet early in game
            if tick <= 5:
                side_bet = pattern_tracker.enhanced_engine.get_side_bet_recommendation()
        
        return {
            "patterns": patterns,
            "prediction": prediction,
            "side_bet_recommendation": side_bet,
            "ml_status": pattern_tracker.ml_engine.get_ml_status(),
            "prediction_history": list(pattern_tracker.prediction_history),  # Send full history
            "side_bet_performance": pattern_tracker.side_bet_performance,
            "current_game": pattern_tracker.current_game,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/side-bet")
async def get_side_bet_recommendation():
    """Get current side bet recommendation"""
    try:
        cg = pattern_tracker.current_game or {}
        side_bet = pattern_tracker.ml_engine.side_bet_signal(
            cg.get('currentTick', 0),
            cg.get('currentPrice', 1.0),
            cg.get('peak_price', 1.0),
        )
        
        return {
            "recommendation": side_bet,
            "performance": pattern_tracker.side_bet_performance,
            "history": list(pattern_tracker.side_bet_history)[-40:],
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting side bet recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_game_history(limit: int = 100):
    """Get game history"""
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
            "ultra_short_count": sum(1 for g in recent if g.is_ultra_short),
            "max_payout_count": sum(1 for g in recent if g.is_max_payout),
            "moonshot_count": sum(1 for g in recent if g.is_moonshot),
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_directional_metrics(records: list, window_size: int = 50) -> dict:
    """Calculate directional error metrics from prediction records"""
    if not records:
        return {
            "median_E40": 0.0,
            "mean_E40": 0.0,
            "median_signed_error": 0.0,
            "early_rate": 0.0,
            "late_rate": 0.0,
            "within_1_window": 0.0,
            "within_2_windows": 0.0,
            "within_3_windows": 0.0,
            "coverage_rate": 0.0,
            "early_skew": 0.0
        }
    
    # Get last N records for rolling calculations
    recent = records[-window_size:] if len(records) > window_size else records
    
    # Extract metrics
    E40_values = [r.get('E40', 0) for r in recent if 'E40' in r]
    signed_errors = [r.get('signed_error', 0) for r in recent if 'signed_error' in r]
    
    # Calculate statistics
    median_E40 = sorted(E40_values)[len(E40_values)//2] if E40_values else 0
    mean_E40 = sum(E40_values) / len(E40_values) if E40_values else 0
    median_signed = sorted(signed_errors)[len(signed_errors)//2] if signed_errors else 0
    
    # Direction rates
    early_count = sum(1 for e in signed_errors if e < 0)
    late_count = sum(1 for e in signed_errors if e > 0)
    total = len(signed_errors) if signed_errors else 1
    
    # Window accuracy
    within_1w = sum(1 for e in E40_values if abs(e) <= 1) / len(E40_values) if E40_values else 0
    within_2w = sum(1 for e in E40_values if abs(e) <= 2) / len(E40_values) if E40_values else 0
    within_3w = sum(1 for e in E40_values if abs(e) <= 3) / len(E40_values) if E40_values else 0
    
    # Coverage rate
    in_band_count = sum(1 for r in recent if r.get('in_band', False))
    coverage_rate = in_band_count / len(recent) if recent else 0
    
    return {
        "median_E40": round(median_E40, 3),
        "mean_E40": round(mean_E40, 3),
        "median_signed_error": round(median_signed, 1),
        "early_rate": round(early_count / total, 3),
        "late_rate": round(late_count / total, 3),
        "within_1_window": round(within_1w, 3),
        "within_2_windows": round(within_2w, 3),
        "within_3_windows": round(within_3w, 3),
        "coverage_rate": round(coverage_rate, 3),
        "early_skew": round((early_count - late_count) / total, 3)
    }

@app.get("/api/prediction-history")
async def get_prediction_history(limit: int = 200):
    """Get prediction history with accuracy metrics"""
    try:
        records = list(pattern_tracker.prediction_history)[-limit:]
        
        # Calculate accuracy metrics
        if records:
            within_tolerance = sum(1 for r in records if r.get('within_tolerance', False))
            accuracy = within_tolerance / len(records)
            avg_error = sum(r.get('diff', 0) for r in records) / len(records)
        else:
            accuracy = 0.0
            avg_error = 0.0
        
        # Calculate directional metrics
        directional_metrics = calculate_directional_metrics(records)
        
        return {
            "history": records,  # Changed from "records" to match frontend expectation
            "metrics": {
                "accuracy": accuracy,
                "average_error": avg_error,
                "within_tolerance_count": within_tolerance if records else 0,
                **directional_metrics  # Include all directional metrics
            },
            "total": len(pattern_tracker.prediction_history),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"Error getting prediction history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tick-history")
async def get_tick_history():
    """Get tick feature history (if enabled)"""
    try:
        if not pattern_tracker.stream_features_enabled:
            return {
                "enabled": False,
                "message": "Tick features not enabled. Set STREAM_FEATURES_ENABLED=true",
                "ticks": []
            }
        
        ticks = list(pattern_tracker.tick_ring) if pattern_tracker.tick_ring else []
        return {
            "enabled": True,
            "ticks": ticks,
            "count": len(ticks),
            "max_size": int(os.getenv("STREAM_RING_SIZE", "1200")),
            "sample_every": pattern_tracker.stream_sample_every,
            "influence_enabled": pattern_tracker.stream_influence_enabled
        }
    except Exception as e:
        logger.error(f"Error getting tick history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Get comprehensive metrics"""
    stats = pattern_tracker.enhanced_engine.pattern_stats
    
    # Calculate directional metrics for different window sizes
    all_records = list(pattern_tracker.prediction_history)
    metrics_20 = calculate_directional_metrics(all_records, 20)
    metrics_50 = calculate_directional_metrics(all_records, 50)
    metrics_100 = calculate_directional_metrics(all_records, 100)
    
    return {
        "pattern_statistics": {
            "pattern1": {
                "name": "Post-Max-Payout Recovery",
                "accuracy": stats['pattern1'].accuracy,
                "total_predictions": stats['pattern1'].successful_predictions + stats['pattern1'].failed_predictions,
                "successful_predictions": stats['pattern1'].successful_predictions,
                "last_updated": stats['pattern1'].last_updated.isoformat(),
                "validated_improvement": 0.727,  # 72.7% improvement
            },
            "pattern2": {
                "name": "Ultra-Short High-Payout",
                "accuracy": stats['pattern2'].accuracy,
                "total_predictions": stats['pattern2'].successful_predictions + stats['pattern2'].failed_predictions,
                "successful_predictions": stats['pattern2'].successful_predictions,
                "last_updated": stats['pattern2'].last_updated.isoformat(),
                "validated_improvement": 0.251,  # 25.1% improvement
            },
            "pattern3": {
                "name": "Momentum Thresholds",
                "accuracy": stats['pattern3'].accuracy,
                "total_predictions": stats['pattern3'].successful_predictions + stats['pattern3'].failed_predictions,
                "successful_predictions": stats['pattern3'].successful_predictions,
                "last_updated": stats['pattern3'].last_updated.isoformat(),
                "validated_improvement": 0.244,  # 24.4% improvement minimum
            },
        },
        "directional_metrics": {
            "last_20": metrics_20,
            "last_50": metrics_50,
            "last_100": metrics_100,
            "targets": {
                "median_E40": {"target": 0.0, "range": [-0.25, 0.25]},
                "within_2_windows": {"target": 0.5, "min": 0.5},
                "coverage_rate": {"target": 0.85, "range": [0.83, 0.87]},
                "early_skew": {"target": 0.0, "range": [-0.1, 0.1]}
            }
        },
        "side_bet_metrics": pattern_tracker.side_bet_performance,
        "system_performance": {
            "uptime_seconds": int((datetime.now() - system_stats['start_time']).total_seconds()),
            "total_game_updates": system_stats['total_game_updates'],
            "error_rate": system_stats['total_errors'] / max(system_stats['total_game_updates'], 1),
            "connected_clients": len(connected_clients),
        },
        "constants": {
            "tick_duration_ms": TICK_DURATION_MS,
            "median_duration": MEDIAN_DURATION,
            "ultra_short_threshold": ULTRA_SHORT_THRESHOLD,
            "max_payout_threshold": MAX_PAYOUT_THRESHOLD,
        }
    }