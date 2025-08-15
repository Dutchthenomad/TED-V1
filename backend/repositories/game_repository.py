"""
Repository layer for persistent storage with MongoDB.
Implements safe persistence with feature flag for easy rollback.
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import os
try:
    from ..models.storage import (
        GameRecord, PredictionRecord, SideBetRecord, 
        HourlyMetrics, TickSample, PersistenceStatus
    )
except ImportError:
    from models.storage import (
        GameRecord, PredictionRecord, SideBetRecord, 
        HourlyMetrics, TickSample, PersistenceStatus
    )

logger = logging.getLogger(__name__)


class GameRepository:
    """
    Repository for game data persistence.
    Can be disabled via PERSISTENCE_ENABLED flag for safe rollback.
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.games = db.games
        self.predictions = db.predictions
        self.side_bets = db.side_bets
        self.metrics = db.metrics_hourly
        self.tick_samples = db.tick_samples
        
        # Feature flag for safe rollback
        self.persistence_enabled = os.getenv("PERSISTENCE_ENABLED", "false").lower() == "true"
        
        # Batch settings
        self.batch_size = int(os.getenv("PERSISTENCE_BATCH_SIZE", "100"))
        
        # Track persistence status
        self.status = PersistenceStatus(enabled=self.persistence_enabled)
        
        if not self.persistence_enabled:
            logger.warning("Persistence is DISABLED. Data will not be saved to MongoDB.")
        else:
            logger.info("Persistence is ENABLED. Data will be saved to MongoDB.")
    
    async def initialize_indexes(self) -> bool:
        """Create all required indexes for optimal performance"""
        if not self.persistence_enabled:
            return False
            
        try:
            # Games collection indexes
            await self.games.create_index("game_id", unique=True)
            await self.games.create_index([("created_at", -1)])
            await self.games.create_index([("duration_ticks", 1)])
            await self.games.create_index([
                ("created_at", -1), 
                ("had_predictions", 1)
            ])
            
            # Predictions collection indexes
            await self.predictions.create_index("game_id")
            await self.predictions.create_index([("created_at", -1)])
            await self.predictions.create_index([
                ("game_id", 1), 
                ("predicted_at_tick", 1)
            ])
            await self.predictions.create_index("error_metrics.e40")
            
            # Side bets collection indexes
            await self.side_bets.create_index("game_id")
            await self.side_bets.create_index([("created_at", -1)])
            await self.side_bets.create_index([
                ("game_id", 1), 
                ("placed_at_tick", 1)
            ])
            await self.side_bets.create_index("actual_outcome")
            
            # Metrics collection indexes
            await self.metrics.create_index([("hour_start", -1)])
            await self.metrics.create_index([
                ("hour_start", -1), 
                ("hour_end", -1)
            ])
            
            # Tick samples collection indexes
            await self.tick_samples.create_index([
                ("game_id", 1), 
                ("tick", 1)
            ], unique=True)
            await self.tick_samples.create_index([("created_at", -1)])
            
            logger.info("All database indexes created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
            self.status.last_error = str(e)
            self.status.error_count += 1
            return False
    
    # Game Operations
    
    async def save_game(self, game: GameRecord) -> Optional[str]:
        """Save or update game record"""
        if not self.persistence_enabled:
            return None
            
        try:
            game.updated_at = datetime.utcnow()
            result = await self.games.update_one(
                {"game_id": game.game_id},
                {"$set": game.dict()},
                upsert=True
            )
            
            self.status.last_save = datetime.utcnow()
            self.status.records_saved_total += 1
            
            return game.game_id
            
        except Exception as e:
            logger.error(f"Error saving game {game.game_id}: {e}")
            self.status.last_error = str(e)
            self.status.error_count += 1
            return None
    
    async def get_game(self, game_id: str) -> Optional[Dict]:
        """Retrieve game by ID"""
        if not self.persistence_enabled:
            return None
            
        try:
            return await self.games.find_one({"game_id": game_id})
        except Exception as e:
            logger.error(f"Error retrieving game {game_id}: {e}")
            return None
    
    async def update_game_end(self, game_id: str, end_tick: int, 
                             final_price: float, treasury_remainder: Optional[int] = None):
        """Update game with ending information"""
        if not self.persistence_enabled:
            return
            
        try:
            # Get start tick to calculate duration
            game = await self.games.find_one({"game_id": game_id})
            if not game:
                logger.warning(f"Game {game_id} not found for end update")
                return
            
            duration = end_tick - game["start_tick"]
            
            await self.games.update_one(
                {"game_id": game_id},
                {"$set": {
                    "end_tick": end_tick,
                    "duration_ticks": duration,
                    "final_price": final_price,
                    "treasury_remainder": treasury_remainder,
                    "updated_at": datetime.utcnow()
                }}
            )
            
        except Exception as e:
            logger.error(f"Error updating game end for {game_id}: {e}")
    
    # Prediction Operations
    
    async def save_prediction(self, prediction: PredictionRecord) -> Optional[str]:
        """Save prediction record"""
        if not self.persistence_enabled:
            return None
            
        try:
            result = await self.predictions.insert_one(prediction.dict())
            
            # Update game to indicate it has predictions
            await self.games.update_one(
                {"game_id": prediction.game_id},
                {"$set": {"had_predictions": True}}
            )
            
            self.status.records_saved_total += 1
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving prediction for game {prediction.game_id}: {e}")
            self.status.last_error = str(e)
            self.status.error_count += 1
            return None
    
    async def update_prediction_outcome(self, game_id: str, actual_tick: int):
        """Update all predictions for a game with actual outcome"""
        if not self.persistence_enabled:
            return
            
        try:
            # Find all predictions for this game without outcomes
            cursor = self.predictions.find({
                "game_id": game_id,
                "actual_end_tick": None
            })
            
            predictions = await cursor.to_list(None)
            
            for pred_doc in predictions:
                # Create PredictionRecord from document
                pred = PredictionRecord(**pred_doc)
                
                # Calculate error metrics
                error_metrics = pred.calculate_error_metrics(actual_tick)
                
                # Update prediction with outcome
                await self.predictions.update_one(
                    {"_id": pred_doc["_id"]},
                    {"$set": {
                        "actual_end_tick": actual_tick,
                        "error_metrics": error_metrics
                    }}
                )
            
            # Update game with prediction accuracy
            if predictions:
                within_2_windows = sum(
                    1 for p in predictions 
                    if abs(p["predicted_end_tick"] - actual_tick) <= 80
                )
                accuracy = within_2_windows / len(predictions) if predictions else 0
                
                await self.games.update_one(
                    {"game_id": game_id},
                    {"$set": {"prediction_accuracy": accuracy}}
                )
                
        except Exception as e:
            logger.error(f"Error updating prediction outcomes for game {game_id}: {e}")
    
    async def get_recent_predictions(self, hours: int = 24) -> List[Dict]:
        """Get predictions from last N hours"""
        if not self.persistence_enabled:
            return []
            
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            cursor = self.predictions.find(
                {"created_at": {"$gte": cutoff}}
            ).sort("created_at", -1)
            
            return await cursor.to_list(None)
            
        except Exception as e:
            logger.error(f"Error getting recent predictions: {e}")
            return []
    
    # Side Bet Operations
    
    async def save_side_bet(self, side_bet: SideBetRecord) -> Optional[str]:
        """Save side bet record"""
        if not self.persistence_enabled:
            return None
            
        try:
            result = await self.side_bets.insert_one(side_bet.dict())
            
            # Increment side bet counter for game
            await self.games.update_one(
                {"game_id": side_bet.game_id},
                {"$inc": {"side_bets_placed": 1}}
            )
            
            self.status.records_saved_total += 1
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error saving side bet for game {side_bet.game_id}: {e}")
            self.status.last_error = str(e)
            self.status.error_count += 1
            return None
    
    async def update_side_bet_outcomes(self, game_id: str, game_end_tick: int):
        """Update all side bets for a game with outcomes"""
        if not self.persistence_enabled:
            return
            
        try:
            cursor = self.side_bets.find({
                "game_id": game_id,
                "actual_outcome": "PENDING"
            })
            
            side_bets = await cursor.to_list(None)
            
            for bet_doc in side_bets:
                bet = SideBetRecord(**bet_doc)
                payout = bet.calculate_payout(game_end_tick)
                
                await self.side_bets.update_one(
                    {"_id": bet_doc["_id"]},
                    {"$set": {
                        "actual_outcome": bet.actual_outcome.value,
                        "payout": payout
                    }}
                )
                
        except Exception as e:
            logger.error(f"Error updating side bet outcomes for game {game_id}: {e}")
    
    # Tick Sample Operations
    
    async def save_tick_sample(self, tick_sample: TickSample) -> Optional[str]:
        """Save tick sample (with deduplication)"""
        if not self.persistence_enabled:
            return None
            
        try:
            # Use upsert to avoid duplicates
            result = await self.tick_samples.update_one(
                {
                    "game_id": tick_sample.game_id,
                    "tick": tick_sample.tick
                },
                {"$set": tick_sample.dict()},
                upsert=True
            )
            
            if result.upserted_id:
                self.status.records_saved_total += 1
                return str(result.upserted_id)
            return None
            
        except Exception as e:
            logger.error(f"Error saving tick sample: {e}")
            return None
    
    async def save_tick_samples_batch(self, samples: List[TickSample]) -> int:
        """Save multiple tick samples efficiently"""
        if not self.persistence_enabled or not samples:
            return 0
            
        try:
            # Prepare bulk operations
            operations = []
            for sample in samples:
                operations.append({
                    "update_one": {
                        "filter": {
                            "game_id": sample.game_id,
                            "tick": sample.tick
                        },
                        "update": {"$set": sample.dict()},
                        "upsert": True
                    }
                })
            
            # Execute bulk write
            result = await self.tick_samples.bulk_write(operations, ordered=False)
            
            saved_count = result.upserted_count + result.modified_count
            self.status.records_saved_total += saved_count
            
            return saved_count
            
        except Exception as e:
            logger.error(f"Error in batch save of tick samples: {e}")
            return 0
    
    # Metrics Operations
    
    async def calculate_hourly_metrics(self, hour_start: datetime, hour_end: datetime) -> HourlyMetrics:
        """Calculate aggregated metrics for an hour"""
        if not self.persistence_enabled:
            return HourlyMetrics(hour_start=hour_start, hour_end=hour_end)
            
        try:
            # Calculate prediction metrics
            pred_pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": hour_start, "$lt": hour_end},
                        "actual_end_tick": {"$ne": None}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "count": {"$sum": 1},
                        "median_e40": {"$avg": "$error_metrics.e40"},
                        "mean_absolute_error": {"$avg": "$error_metrics.absolute_error"},
                        "within_1_window": {
                            "$avg": {
                                "$cond": [{"$lte": ["$error_metrics.within_windows", 1]}, 1, 0]
                            }
                        },
                        "within_2_windows": {
                            "$avg": {
                                "$cond": [{"$lte": ["$error_metrics.within_windows", 2]}, 1, 0]
                            }
                        },
                        "within_3_windows": {
                            "$avg": {
                                "$cond": [{"$lte": ["$error_metrics.within_windows", 3]}, 1, 0]
                            }
                        }
                    }
                }
            ]
            
            pred_results = await self.predictions.aggregate(pred_pipeline).to_list(1)
            pred_metrics = pred_results[0] if pred_results else {}
            
            # Calculate side bet metrics
            bet_pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": hour_start, "$lt": hour_end}
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "total_recommended": {"$sum": 1},
                        "positive_ev_count": {
                            "$sum": {"$cond": [{"$gt": ["$expected_value", 0]}, 1, 0]}
                        },
                        "bets_won": {
                            "$sum": {"$cond": [{"$eq": ["$actual_outcome", "WON"]}, 1, 0]}
                        },
                        "bets_lost": {
                            "$sum": {"$cond": [{"$eq": ["$actual_outcome", "LOST"]}, 1, 0]}
                        },
                        "total_payout": {"$sum": "$payout"}
                    }
                }
            ]
            
            bet_results = await self.side_bets.aggregate(bet_pipeline).to_list(1)
            bet_metrics = bet_results[0] if bet_results else {}
            
            # Calculate ROI
            if bet_metrics.get("bets_won", 0) + bet_metrics.get("bets_lost", 0) > 0:
                total_bets = bet_metrics["bets_won"] + bet_metrics["bets_lost"]
                roi = (bet_metrics.get("total_payout", 0) / total_bets) * 100
            else:
                roi = 0
            
            # Count games
            games_count = await self.games.count_documents({
                "created_at": {"$gte": hour_start, "$lt": hour_end}
            })
            
            # Create metrics object
            metrics = HourlyMetrics(
                hour_start=hour_start,
                hour_end=hour_end,
                games_analyzed=games_count,
                predictions_made=pred_metrics.get("count", 0),
                prediction_metrics={
                    "median_e40": pred_metrics.get("median_e40", 0),
                    "mean_absolute_error": pred_metrics.get("mean_absolute_error", 0),
                    "within_1_window": pred_metrics.get("within_1_window", 0),
                    "within_2_windows": pred_metrics.get("within_2_windows", 0),
                    "within_3_windows": pred_metrics.get("within_3_windows", 0)
                },
                side_bet_metrics={
                    "total_recommended": bet_metrics.get("total_recommended", 0),
                    "positive_ev_count": bet_metrics.get("positive_ev_count", 0),
                    "bets_won": bet_metrics.get("bets_won", 0),
                    "bets_lost": bet_metrics.get("bets_lost", 0),
                    "total_ev": bet_metrics.get("total_payout", 0),
                    "roi_percentage": roi
                }
            )
            
            # Save metrics
            await self.metrics.insert_one(metrics.dict())
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating hourly metrics: {e}")
            return HourlyMetrics(hour_start=hour_start, hour_end=hour_end)
    
    # Data Retention
    
    async def cleanup_old_data(self, retention_days: Dict[str, int]) -> Dict[str, int]:
        """Remove old data based on retention policies"""
        if not self.persistence_enabled:
            return {}
            
        deleted_counts = {}
        
        try:
            # Clean tick samples (highest volume, shortest retention)
            if "tick_samples" in retention_days:
                cutoff = datetime.utcnow() - timedelta(days=retention_days["tick_samples"])
                result = await self.tick_samples.delete_many({"created_at": {"$lt": cutoff}})
                deleted_counts["tick_samples"] = result.deleted_count
            
            # Clean predictions
            if "predictions" in retention_days:
                cutoff = datetime.utcnow() - timedelta(days=retention_days["predictions"])
                result = await self.predictions.delete_many({"created_at": {"$lt": cutoff}})
                deleted_counts["predictions"] = result.deleted_count
            
            # Clean side bets
            if "side_bets" in retention_days:
                cutoff = datetime.utcnow() - timedelta(days=retention_days["side_bets"])
                result = await self.side_bets.delete_many({"created_at": {"$lt": cutoff}})
                deleted_counts["side_bets"] = result.deleted_count
            
            # Clean games
            if "games" in retention_days:
                cutoff = datetime.utcnow() - timedelta(days=retention_days["games"])
                result = await self.games.delete_many({"created_at": {"$lt": cutoff}})
                deleted_counts["games"] = result.deleted_count
            
            # Metrics are kept indefinitely (low volume)
            
            logger.info(f"Data cleanup completed: {deleted_counts}")
            return deleted_counts
            
        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")
            return deleted_counts
    
    # Status and Health
    
    def get_status(self) -> Dict:
        """Get persistence system status"""
        return {
            "enabled": self.persistence_enabled,
            "last_save": self.status.last_save.isoformat() if self.status.last_save else None,
            "records_saved": self.status.records_saved_total,
            "records_pending": self.status.records_pending,
            "errors": self.status.error_count,
            "last_error": self.status.last_error
        }