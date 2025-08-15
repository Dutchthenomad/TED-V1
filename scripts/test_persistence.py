#!/usr/bin/env python3
"""
Test script to verify persistence system is working correctly.
This script tests both enabled and disabled states.
"""

import asyncio
import os
import sys
from pathlib import Path
import logging
from datetime import datetime
import json

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PersistenceTestSuite:
    """Test suite for persistence functionality"""
    
    def __init__(self):
        self.mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/rugs_tracker")
        self.db_name = os.getenv("DB_NAME", "rugs_tracker_test")  # Use test DB
        self.client = None
        self.db = None
        self.test_results = []
    
    async def setup(self):
        """Setup test environment"""
        try:
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            logger.info(f"✓ Connected to MongoDB: {self.db_name}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to connect to MongoDB: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup test data"""
        try:
            # Clean test collections
            await self.db.games.delete_many({"game_id": {"$regex": "^test_"}})
            await self.db.predictions.delete_many({"game_id": {"$regex": "^test_"}})
            await self.db.side_bets.delete_many({"game_id": {"$regex": "^test_"}})
            logger.info("✓ Cleaned up test data")
        except Exception as e:
            logger.error(f"✗ Cleanup failed: {e}")
        finally:
            if self.client:
                self.client.close()
    
    async def test_persistence_disabled(self):
        """Test that system works with persistence disabled"""
        test_name = "Persistence Disabled Mode"
        try:
            # Set persistence disabled
            os.environ["PERSISTENCE_ENABLED"] = "false"
            
            from repositories.game_repository import GameRepository
            from models.storage import GameRecord
            
            repo = GameRepository(self.db)
            
            # Should be disabled
            assert repo.persistence_enabled is False, "Repository should be disabled"
            
            # Operations should return None
            game = GameRecord(
                game_id="test_disabled_001",
                start_tick=0,
                peak_price=1.0,
                peak_tick=0
            )
            result = await repo.save_game(game)
            assert result is None, "Save should return None when disabled"
            
            # Verify nothing was saved
            count = await self.db.games.count_documents({"game_id": "test_disabled_001"})
            assert count == 0, "No data should be saved when disabled"
            
            self.test_results.append((test_name, "PASSED"))
            logger.info(f"✓ {test_name}: PASSED")
            return True
            
        except AssertionError as e:
            self.test_results.append((test_name, f"FAILED: {e}"))
            logger.error(f"✗ {test_name}: {e}")
            return False
        except Exception as e:
            self.test_results.append((test_name, f"ERROR: {e}"))
            logger.error(f"✗ {test_name}: Unexpected error: {e}")
            return False
    
    async def test_persistence_enabled(self):
        """Test that persistence works when enabled"""
        test_name = "Persistence Enabled Mode"
        try:
            # Set persistence enabled
            os.environ["PERSISTENCE_ENABLED"] = "true"
            
            from repositories.game_repository import GameRepository
            from models.storage import GameRecord, PredictionRecord, SideBetRecord
            
            repo = GameRepository(self.db)
            
            # Initialize indexes
            await repo.initialize_indexes()
            
            # Should be enabled
            assert repo.persistence_enabled is True, "Repository should be enabled"
            
            # Test saving a game
            game = GameRecord(
                game_id="test_enabled_001",
                start_tick=0,
                peak_price=1.0,
                peak_tick=0
            )
            result = await repo.save_game(game)
            assert result == "test_enabled_001", "Save should return game_id"
            
            # Verify it was saved
            saved_game = await self.db.games.find_one({"game_id": "test_enabled_001"})
            assert saved_game is not None, "Game should be saved"
            assert saved_game["peak_price"] == 1.0, "Game data should match"
            
            # Test saving a prediction
            prediction = PredictionRecord(
                game_id="test_enabled_001",
                predicted_at_tick=50,
                predicted_end_tick=280,
                confidence=0.7
            )
            pred_id = await repo.save_prediction(prediction)
            assert pred_id is not None, "Prediction should be saved"
            
            # Test updating game end
            await repo.update_game_end("test_enabled_001", 290, 5.2)
            
            # Verify game was updated
            updated_game = await self.db.games.find_one({"game_id": "test_enabled_001"})
            assert updated_game["end_tick"] == 290, "End tick should be updated"
            assert updated_game["final_price"] == 5.2, "Final price should be updated"
            
            # Test prediction outcome update
            await repo.update_prediction_outcome("test_enabled_001", 290)
            
            # Verify prediction was updated
            updated_pred = await self.db.predictions.find_one({"game_id": "test_enabled_001"})
            assert updated_pred["actual_end_tick"] == 290, "Actual tick should be set"
            assert updated_pred["error_metrics"] is not None, "Error metrics should be calculated"
            assert updated_pred["error_metrics"]["raw_error"] == -10, "Error should be -10"
            
            self.test_results.append((test_name, "PASSED"))
            logger.info(f"✓ {test_name}: PASSED")
            return True
            
        except AssertionError as e:
            self.test_results.append((test_name, f"FAILED: {e}"))
            logger.error(f"✗ {test_name}: {e}")
            return False
        except Exception as e:
            self.test_results.append((test_name, f"ERROR: {e}"))
            logger.error(f"✗ {test_name}: Unexpected error: {e}")
            return False
    
    async def test_integration(self):
        """Test the integration module"""
        test_name = "Integration Module"
        try:
            os.environ["PERSISTENCE_ENABLED"] = "true"
            
            from persistence_integration import PersistenceIntegration
            
            # Create integration
            integration = PersistenceIntegration(self.db)
            
            assert integration.enabled is True, "Integration should be enabled"
            assert integration.repo is not None, "Repository should be initialized"
            
            # Test game lifecycle
            await integration.on_game_start("test_integration_001", 0, 1.0)
            await integration.on_prediction_made(
                "test_integration_001", 100, 280, 0.75,
                {"lower": 240, "upper": 320},
                {"epr_active": False}
            )
            await integration.on_side_bet_placed(
                "test_integration_001", 100, 0.22, 0.1, 0.6, "BET"
            )
            await integration.on_game_end("test_integration_001", 275, 4.8)
            
            # Verify data was saved
            game = await self.db.games.find_one({"game_id": "test_integration_001"})
            assert game is not None, "Game should be saved"
            assert game["end_tick"] == 275, "Game should have end data"
            
            pred = await self.db.predictions.find_one({"game_id": "test_integration_001"})
            assert pred is not None, "Prediction should be saved"
            
            bet = await self.db.side_bets.find_one({"game_id": "test_integration_001"})
            assert bet is not None, "Side bet should be saved"
            
            # Test status
            status = integration.get_status()
            assert status["enabled"] is True, "Status should show enabled"
            
            self.test_results.append((test_name, "PASSED"))
            logger.info(f"✓ {test_name}: PASSED")
            return True
            
        except AssertionError as e:
            self.test_results.append((test_name, f"FAILED: {e}"))
            logger.error(f"✗ {test_name}: {e}")
            return False
        except Exception as e:
            self.test_results.append((test_name, f"ERROR: {e}"))
            logger.error(f"✗ {test_name}: Unexpected error: {e}")
            return False
    
    async def test_rollback(self):
        """Test that rollback works correctly"""
        test_name = "Rollback Safety"
        try:
            # Start with enabled
            os.environ["PERSISTENCE_ENABLED"] = "true"
            
            from repositories.game_repository import GameRepository
            from models.storage import GameRecord
            
            repo1 = GameRepository(self.db)
            assert repo1.persistence_enabled is True, "Should start enabled"
            
            # Save a game
            game = GameRecord(
                game_id="test_rollback_001",
                start_tick=0,
                peak_price=1.0,
                peak_tick=0
            )
            result = await repo1.save_game(game)
            assert result is not None, "Should save when enabled"
            
            # Now disable (simulating rollback)
            os.environ["PERSISTENCE_ENABLED"] = "false"
            
            repo2 = GameRepository(self.db)
            assert repo2.persistence_enabled is False, "Should be disabled after rollback"
            
            # Try to save another game
            game2 = GameRecord(
                game_id="test_rollback_002",
                start_tick=0,
                peak_price=1.0,
                peak_tick=0
            )
            result2 = await repo2.save_game(game2)
            assert result2 is None, "Should not save when disabled"
            
            # Verify only first game was saved
            count = await self.db.games.count_documents({"game_id": {"$regex": "^test_rollback_"}})
            assert count == 1, "Only first game should be saved"
            
            self.test_results.append((test_name, "PASSED"))
            logger.info(f"✓ {test_name}: PASSED")
            return True
            
        except AssertionError as e:
            self.test_results.append((test_name, f"FAILED: {e}"))
            logger.error(f"✗ {test_name}: {e}")
            return False
        except Exception as e:
            self.test_results.append((test_name, f"ERROR: {e}"))
            logger.error(f"✗ {test_name}: Unexpected error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests"""
        logger.info("=" * 60)
        logger.info("TED Persistence System - Test Suite")
        logger.info("=" * 60)
        
        if not await self.setup():
            logger.error("Setup failed - cannot run tests")
            return False
        
        # Run tests
        await self.test_persistence_disabled()
        await self.test_persistence_enabled()
        await self.test_integration()
        await self.test_rollback()
        
        # Cleanup
        await self.cleanup()
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        
        passed = 0
        failed = 0
        for test_name, result in self.test_results:
            if result == "PASSED":
                logger.info(f"✓ {test_name}: {result}")
                passed += 1
            else:
                logger.error(f"✗ {test_name}: {result}")
                failed += 1
        
        logger.info("-" * 60)
        logger.info(f"Total: {len(self.test_results)} tests")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        
        if failed == 0:
            logger.info("\n🎉 All tests passed! Persistence system is ready.")
            return True
        else:
            logger.error(f"\n❌ {failed} tests failed. Please check the errors above.")
            return False


async def main():
    """Main test runner"""
    test_suite = PersistenceTestSuite()
    success = await test_suite.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)