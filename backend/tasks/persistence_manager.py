"""
Background persistence manager for saving in-memory data to MongoDB.
Runs async tasks to persist data without blocking real-time operations.
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Dict, Any
import logging

try:
    from ..models.storage import (
        GameRecord, PredictionRecord, SideBetRecord,
        TickSample, SideBetRecommendation
    )
    from ..repositories.game_repository import GameRepository
except ImportError:
    from models.storage import (
        GameRecord, PredictionRecord, SideBetRecord,
        TickSample, SideBetRecommendation
    )
    from repositories.game_repository import GameRepository

if TYPE_CHECKING:
    from server import IntegratedPatternTracker

logger = logging.getLogger(__name__)


class PersistenceManager:
    """
    Manages background persistence of in-memory data to MongoDB.
    Can be safely disabled via environment variable for rollback.
    """
    
    def __init__(self, tracker: 'IntegratedPatternTracker', repo: GameRepository):
        self.tracker = tracker
        self.repo = repo
        self.running = False
        
        # Configuration
        self.enabled = os.getenv("PERSISTENCE_ENABLED", "false").lower() == "true"
        self.persist_interval = int(os.getenv("PERSISTENCE_INTERVAL_SECONDS", "30"))
        self.batch_size = int(os.getenv("PERSISTENCE_BATCH_SIZE", "100"))
        
        # Retention policies (days)
        self.retention_days = {
            "tick_samples": int(os.getenv("TICK_RETENTION_DAYS", "7")),
            "predictions": int(os.getenv("PREDICTION_RETENTION_DAYS", "90")),
            "side_bets": int(os.getenv("SIDEBET_RETENTION_DAYS", "90")),
            "games": int(os.getenv("GAME_RETENTION_DAYS", "180"))
        }
        
        # Tasks
        self.tasks = []
        
        if not self.enabled:
            logger.warning("PersistenceManager is DISABLED. No background persistence will occur.")
        else:
            logger.info(f"PersistenceManager is ENABLED. Persisting every {self.persist_interval}s")
    
    async def start(self):
        """Start all background persistence tasks"""
        if not self.enabled:
            logger.info("Persistence disabled - not starting background tasks")
            return
            
        self.running = True
        
        # Initialize database indexes
        await self.repo.initialize_indexes()
        
        # Start background tasks
        self.tasks = [
            asyncio.create_task(self.persist_memory_buffers()),
            asyncio.create_task(self.calculate_hourly_metrics()),
            asyncio.create_task(self.cleanup_old_data())
        ]
        
        logger.info("Background persistence tasks started")
    
    async def stop(self):
        """Stop all background tasks gracefully"""
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("Background persistence tasks stopped")
    
    async def persist_memory_buffers(self):
        """Periodically save in-memory buffers to MongoDB"""
        while self.running:
            try:
                await asyncio.sleep(self.persist_interval)
                
                if not self.enabled:
                    continue
                
                # Track what we've saved
                saved_counts = {
                    "predictions": 0,
                    "side_bets": 0,
                    "tick_samples": 0
                }
                
                # Save prediction history
                predictions_to_save = []
                for pred in list(self.tracker.prediction_history):
                    if not pred.get("_persisted"):
                        # Convert to PredictionRecord
                        prediction = PredictionRecord(
                            game_id=pred["game_id"],
                            predicted_at_tick=pred["predicted_at_tick"],
                            predicted_end_tick=pred["predicted_tick"],
                            actual_end_tick=pred.get("actual_tick"),
                            confidence=pred.get("confidence", 0.5),
                            uncertainty_bounds=pred.get("uncertainty_bounds", {"lower": 0, "upper": 0}),
                            features_used=pred.get("features", {}),
                            error_metrics=pred.get("error_metrics"),
                            model_version=pred.get("model_version", "v2.1.0")
                        )
                        
                        # Save to database
                        result = await self.repo.save_prediction(prediction)
                        if result:
                            pred["_persisted"] = True
                            saved_counts["predictions"] += 1
                        
                        # Batch limit
                        if saved_counts["predictions"] >= self.batch_size:
                            break
                
                # Save side bet history
                for bet in list(self.tracker.side_bet_history):
                    if not bet.get("_persisted"):
                        # Convert to SideBetRecord
                        side_bet = SideBetRecord(
                            game_id=bet["game_id"],
                            placed_at_tick=bet["tick"],
                            window_end_tick=bet["tick"] + 40,
                            probability=bet.get("probability", 0),
                            expected_value=bet.get("expected_value", 0),
                            confidence=bet.get("confidence", 0),
                            recommendation=SideBetRecommendation(bet.get("action", "SKIP")),
                            actual_outcome=bet.get("outcome", "PENDING")
                        )
                        
                        # Save to database
                        result = await self.repo.save_side_bet(side_bet)
                        if result:
                            bet["_persisted"] = True
                            saved_counts["side_bets"] += 1
                        
                        # Batch limit
                        if saved_counts["side_bets"] >= self.batch_size:
                            break
                
                # Save tick samples (sample every 10th tick to reduce volume)
                tick_samples = []
                tick_list = list(self.tracker.tick_ring)
                
                for i, tick_data in enumerate(tick_list):
                    # Sample every 10th tick and ensure not already persisted
                    if i % 10 == 0 and not tick_data.get("_persisted"):
                        if "game_id" in tick_data and "tick" in tick_data:
                            tick_sample = TickSample(
                                game_id=tick_data["game_id"],
                                tick=tick_data["tick"],
                                price=tick_data.get("price", 0),
                                features=tick_data.get("features", {}),
                                timestamp=tick_data.get("timestamp", datetime.utcnow())
                            )
                            tick_samples.append(tick_sample)
                            tick_data["_persisted"] = True
                
                # Batch save tick samples
                if tick_samples:
                    saved_count = await self.repo.save_tick_samples_batch(tick_samples[:self.batch_size])
                    saved_counts["tick_samples"] = saved_count
                
                # Log if we saved anything
                if any(saved_counts.values()):
                    logger.info(f"Persisted: {saved_counts}")
                
            except Exception as e:
                logger.error(f"Error in persist_memory_buffers: {e}")
                # Continue running even if error occurs
    
    async def calculate_hourly_metrics(self):
        """Calculate and store hourly aggregated metrics"""
        while self.running:
            try:
                if not self.enabled:
                    await asyncio.sleep(3600)  # Check again in an hour
                    continue
                
                # Calculate when next hour starts
                now = datetime.utcnow()
                hour_start = now.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                # Wait until hour is complete
                wait_seconds = (hour_end - now).total_seconds()
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                # Calculate metrics for completed hour
                metrics = await self.repo.calculate_hourly_metrics(hour_start, hour_end)
                
                logger.info(f"Calculated hourly metrics for {hour_start}: "
                          f"{metrics.predictions_made} predictions, "
                          f"{metrics.games_analyzed} games")
                
            except Exception as e:
                logger.error(f"Error calculating hourly metrics: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying
    
    async def cleanup_old_data(self):
        """Implement data retention policies"""
        while self.running:
            try:
                if not self.enabled:
                    await asyncio.sleep(86400)  # Check again tomorrow
                    continue
                
                # Run cleanup once per day at 3 AM UTC
                now = datetime.utcnow()
                next_cleanup = now.replace(hour=3, minute=0, second=0, microsecond=0)
                
                # If it's already past 3 AM today, schedule for tomorrow
                if now >= next_cleanup:
                    next_cleanup += timedelta(days=1)
                
                # Wait until cleanup time
                wait_seconds = (next_cleanup - now).total_seconds()
                await asyncio.sleep(wait_seconds)
                
                # Perform cleanup
                deleted_counts = await self.repo.cleanup_old_data(self.retention_days)
                
                logger.info(f"Data cleanup completed: {deleted_counts}")
                
            except Exception as e:
                logger.error(f"Error during data cleanup: {e}")
                await asyncio.sleep(3600)  # Wait an hour before retrying
    
    async def persist_current_game(self, game_data: Dict[str, Any]):
        """
        Persist current game data immediately.
        Called when game events occur (start, update, end).
        """
        if not self.enabled:
            return
            
        try:
            event = game_data.get("event")
            game_id = game_data.get("gameId")
            
            if not game_id:
                return
            
            if event == "gameStart":
                # Create new game record
                game = GameRecord(
                    game_id=game_id,
                    start_tick=game_data.get("tick", 0),
                    peak_price=game_data.get("price", 1.0),
                    peak_tick=game_data.get("tick", 0)
                )
                await self.repo.save_game(game)
                
            elif event == "priceUpdate":
                # Update peak if needed (handled in tracker)
                pass
                
            elif event == "gameEnd":
                # Update game completion
                await self.repo.update_game_end(
                    game_id=game_id,
                    end_tick=game_data.get("tick", 0),
                    final_price=game_data.get("finalPrice", 0),
                    treasury_remainder=game_data.get("treasuryRemainder")
                )
                
                # Update all predictions for this game
                await self.repo.update_prediction_outcome(game_id, game_data.get("tick", 0))
                
                # Update all side bets for this game
                await self.repo.update_side_bet_outcomes(game_id, game_data.get("tick", 0))
                
        except Exception as e:
            logger.error(f"Error persisting game {game_id}: {e}")
    
    def get_status(self) -> Dict:
        """Get persistence manager status"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "persist_interval": self.persist_interval,
            "batch_size": self.batch_size,
            "retention_days": self.retention_days,
            "repository_status": self.repo.get_status() if self.repo else None
        }