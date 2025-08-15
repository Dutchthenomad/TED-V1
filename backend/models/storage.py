"""
Pydantic models for persistent storage in MongoDB.
These models define the schema for game data, predictions, and metrics.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class SideBetRecommendation(str, Enum):
    """Side bet recommendation types"""
    BET = "BET"
    SKIP = "SKIP"
    WAIT = "WAIT"


class SideBetOutcome(str, Enum):
    """Side bet outcome status"""
    WON = "WON"
    LOST = "LOST"
    PENDING = "PENDING"


class GameRecord(BaseModel):
    """Complete game record for MongoDB storage"""
    game_id: str
    start_tick: int
    end_tick: Optional[int] = None
    duration_ticks: Optional[int] = None
    peak_price: float
    peak_tick: int
    final_price: Optional[float] = None
    treasury_remainder: Optional[int] = None
    patterns_detected: List[str] = Field(default_factory=list)
    had_predictions: bool = False
    prediction_accuracy: Optional[float] = None
    side_bets_placed: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PredictionRecord(BaseModel):
    """Prediction record with features and outcomes"""
    game_id: str
    predicted_at_tick: int
    predicted_end_tick: int
    actual_end_tick: Optional[int] = None
    confidence: float
    uncertainty_bounds: Dict[str, float] = Field(
        default_factory=lambda: {"lower": 0, "upper": 0}
    )
    features_used: Dict[str, Any] = Field(default_factory=dict)
    error_metrics: Optional[Dict[str, float]] = None
    model_version: str = "v2.1.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def calculate_error_metrics(self, actual_tick: int) -> Dict[str, float]:
        """Calculate error metrics when outcome is known"""
        raw_error = self.predicted_end_tick - actual_tick
        signed_error = raw_error  # Preserves direction
        e40 = raw_error / 40.0  # Window normalized error
        within_windows = abs(raw_error) // 40
        
        return {
            "raw_error": raw_error,
            "signed_error": signed_error,
            "e40": e40,
            "within_windows": within_windows,
            "absolute_error": abs(raw_error)
        }
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SideBetRecord(BaseModel):
    """Side bet recommendation and outcome"""
    game_id: str
    placed_at_tick: int
    window_end_tick: int  # placed_at + 40
    probability: float
    expected_value: float
    confidence: float
    recommendation: SideBetRecommendation
    actual_outcome: SideBetOutcome = SideBetOutcome.PENDING
    payout: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    def calculate_payout(self, game_end_tick: int) -> float:
        """Calculate payout based on game outcome"""
        if game_end_tick <= self.window_end_tick:
            self.actual_outcome = SideBetOutcome.WON
            return 5.0  # 5x payout
        else:
            self.actual_outcome = SideBetOutcome.LOST
            return -1.0  # Lost bet
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HourlyMetrics(BaseModel):
    """Aggregated hourly performance metrics"""
    hour_start: datetime
    hour_end: datetime
    games_analyzed: int = 0
    predictions_made: int = 0
    
    # Prediction metrics
    prediction_metrics: Dict[str, float] = Field(
        default_factory=lambda: {
            "median_e40": 0.0,
            "mean_absolute_error": 0.0,
            "within_1_window": 0.0,
            "within_2_windows": 0.0,
            "within_3_windows": 0.0
        }
    )
    
    # Side bet metrics
    side_bet_metrics: Dict[str, float] = Field(
        default_factory=lambda: {
            "total_recommended": 0,
            "positive_ev_count": 0,
            "bets_won": 0,
            "bets_lost": 0,
            "total_ev": 0.0,
            "roi_percentage": 0.0
        }
    )
    
    # System metrics
    system_metrics: Dict[str, float] = Field(
        default_factory=lambda: {
            "avg_latency_ms": 0.0,
            "websocket_disconnects": 0,
            "errors_logged": 0
        }
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TickSample(BaseModel):
    """Sampled tick data for detailed analysis"""
    game_id: str
    tick: int
    price: float
    features: Dict[str, float] = Field(default_factory=dict)
    timestamp: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PersistenceStatus(BaseModel):
    """Track persistence system status"""
    enabled: bool = False
    last_save: Optional[datetime] = None
    records_pending: int = 0
    records_saved_total: int = 0
    last_error: Optional[str] = None
    error_count: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }