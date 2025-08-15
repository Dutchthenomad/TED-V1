# TED System - Persistent Historic Data Storage Implementation Plan

## Executive Summary

This plan outlines the implementation of persistent data storage for the TED system, transitioning from the current in-memory only approach to a hybrid model with MongoDB persistence. This will enable historical analysis, performance tracking across restarts, and long-term pattern discovery.

## Current State Analysis

### Problems with Current Architecture
1. **Data Loss on Restart**: All prediction history and metrics lost
2. **Limited History**: Fixed-size deques (200 games, 1200 ticks)
3. **No Long-term Analysis**: Can't analyze patterns over days/weeks
4. **MongoDB Underutilized**: Connection exists but only used for status_checks
5. **No Performance Tracking**: Can't measure improvement over time

### Current In-Memory Storage
- `prediction_history`: deque(maxlen=200) - ~3-4 hours of data
- `side_bet_history`: deque(maxlen=200) - Recent bet records
- `tick_ring`: deque(maxlen=1200) - ~5 minutes of tick data
- All managed in `IntegratedPatternTracker` class (server.py:129-455)

## Implementation Plan

### Phase 1: Database Schema Design (Week 1)

#### 1.1 MongoDB Collections Schema

```javascript
// games collection - Complete game records
{
  _id: ObjectId,
  game_id: String,  // Unique game identifier
  start_tick: Number,
  end_tick: Number,
  duration_ticks: Number,
  peak_price: Number,
  peak_tick: Number,
  final_price: Number,
  treasury_remainder: Number,
  patterns_detected: [String],
  created_at: DateTime,
  updated_at: DateTime,
  // Denormalized aggregates for fast queries
  had_predictions: Boolean,
  prediction_accuracy: Number,  // If predicted
  side_bets_placed: Number
}

// predictions collection - All predictions with outcomes
{
  _id: ObjectId,
  game_id: String,
  predicted_at_tick: Number,
  predicted_end_tick: Number,
  actual_end_tick: Number,  // null if game still running
  confidence: Number,
  uncertainty_bounds: {
    lower: Number,
    upper: Number
  },
  features_used: {
    epr_active: Boolean,
    peak_ratio: Number,
    volatility: Number,
    momentum: Number
  },
  error_metrics: {
    raw_error: Number,      // predicted - actual
    signed_error: Number,   // with direction
    e40: Number,           // window normalized
    within_windows: Number  // accuracy windows
  },
  model_version: String,
  created_at: DateTime
}

// side_bets collection - Side bet recommendations and outcomes
{
  _id: ObjectId,
  game_id: String,
  placed_at_tick: Number,
  window_end_tick: Number,  // placed_at + 40
  probability: Number,
  expected_value: Number,
  confidence: Number,
  recommendation: String,  // "BET" or "SKIP"
  actual_outcome: String,  // "WON", "LOST", "PENDING"
  payout: Number,         // 5x if won, -1 if lost
  created_at: DateTime
}

// metrics_hourly collection - Aggregated performance metrics
{
  _id: ObjectId,
  hour_start: DateTime,
  hour_end: DateTime,
  games_analyzed: Number,
  predictions_made: Number,
  prediction_metrics: {
    median_e40: Number,
    mean_absolute_error: Number,
    within_1_window: Number,  // percentage
    within_2_windows: Number,
    within_3_windows: Number
  },
  side_bet_metrics: {
    total_recommended: Number,
    positive_ev_count: Number,
    bets_won: Number,
    bets_lost: Number,
    total_ev: Number,
    roi_percentage: Number
  },
  system_metrics: {
    avg_latency_ms: Number,
    websocket_disconnects: Number,
    errors_logged: Number
  },
  created_at: DateTime
}

// tick_samples collection - Sampled tick data for analysis
{
  _id: ObjectId,
  game_id: String,
  tick: Number,
  price: Number,
  features: {
    volatility_10: Number,
    volatility_40: Number,
    momentum: Number,
    rsi: Number,
    volume_ratio: Number
  },
  timestamp: DateTime,
  created_at: DateTime
}
```

#### 1.2 Indexes for Performance

