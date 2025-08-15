"""
Integration module for adding persistence to the existing TED server.
This module can be imported and activated without modifying core server logic.
Provides safe rollback via PERSISTENCE_ENABLED environment variable.
"""

import os
import logging
from typing import Optional, TYPE_CHECKING
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi import HTTPException

try:
    from repositories.game_repository import GameRepository
    from tasks.persistence_manager import PersistenceManager
    from models.storage import GameRecord, PredictionRecord, SideBetRecord
except ImportError:
    # Handle both relative and absolute imports
    try:
        from .repositories.game_repository import GameRepository
        from .tasks.persistence_manager import PersistenceManager
        from .models.storage import GameRecord, PredictionRecord, SideBetRecord
    except ImportError:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from repositories.game_repository import GameRepository
        from tasks.persistence_manager import PersistenceManager
        from models.storage import GameRecord, PredictionRecord, SideBetRecord

if TYPE_CHECKING:
    from server import IntegratedPatternTracker

logger = logging.getLogger(__name__)


class PersistenceIntegration:
    """
    Main integration class for persistence features.
    Wraps all persistence functionality with safe fallback.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase, tracker: Optional['IntegratedPatternTracker'] = None):
        """
        Initialize persistence integration.
        
        Args:
            db: MongoDB database connection
            tracker: IntegratedPatternTracker instance (can be set later)
        """
        self.enabled = os.getenv("PERSISTENCE_ENABLED", "false").lower() == "true"
        self.db = db
        self.tracker = tracker
        self.repo = None
        self.manager = None
        
        if self.enabled:
            logger.info("Initializing persistence integration...")
            self.repo = GameRepository(db)
            if tracker:
                self.manager = PersistenceManager(tracker, self.repo)
        else:
            logger.info("Persistence is DISABLED. Running in-memory only mode.")
    
    def set_tracker(self, tracker: 'IntegratedPatternTracker'):
        """Set the tracker instance after initialization"""
        self.tracker = tracker
        if self.enabled and self.repo and not self.manager:
            self.manager = PersistenceManager(tracker, self.repo)
    
    async def start(self):
        """Start persistence background tasks"""
        if self.enabled and self.manager:
            await self.manager.start()
            logger.info("Persistence background tasks started")
    
    async def stop(self):
        """Stop persistence background tasks"""
        if self.enabled and self.manager:
            await self.manager.stop()
            logger.info("Persistence background tasks stopped")
    
    async def on_game_start(self, game_id: str, start_tick: int, initial_price: float = 1.0):
        """Called when a new game starts"""
        if not self.enabled or not self.repo:
            return
        
        try:
            game = GameRecord(
                game_id=game_id,
                start_tick=start_tick,
                peak_price=initial_price,
                peak_tick=start_tick
            )
            await self.repo.save_game(game)
            logger.debug(f"Persisted game start: {game_id}")
        except Exception as e:
            logger.error(f"Error persisting game start: {e}")
    
    async def on_game_update(self, game_id: str, tick: int, price: float, peak_price: float, peak_tick: int):
        """Called on game price updates"""
        if not self.enabled or not self.repo:
            return
        
        try:
            # Update peak if needed
            if price > peak_price:
                await self.repo.games.update_one(
                    {"game_id": game_id},
                    {"$set": {
                        "peak_price": price,
                        "peak_tick": tick
                    }}
                )
        except Exception as e:
            logger.error(f"Error updating game peak: {e}")
    
    async def on_game_end(self, game_id: str, end_tick: int, final_price: float, 
                         treasury_remainder: Optional[int] = None):
        """Called when a game ends"""
        if not self.enabled or not self.repo:
            return
        
        try:
            # Update game end
            await self.repo.update_game_end(game_id, end_tick, final_price, treasury_remainder)
            
            # Update predictions
            await self.repo.update_prediction_outcome(game_id, end_tick)
            
            # Update side bets
            await self.repo.update_side_bet_outcomes(game_id, end_tick)
            
            logger.debug(f"Persisted game end: {game_id} at tick {end_tick}")
        except Exception as e:
            logger.error(f"Error persisting game end: {e}")
    
    async def on_prediction_made(self, game_id: str, predicted_at_tick: int, 
                                predicted_end_tick: int, confidence: float,
                                uncertainty_bounds: dict, features: dict):
        """Called when a prediction is made"""
        if not self.enabled or not self.repo:
            return
        
        try:
            prediction = PredictionRecord(
                game_id=game_id,
                predicted_at_tick=predicted_at_tick,
                predicted_end_tick=predicted_end_tick,
                confidence=confidence,
                uncertainty_bounds=uncertainty_bounds,
                features_used=features
            )
            await self.repo.save_prediction(prediction)
        except Exception as e:
            logger.error(f"Error persisting prediction: {e}")
    
    async def on_side_bet_placed(self, game_id: str, placed_at_tick: int,
                                probability: float, expected_value: float,
                                confidence: float, recommendation: str):
        """Called when a side bet recommendation is made"""
        if not self.enabled or not self.repo:
            return
        
        try:
            side_bet = SideBetRecord(
                game_id=game_id,
                placed_at_tick=placed_at_tick,
                window_end_tick=placed_at_tick + 40,
                probability=probability,
                expected_value=expected_value,
                confidence=confidence,
                recommendation=recommendation
            )
            await self.repo.save_side_bet(side_bet)
        except Exception as e:
            logger.error(f"Error persisting side bet: {e}")
    
    def get_status(self) -> dict:
        """Get persistence system status"""
        if not self.enabled:
            return {
                "enabled": False,
                "message": "Persistence is disabled"
            }
        
        status = {
            "enabled": True,
            "repository": self.repo.get_status() if self.repo else None,
            "manager": self.manager.get_status() if self.manager else None
        }
        
        return status
    
    async def get_game_history(self, game_id: str) -> Optional[dict]:
        """Get complete history for a game"""
        if not self.enabled or not self.repo:
            return None
        
        try:
            game = await self.repo.get_game(game_id)
            if not game:
                return None
            
            predictions = await self.repo.predictions.find({"game_id": game_id}).to_list(None)
            side_bets = await self.repo.side_bets.find({"game_id": game_id}).to_list(None)
            
            return {
                "game": game,
                "predictions": predictions,
                "side_bets": side_bets
            }
        except Exception as e:
            logger.error(f"Error getting game history: {e}")
            return None
    
    async def get_recent_metrics(self, hours: int = 24) -> dict:
        """Get recent performance metrics"""
        if not self.enabled or not self.repo:
            return {}
        
        try:
            predictions = await self.repo.get_recent_predictions(hours)
            
            # Calculate metrics
            if predictions:
                completed = [p for p in predictions if p.get("actual_end_tick")]
                if completed:
                    total = len(completed)
                    within_1 = sum(1 for p in completed 
                                 if abs(p.get("error_metrics", {}).get("within_windows", 999)) <= 1)
                    within_2 = sum(1 for p in completed 
                                 if abs(p.get("error_metrics", {}).get("within_windows", 999)) <= 2)
                    avg_e40 = sum(p.get("error_metrics", {}).get("e40", 0) 
                                for p in completed) / total
                    
                    return {
                        "total_predictions": total,
                        "accuracy_1_window": within_1 / total,
                        "accuracy_2_windows": within_2 / total,
                        "average_e40": avg_e40
                    }
            
            return {"message": "No completed predictions in timeframe"}
            
        except Exception as e:
            logger.error(f"Error getting recent metrics: {e}")
            return {}


# Helper function to easily add persistence to existing server
def setup_persistence(app, db: AsyncIOMotorDatabase, tracker: Optional['IntegratedPatternTracker'] = None):
    """
    Setup persistence for the TED server.
    
    Args:
        app: FastAPI application instance
        db: MongoDB database connection
        tracker: IntegratedPatternTracker instance
    
    Returns:
        PersistenceIntegration instance
    """
    # Create persistence integration
    persistence = PersistenceIntegration(db, tracker)
    
    # Add to app state for access in routes
    app.state.persistence = persistence
    
    # Add startup/shutdown handlers
    @app.on_event("startup")
    async def start_persistence():
        await persistence.start()
    
    @app.on_event("shutdown")
    async def stop_persistence():
        await persistence.stop()
    
    # Add status endpoint
    @app.get("/api/persistence/status")
    async def get_persistence_status():
        """Get persistence system status"""
        return persistence.get_status()
    
    # Add metrics endpoint
    @app.get("/api/persistence/metrics")
    async def get_persistence_metrics(hours: int = 24):
        """Get recent performance metrics from persistent storage"""
        return await persistence.get_recent_metrics(hours)
    
    # Add game history endpoint
    @app.get("/api/persistence/game/{game_id}")
    async def get_game_history(game_id: str):
        """Get complete history for a specific game"""
        history = await persistence.get_game_history(game_id)
        if not history:
            raise HTTPException(status_code=404, detail="Game not found")
        return history
    
    logger.info(f"Persistence setup complete. Enabled: {persistence.enabled}")
    
    return persistence