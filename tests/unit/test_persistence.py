"""
Unit tests for persistence layer.
Tests data models, repository operations, and rollback safety.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.models.storage import (
    GameRecord, PredictionRecord, SideBetRecord,
    HourlyMetrics, TickSample, SideBetRecommendation, SideBetOutcome
)
from backend.repositories.game_repository import GameRepository


class TestDataModels:
    """Test Pydantic data models"""
    
    def test_game_record_creation(self):
        """Test GameRecord model creation"""
        game = GameRecord(
            game_id="test_123",
            start_tick=0,
            peak_price=1.5,
            peak_tick=10
        )
        
        assert game.game_id == "test_123"
        assert game.start_tick == 0
        assert game.peak_price == 1.5
        assert game.peak_tick == 10
        assert game.end_tick is None
        assert game.had_predictions is False
        assert len(game.patterns_detected) == 0
    
    def test_prediction_error_calculation(self):
        """Test prediction error metrics calculation"""
        pred = PredictionRecord(
            game_id="test_123",
            predicted_at_tick=50,
            predicted_end_tick=200,
            confidence=0.7
        )
        
        # Calculate error metrics
        metrics = pred.calculate_error_metrics(actual_tick=280)
        
        assert metrics["raw_error"] == -80  # 200 - 280
        assert metrics["signed_error"] == -80
        assert metrics["e40"] == -2.0  # -80 / 40
        assert metrics["within_windows"] == 2  # abs(-80) // 40
        assert metrics["absolute_error"] == 80
    
    def test_side_bet_payout_calculation(self):
        """Test side bet payout calculation"""
        bet = SideBetRecord(
            game_id="test_123",
            placed_at_tick=100,
            window_end_tick=140,
            probability=0.25,
            expected_value=0.25,
            confidence=0.6,
            recommendation=SideBetRecommendation.BET
        )
        
        # Test win scenario
        payout = bet.calculate_payout(game_end_tick=130)
        assert payout == 5.0
        assert bet.actual_outcome == SideBetOutcome.WON
        
        # Reset and test loss scenario
        bet.actual_outcome = SideBetOutcome.PENDING
        payout = bet.calculate_payout(game_end_tick=141)
        assert payout == -1.0
        assert bet.actual_outcome == SideBetOutcome.LOST


@pytest.mark.asyncio
class TestGameRepository:
    """Test repository operations"""
    
    @pytest.fixture
    async def mock_db(self):
        """Create mock database"""
        db = MagicMock()
        db.games = AsyncMock()
        db.predictions = AsyncMock()
        db.side_bets = AsyncMock()
        db.metrics_hourly = AsyncMock()
        db.tick_samples = AsyncMock()
        return db
    
    async def test_persistence_disabled(self, mock_db):
        """Test that operations are no-ops when persistence is disabled"""
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "false"}):
            repo = GameRepository(mock_db)
            
            assert repo.persistence_enabled is False
            
            # Try to save a game
            game = GameRecord(game_id="test", start_tick=0, peak_price=1.0, peak_tick=0)
            result = await repo.save_game(game)
            
            assert result is None
            mock_db.games.update_one.assert_not_called()
    
    async def test_save_game_with_persistence(self, mock_db):
        """Test saving game with persistence enabled"""
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "true"}):
            repo = GameRepository(mock_db)
            
            assert repo.persistence_enabled is True
            
            # Mock the update_one response
            mock_db.games.update_one.return_value = MagicMock(upserted_id="123")
            
            # Save a game
            game = GameRecord(game_id="test_456", start_tick=0, peak_price=1.0, peak_tick=0)
            result = await repo.save_game(game)
            
            assert result == "test_456"
            mock_db.games.update_one.assert_called_once()
            
            # Check the call arguments
            call_args = mock_db.games.update_one.call_args
            assert call_args[0][0] == {"game_id": "test_456"}  # filter
            assert "$set" in call_args[0][1]  # update operation
            assert call_args[1]["upsert"] is True  # upsert flag
    
    async def test_update_prediction_outcome(self, mock_db):
        """Test updating predictions with actual outcomes"""
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "true"}):
            repo = GameRepository(mock_db)
            
            # Mock finding predictions
            mock_predictions = [
                {
                    "_id": "pred1",
                    "game_id": "test_game",
                    "predicted_end_tick": 200,
                    "actual_end_tick": None
                },
                {
                    "_id": "pred2", 
                    "game_id": "test_game",
                    "predicted_end_tick": 250,
                    "actual_end_tick": None
                }
            ]
            
            mock_cursor = AsyncMock()
            mock_cursor.to_list.return_value = mock_predictions
            mock_db.predictions.find.return_value = mock_cursor
            
            # Update predictions
            await repo.update_prediction_outcome("test_game", actual_tick=280)
            
            # Should have updated both predictions
            assert mock_db.predictions.update_one.call_count == 2
            
            # Check first update call
            first_call = mock_db.predictions.update_one.call_args_list[0]
            update_data = first_call[0][1]["$set"]
            assert update_data["actual_end_tick"] == 280
            assert update_data["error_metrics"]["raw_error"] == -80  # 200 - 280
            assert update_data["error_metrics"]["e40"] == -2.0
    
    async def test_batch_tick_sample_save(self, mock_db):
        """Test batch saving of tick samples"""
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "true"}):
            repo = GameRepository(mock_db)
            
            # Create sample data
            samples = [
                TickSample(
                    game_id="game1",
                    tick=100,
                    price=1.5,
                    features={"volatility": 0.1},
                    timestamp=datetime.utcnow()
                ),
                TickSample(
                    game_id="game1",
                    tick=110,
                    price=1.6,
                    features={"volatility": 0.12},
                    timestamp=datetime.utcnow()
                )
            ]
            
            # Mock bulk write response
            mock_result = MagicMock()
            mock_result.upserted_count = 2
            mock_result.modified_count = 0
            mock_db.tick_samples.bulk_write.return_value = mock_result
            
            # Save samples
            count = await repo.save_tick_samples_batch(samples)
            
            assert count == 2
            mock_db.tick_samples.bulk_write.assert_called_once()
            
            # Check bulk operations
            operations = mock_db.tick_samples.bulk_write.call_args[0][0]
            assert len(operations) == 2
            assert operations[0]["update_one"]["filter"]["game_id"] == "game1"
            assert operations[0]["update_one"]["filter"]["tick"] == 100
    
    async def test_cleanup_old_data(self, mock_db):
        """Test data retention cleanup"""
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "true"}):
            repo = GameRepository(mock_db)
            
            # Mock delete responses
            mock_db.tick_samples.delete_many.return_value = MagicMock(deleted_count=100)
            mock_db.predictions.delete_many.return_value = MagicMock(deleted_count=50)
            mock_db.side_bets.delete_many.return_value = MagicMock(deleted_count=30)
            mock_db.games.delete_many.return_value = MagicMock(deleted_count=10)
            
            # Run cleanup
            retention_days = {
                "tick_samples": 7,
                "predictions": 90,
                "side_bets": 90,
                "games": 180
            }
            
            deleted = await repo.cleanup_old_data(retention_days)
            
            assert deleted["tick_samples"] == 100
            assert deleted["predictions"] == 50
            assert deleted["side_bets"] == 30
            assert deleted["games"] == 10
            
            # Verify cutoff dates were calculated correctly
            tick_cutoff = mock_db.tick_samples.delete_many.call_args[0][0]["created_at"]["$lt"]
            assert isinstance(tick_cutoff, datetime)
            
            # Should be approximately 7 days ago
            expected_cutoff = datetime.utcnow() - timedelta(days=7)
            time_diff = abs((tick_cutoff - expected_cutoff).total_seconds())
            assert time_diff < 60  # Within 1 minute tolerance


@pytest.mark.asyncio
class TestPersistenceIntegration:
    """Test the main persistence integration"""
    
    async def test_integration_disabled_by_default(self):
        """Test that persistence is disabled by default"""
        from backend.persistence_integration import PersistenceIntegration
        
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "false"}):
            mock_db = MagicMock()
            integration = PersistenceIntegration(mock_db)
            
            assert integration.enabled is False
            assert integration.repo is None
            assert integration.manager is None
            
            # Operations should be no-ops
            await integration.on_game_start("game1", 0, 1.0)
            await integration.on_game_end("game1", 280, 5.0)
            
            # No errors should occur
            status = integration.get_status()
            assert status["enabled"] is False
    
    async def test_integration_can_be_enabled(self):
        """Test that persistence can be enabled via environment"""
        from backend.persistence_integration import PersistenceIntegration
        
        with patch.dict(os.environ, {"PERSISTENCE_ENABLED": "true"}):
            mock_db = MagicMock()
            integration = PersistenceIntegration(mock_db)
            
            assert integration.enabled is True
            assert integration.repo is not None
            
            status = integration.get_status()
            assert status["enabled"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])