```python
# Critical indexes for each collection
indexes = {
    "games": [
        ("game_id", 1),  # Unique index
        ("created_at", -1),  # Recent games first
        ("duration_ticks", 1),  # Analysis by game length
        ([("created_at", -1), ("had_predictions", 1)])  # Filtered queries
    ],
    "predictions": [
        ("game_id", 1),
        ("created_at", -1),
        ([("game_id", 1), ("predicted_at_tick", 1)]),  # Compound
        ("error_metrics.e40", 1)  # Bias analysis
    ],
    "side_bets": [
        ("game_id", 1),
        ("created_at", -1),
        ([("game_id", 1), ("placed_at_tick", 1)]),
        ("actual_outcome", 1)
    ],
    "metrics_hourly": [
        ("hour_start", -1),  # Time series queries
        ([("hour_start", -1), ("hour_end", -1)])
    ],
    "tick_samples": [
        ([("game_id", 1), ("tick", 1)]),  # Unique compound
        ("created_at", -1)
    ]
}
```

### Phase 2: Data Models & Repository Layer (Week 1-2)

#### 2.1 Pydantic Models

```python
# backend/models/storage.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict

class GameRecord(BaseModel):
    game_id: str
    start_tick: int
    end_tick: Optional[int] = None
    duration_ticks: Optional[int] = None
    peak_price: float
    peak_tick: int
    final_price: Optional[float] = None
    treasury_remainder: Optional[int] = None
    patterns_detected: List[str] = []
    had_predictions: bool = False
    prediction_accuracy: Optional[float] = None
    side_bets_placed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PredictionRecord(BaseModel):
    game_id: str
    predicted_at_tick: int
    predicted_end_tick: int
    actual_end_tick: Optional[int] = None
    confidence: float
    uncertainty_bounds: Dict[str, float]
    features_used: Dict[str, any]
    error_metrics: Optional[Dict[str, float]] = None
    model_version: str = "v2.1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SideBetRecord(BaseModel):
    game_id: str
    placed_at_tick: int
    window_end_tick: int
    probability: float
    expected_value: float
    confidence: float
    recommendation: str
    actual_outcome: str = "PENDING"
    payout: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

#### 2.2 Repository Pattern Implementation

```python
# backend/repositories/game_repository.py
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import List, Optional, Dict
from datetime import datetime, timedelta

class GameRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.games = db.games
        self.predictions = db.predictions
        self.side_bets = db.side_bets
        self.metrics = db.metrics_hourly
        
    async def save_game(self, game: GameRecord) -> str:
        """Save or update game record"""
        result = await self.games.update_one(
            {"game_id": game.game_id},
            {"$set": game.dict()},
            upsert=True
        )
        return game.game_id
    
    async def save_prediction(self, prediction: PredictionRecord) -> str:
        """Save prediction record"""
        result = await self.predictions.insert_one(prediction.dict())
        return str(result.inserted_id)
    
    async def update_prediction_outcome(self, game_id: str, actual_tick: int):
        """Update prediction with actual outcome"""
        predictions = await self.predictions.find(
            {"game_id": game_id, "actual_end_tick": None}
        ).to_list(None)
        
        for pred in predictions:
            error = pred["predicted_end_tick"] - actual_tick
            e40 = error / 40.0
            
            await self.predictions.update_one(
                {"_id": pred["_id"]},
                {"$set": {
                    "actual_end_tick": actual_tick,
                    "error_metrics": {
                        "raw_error": error,
                        "signed_error": error,
                        "e40": e40,
                        "within_windows": abs(error) // 40
                    }
                }}
            )
    
    async def get_recent_predictions(self, hours: int = 24) -> List[Dict]:
        """Get predictions from last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return await self.predictions.find(
            {"created_at": {"$gte": cutoff}}
        ).sort("created_at", -1).to_list(None)
    
    async def calculate_metrics(self, start_time: datetime, end_time: datetime) -> Dict:
        """Calculate aggregated metrics for time period"""
        pipeline = [
            {
                "$match": {
                    "created_at": {"$gte": start_time, "$lt": end_time},
                    "actual_end_tick": {"$ne": None}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "median_e40": {"$avg": "$error_metrics.e40"},
                    "mean_absolute_error": {"$avg": {"$abs": "$error_metrics.raw_error"}},
                    "within_1_window": {
                        "$avg": {
                            "$cond": [{"$lte": ["$error_metrics.within_windows", 1]}, 1, 0]
                        }
                    },
                    "within_2_windows": {
                        "$avg": {
                            "$cond": [{"$lte": ["$error_metrics.within_windows", 2]}, 1, 0]
                        }
                    }
                }
            }
        ]
        
        results = await self.predictions.aggregate(pipeline).to_list(1)
        return results[0] if results else {}
```

### Phase 3: Integration with Existing System (Week 2)

#### 3.1 Modify IntegratedPatternTracker

```python
# backend/server.py modifications
class IntegratedPatternTracker:
    def __init__(self, repo: GameRepository):
        # Existing initialization
        self.repo = repo  # Add repository
        self.pending_saves = []  # Buffer for batch saves
        
    async def on_game_update(self, data: dict):
        """Enhanced with persistence"""
        # Existing logic...
        
        # Save to MongoDB asynchronously
        if data.get("event") == "gameStart":
            game = GameRecord(
                game_id=data["gameId"],
                start_tick=data["tick"],
                peak_price=data["price"],
                peak_tick=data["tick"]
            )
            await self.repo.save_game(game)
            
        elif data.get("event") == "priceUpdate":
            # Update peak if needed
            if data["price"] > self.current_peak:
                await self.repo.games.update_one(
                    {"game_id": data["gameId"]},
                    {"$set": {
                        "peak_price": data["price"],
                        "peak_tick": data["tick"]
                    }}
                )
        
        elif data.get("event") == "gameEnd":
            # Update game completion
            await self.repo.games.update_one(
                {"game_id": data["gameId"]},
                {"$set": {
                    "end_tick": data["tick"],
                    "duration_ticks": data["tick"] - data["startTick"],
                    "final_price": data["finalPrice"],
                    "treasury_remainder": data.get("treasuryRemainder")
                }}
            )
            
            # Update all predictions for this game
            await self.repo.update_prediction_outcome(
                data["gameId"], 
                data["tick"]
            )
    
    async def make_prediction(self, game_id: str, tick: int, features: dict):
        """Enhanced prediction with persistence"""
        # Existing prediction logic...
        prediction = self.ml_engine.predict(features)
        
        # Save prediction
        pred_record = PredictionRecord(
            game_id=game_id,
            predicted_at_tick=tick,
            predicted_end_tick=prediction["tick"],
            confidence=prediction["confidence"],
            uncertainty_bounds=prediction["bounds"],
            features_used={
                "epr_active": features.get("epr_active", False),
                "peak_ratio": features.get("peak_ratio", 0),
                "volatility": features.get("volatility", 0)
            }
        )
        await self.repo.save_prediction(pred_record)
        
        return prediction
```

#### 3.2 Background Tasks for Batch Processing

```python
# backend/tasks/persistence_tasks.py
import asyncio
from datetime import datetime, timedelta
from typing import List

class PersistenceManager:
    def __init__(self, tracker: IntegratedPatternTracker, repo: GameRepository):
        self.tracker = tracker
        self.repo = repo
        self.running = False
        
    async def start(self):
        """Start background persistence tasks"""
        self.running = True
        asyncio.create_task(self.persist_memory_buffers())
        asyncio.create_task(self.calculate_hourly_metrics())
        asyncio.create_task(self.cleanup_old_data())
    
    async def persist_memory_buffers(self):
        """Periodically save in-memory buffers to MongoDB"""
        while self.running:
            try:
                # Save prediction history
                for pred in list(self.tracker.prediction_history):
                    if not pred.get("persisted"):
                        await self.repo.save_prediction(pred)
                        pred["persisted"] = True
                
                # Save side bet history
                for bet in list(self.tracker.side_bet_history):
                    if not bet.get("persisted"):
                        await self.repo.save_side_bet(bet)
                        bet["persisted"] = True
                
                # Sample and save tick data (every 10th tick to reduce volume)
                tick_samples = list(self.tracker.tick_ring)[::10]
                for tick_data in tick_samples:
                    if not tick_data.get("persisted"):
                        await self.repo.save_tick_sample(tick_data)
                        tick_data["persisted"] = True
                        
            except Exception as e:
                logger.error(f"Error persisting buffers: {e}")
            
            await asyncio.sleep(30)  # Every 30 seconds
    
    async def calculate_hourly_metrics(self):
        """Calculate and store hourly aggregated metrics"""
        while self.running:
            try:
                now = datetime.utcnow()
                hour_start = now.replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                # Wait until hour is complete
                await asyncio.sleep((hour_end - now).total_seconds())
                
                # Calculate metrics for completed hour
                metrics = await self.repo.calculate_metrics(hour_start, hour_end)
                
                # Add side bet metrics
                side_bet_metrics = await self.repo.calculate_side_bet_metrics(
                    hour_start, hour_end
                )
                
                # Save hourly metrics
                await self.repo.metrics.insert_one({
                    "hour_start": hour_start,
                    "hour_end": hour_end,
                    "games_analyzed": metrics.get("games_count", 0),
                    "predictions_made": metrics.get("count", 0),
                    "prediction_metrics": {
                        "median_e40": metrics.get("median_e40", 0),
                        "mean_absolute_error": metrics.get("mean_absolute_error", 0),
                        "within_1_window": metrics.get("within_1_window", 0),
                        "within_2_windows": metrics.get("within_2_windows", 0)
                    },
                    "side_bet_metrics": side_bet_metrics,
                    "created_at": datetime.utcnow()
                })
                
            except Exception as e:
                logger.error(f"Error calculating hourly metrics: {e}")
    
    async def cleanup_old_data(self):
        """Implement data retention policies"""
        while self.running:
            try:
                # Keep detailed data for 30 days
                cutoff_detailed = datetime.utcnow() - timedelta(days=30)
                
                # Delete old tick samples (highest volume)
                await self.repo.db.tick_samples.delete_many(
                    {"created_at": {"$lt": cutoff_detailed}}
                )
                
                # Keep predictions for 90 days
                cutoff_predictions = datetime.utcnow() - timedelta(days=90)
                await self.repo.predictions.delete_many(
                    {"created_at": {"$lt": cutoff_predictions}}
                )
                
                # Keep aggregated metrics indefinitely (low volume)
                
                logger.info(f"Cleaned up data older than {cutoff_detailed}")
                
            except Exception as e:
                logger.error(f"Error cleaning up old data: {e}")
            
            await asyncio.sleep(86400)  # Daily cleanup
```

### Phase 4: Analytics API Endpoints (Week 3)

#### 4.1 New API Routes

```python
# backend/server.py - Add new routes
@app.get("/api/analytics/performance")
async def get_performance_metrics(
    hours: int = 24,
    metric_type: str = "all"  # all, predictions, sidebets
):
    """Get historical performance metrics"""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    
    if metric_type in ["all", "predictions"]:
        predictions = await repo.get_recent_predictions(hours)
        pred_metrics = calculate_prediction_metrics(predictions)
    
    if metric_type in ["all", "sidebets"]:
        sidebets = await repo.get_recent_sidebets(hours)
        bet_metrics = calculate_sidebet_metrics(sidebets)
    
    return {
        "period_hours": hours,
        "prediction_metrics": pred_metrics if metric_type != "sidebets" else None,
        "sidebet_metrics": bet_metrics if metric_type != "predictions" else None,
        "timestamp": datetime.utcnow()
    }

@app.get("/api/analytics/games/{game_id}")
async def get_game_details(game_id: str):
    """Get complete game history with predictions"""
    game = await repo.games.find_one({"game_id": game_id})
    predictions = await repo.predictions.find({"game_id": game_id}).to_list(None)
    sidebets = await repo.side_bets.find({"game_id": game_id}).to_list(None)
    
    return {
        "game": game,
        "predictions": predictions,
        "side_bets": sidebets
    }

@app.get("/api/analytics/trends")
async def get_trend_analysis(days: int = 7):
    """Get trend analysis over time"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    # Get hourly metrics
    hourly_metrics = await repo.db.metrics_hourly.find(
        {"hour_start": {"$gte": cutoff}}
    ).sort("hour_start", 1).to_list(None)
    
    # Calculate trends
    trends = {
        "e40_trend": calculate_trend([m["prediction_metrics"]["median_e40"] 
                                      for m in hourly_metrics]),
        "accuracy_trend": calculate_trend([m["prediction_metrics"]["within_2_windows"] 
                                          for m in hourly_metrics]),
        "sidebet_roi_trend": calculate_trend([m["side_bet_metrics"]["roi_percentage"] 
                                              for m in hourly_metrics])
    }
    
    return {
        "period_days": days,
        "hourly_metrics": hourly_metrics,
        "trends": trends,
        "timestamp": datetime.utcnow()
    }

@app.get("/api/analytics/patterns")
async def get_pattern_analysis():
    """Analyze pattern detection effectiveness"""
    pipeline = [
        {
            "$match": {
                "patterns_detected": {"$ne": []},
                "created_at": {"$gte": datetime.utcnow() - timedelta(days=7)}
            }
        },
        {
            "$unwind": "$patterns_detected"
        },
        {
            "$group": {
                "_id": "$patterns_detected",
                "count": {"$sum": 1},
                "avg_accuracy": {"$avg": "$prediction_accuracy"},
                "games": {"$push": "$game_id"}
            }
        },
        {
            "$sort": {"count": -1}
        }
    ]
    
    pattern_stats = await repo.db.games.aggregate(pipeline).to_list(None)
    
    return {
        "pattern_statistics": pattern_stats,
        "total_patterns_detected": sum(p["count"] for p in pattern_stats),
        "timestamp": datetime.utcnow()
    }
```

### Phase 5: Migration & Deployment (Week 3-4)

#### 5.1 Data Migration Script

```python
# scripts/migrate_to_persistent.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import logging

async def create_indexes(db):
    """Create all required indexes"""
    # Games collection
    await db.games.create_index("game_id", unique=True)
    await db.games.create_index([("created_at", -1)])
    
    # Predictions collection
    await db.predictions.create_index("game_id")
    await db.predictions.create_index([("game_id", 1), ("predicted_at_tick", 1)])
    await db.predictions.create_index("error_metrics.e40")
    
    # Side bets collection
    await db.side_bets.create_index("game_id")
    await db.side_bets.create_index([("game_id", 1), ("placed_at_tick", 1)])
    
    # Metrics collection
    await db.metrics_hourly.create_index([("hour_start", -1)])
    
    # Tick samples collection
    await db.tick_samples.create_index([("game_id", 1), ("tick", 1)])
    
    logging.info("All indexes created successfully")

async def migrate_existing_data(tracker, repo):
    """Migrate existing in-memory data to MongoDB"""
    # Migrate prediction history
    for pred in tracker.prediction_history:
        await repo.save_prediction(pred)
    
    # Migrate side bet history
    for bet in tracker.side_bet_history:
        await repo.save_side_bet(bet)
    
    logging.info(f"Migrated {len(tracker.prediction_history)} predictions")
    logging.info(f"Migrated {len(tracker.side_bet_history)} side bets")

async def main():
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.environ['MONGO_URL'])
    db = client[os.environ.get('DB_NAME', 'rugs_tracker')]
    
    # Create indexes
    await create_indexes(db)
    
    # Note: Actual migration would need access to running tracker instance
    logging.info("Migration setup complete. Restart server to begin using persistence.")

if __name__ == "__main__":
    asyncio.run(main())
```

#### 5.2 Deployment Steps

1. **Database Preparation**
   ```bash
   # Run migration script to create indexes
   python scripts/migrate_to_persistent.py
   ```

2. **Configuration Update**
   ```bash
   # Add to .env
   PERSISTENCE_ENABLED=true
   PERSISTENCE_BATCH_SIZE=100
   PERSISTENCE_INTERVAL_SECONDS=30
   DATA_RETENTION_DAYS=30
   METRICS_RETENTION_DAYS=365
   ```

3. **Code Deployment**
   ```bash
   # Update server.py with persistence
   # Deploy new version with zero-downtime
   docker-compose up -d --build backend
   ```

4. **Monitoring**
   ```bash
   # Monitor MongoDB collections growth
   docker-compose exec mongodb mongosh rugs_tracker --eval "db.stats()"
   
   # Check persistence logs
   docker-compose logs -f backend | grep -i persist
   ```

### Phase 6: Frontend Integration (Week 4)

#### 6.1 Historical Charts Component

```jsx
// frontend/src/components/HistoricalAnalytics.jsx
import React, { useState, useEffect } from 'react';
import { Line, Bar } from 'recharts';

const HistoricalAnalytics = () => {
    const [metrics, setMetrics] = useState(null);
    const [timeRange, setTimeRange] = useState(24); // hours
    
    useEffect(() => {
        fetchMetrics();
    }, [timeRange]);
    
    const fetchMetrics = async () => {
        const response = await fetch(`/api/analytics/performance?hours=${timeRange}`);
        const data = await response.json();
        setMetrics(data);
    };
    
    return (
        <div className="analytics-panel">
            <div className="controls">
                <select onChange={(e) => setTimeRange(e.target.value)}>
                    <option value="24">Last 24 Hours</option>
                    <option value="168">Last Week</option>
                    <option value="720">Last Month</option>
                </select>
            </div>
            
            {metrics && (
                <>
                    <div className="metric-card">
                        <h3>Prediction Accuracy</h3>
                        <Line 
                            data={metrics.prediction_metrics.hourly}
                            dataKey="within_2_windows"
                            stroke="#10b981"
                        />
                    </div>
                    
                    <div className="metric-card">
                        <h3>E40 Bias Trend</h3>
                        <Line 
                            data={metrics.prediction_metrics.hourly}
                            dataKey="median_e40"
                            stroke="#3b82f6"
                            referenceLineY={0}
                        />
                    </div>
                    
                    <div className="metric-card">
                        <h3>Side Bet ROI</h3>
                        <Bar 
                            data={metrics.sidebet_metrics.hourly}
                            dataKey="roi_percentage"
                            fill="#8b5cf6"
                        />
                    </div>
                </>
            )}
        </div>
    );
};
```

## Testing Strategy

### Unit Tests
```python
# tests/unit/test_persistence.py
import pytest
from backend.repositories import GameRepository
from backend.models.storage import GameRecord

@pytest.mark.asyncio
async def test_save_game_record(mock_db):
    repo = GameRepository(mock_db)
    game = GameRecord(
        game_id="test_123",
        start_tick=0,
        peak_price=1.5,
        peak_tick=10
    )
    
    result = await repo.save_game(game)
    assert result == "test_123"
    
    # Verify saved
    saved = await repo.games.find_one({"game_id": "test_123"})
    assert saved["peak_price"] == 1.5
```

### Integration Tests
```python
# tests/integration/test_persistence_integration.py
@pytest.mark.asyncio
async def test_end_to_end_persistence(test_tracker, test_repo):
    # Simulate game lifecycle
    await test_tracker.on_game_update({
        "event": "gameStart",
        "gameId": "test_game",
        "tick": 0,
        "price": 1.0
    })
    
    # Make prediction
    await test_tracker.make_prediction("test_game", 50, {...})
    
    # End game
    await test_tracker.on_game_update({
        "event": "gameEnd",
        "gameId": "test_game",
        "tick": 280,
        "finalPrice": 5.2
    })
    
    # Verify persistence
    game = await test_repo.games.find_one({"game_id": "test_game"})
    assert game["duration_ticks"] == 280
    
    predictions = await test_repo.predictions.find({"game_id": "test_game"}).to_list(None)
    assert len(predictions) > 0
    assert predictions[0]["actual_end_tick"] == 280
```

## Performance Considerations

### Storage Estimates
- **Games**: ~500 games/day × 1KB = 0.5MB/day = 15MB/month
- **Predictions**: ~2000 predictions/day × 0.5KB = 1MB/day = 30MB/month  
- **Side Bets**: ~1000 bets/day × 0.3KB = 0.3MB/day = 9MB/month
- **Tick Samples**: ~50K samples/day × 0.2KB = 10MB/day = 300MB/month
- **Total**: ~350MB/month growth rate

### Query Performance
- All critical queries use indexes
- Aggregation pipelines optimized for common patterns
- Consider read replicas for analytics if load increases

### Backup Strategy
- Daily mongodump backups
- Weekly full backups to S3
- Point-in-time recovery with oplog

## Rollback Plan

If issues arise:
1. Set `PERSISTENCE_ENABLED=false` in environment
2. Server continues with in-memory only operation
3. Fix issues and re-enable
4. Run migration to catch up missed data from logs

## Success Metrics

1. **Week 1**: Schema deployed, indexes created
2. **Week 2**: Repository layer integrated, 0% data loss
3. **Week 3**: Analytics API live, <100ms query times
4. **Week 4**: Full system operational, frontend showing historical data
5. **Month 1**: 30 days of historical data accumulated
6. **Month 3**: Pattern analysis showing improvement trends

## Next Steps

1. Review and approve plan
2. Create feature branch `feature/persistent-storage`
3. Implement Phase 1 (Schema Design)
4. Test in development environment
5. Deploy to staging for validation
6. Production rollout with monitoring

---

*This plan enables the TED system to maintain full historical records while preserving the real-time performance characteristics of the current in-memory architecture.*