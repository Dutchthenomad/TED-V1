#!/usr/bin/env python3
"""
Simple test to verify persistence system functionality.
Tests both enabled and disabled states without complex imports.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Load environment
from dotenv import load_dotenv
env_path = Path(__file__).parent / "backend" / ".env"
load_dotenv(env_path)

print("=" * 60)
print("TED Persistence System - Simple Test")
print("=" * 60)

async def test_disabled():
    """Test with persistence disabled"""
    print("\n1. Testing with PERSISTENCE_ENABLED=false")
    print("-" * 40)
    
    os.environ["PERSISTENCE_ENABLED"] = "false"
    
    from repositories.game_repository import GameRepository
    from models.storage import GameRecord
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client["rugs_tracker_test"]
    
    # Create repository
    repo = GameRepository(db)
    
    print(f"✓ Repository created")
    print(f"  Enabled: {repo.persistence_enabled}")
    
    # Try to save a game
    game = GameRecord(
        game_id="test_disabled_001",
        start_tick=0,
        peak_price=1.0,
        peak_tick=0
    )
    
    result = await repo.save_game(game)
    print(f"  Save result: {result}")
    
    # Check if anything was saved
    count = await db.games.count_documents({"game_id": "test_disabled_001"})
    print(f"  Documents in DB: {count}")
    
    if result is None and count == 0:
        print("✓ PASS: No data saved when disabled")
    else:
        print("✗ FAIL: Data was saved when it shouldn't be")
    
    client.close()
    return result is None

async def test_enabled():
    """Test with persistence enabled"""
    print("\n2. Testing with PERSISTENCE_ENABLED=true")
    print("-" * 40)
    
    os.environ["PERSISTENCE_ENABLED"] = "true"
    
    from repositories.game_repository import GameRepository
    from models.storage import GameRecord, PredictionRecord
    from motor.motor_asyncio import AsyncIOMotorClient
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client["rugs_tracker_test"]
    
    # Create repository
    repo = GameRepository(db)
    
    print(f"✓ Repository created")
    print(f"  Enabled: {repo.persistence_enabled}")
    
    # Initialize indexes
    await repo.initialize_indexes()
    print("✓ Indexes initialized")
    
    # Save a game
    game = GameRecord(
        game_id="test_enabled_001",
        start_tick=0,
        peak_price=1.0,
        peak_tick=0
    )
    
    result = await repo.save_game(game)
    print(f"  Save result: {result}")
    
    # Check if it was saved
    saved_game = await db.games.find_one({"game_id": "test_enabled_001"})
    
    if saved_game:
        print(f"✓ Game saved: {saved_game['game_id']}")
    else:
        print("✗ Game not found in database")
    
    # Save a prediction
    pred = PredictionRecord(
        game_id="test_enabled_001",
        predicted_at_tick=50,
        predicted_end_tick=280,
        confidence=0.75
    )
    
    pred_result = await repo.save_prediction(pred)
    print(f"✓ Prediction saved: {pred_result}")
    
    # Update game end
    await repo.update_game_end("test_enabled_001", 290, 5.2)
    
    # Update prediction outcome
    await repo.update_prediction_outcome("test_enabled_001", 290)
    
    # Check updates
    updated_game = await db.games.find_one({"game_id": "test_enabled_001"})
    updated_pred = await db.predictions.find_one({"game_id": "test_enabled_001"})
    
    if updated_game and updated_game.get("end_tick") == 290:
        print(f"✓ Game end updated: tick {updated_game['end_tick']}")
    
    if updated_pred and updated_pred.get("error_metrics"):
        print(f"✓ Prediction metrics calculated: E40 = {updated_pred['error_metrics']['e40']}")
    
    # Cleanup test data
    await db.games.delete_many({"game_id": {"$regex": "^test_"}})
    await db.predictions.delete_many({"game_id": {"$regex": "^test_"}})
    
    client.close()
    return saved_game is not None

async def test_rollback():
    """Test rollback scenario"""
    print("\n3. Testing Rollback (enabled → disabled)")
    print("-" * 40)
    
    from repositories.game_repository import GameRepository
    from models.storage import GameRecord
    from motor.motor_asyncio import AsyncIOMotorClient
    
    client = AsyncIOMotorClient(os.getenv("MONGO_URL"))
    db = client["rugs_tracker_test"]
    
    # Start enabled
    os.environ["PERSISTENCE_ENABLED"] = "true"
    repo1 = GameRepository(db)
    print(f"  Initial state: Enabled = {repo1.persistence_enabled}")
    
    # Save a game
    game1 = GameRecord(game_id="test_rollback_001", start_tick=0, peak_price=1.0, peak_tick=0)
    result1 = await repo1.save_game(game1)
    print(f"  Saved game while enabled: {result1}")
    
    # Simulate rollback
    os.environ["PERSISTENCE_ENABLED"] = "false"
    repo2 = GameRepository(db)
    print(f"  After rollback: Enabled = {repo2.persistence_enabled}")
    
    # Try to save another game
    game2 = GameRecord(game_id="test_rollback_002", start_tick=0, peak_price=1.0, peak_tick=0)
    result2 = await repo2.save_game(game2)
    print(f"  Save attempt after rollback: {result2}")
    
    # Check what's in DB
    count = await db.games.count_documents({"game_id": {"$regex": "^test_rollback_"}})
    print(f"  Games in DB: {count}")
    
    # Cleanup
    await db.games.delete_many({"game_id": {"$regex": "^test_rollback_"}})
    
    client.close()
    
    if count == 1 and result2 is None:
        print("✓ PASS: Rollback works correctly")
        return True
    else:
        print("✗ FAIL: Rollback didn't work as expected")
        return False

async def main():
    """Run all tests"""
    results = []
    
    try:
        # Test disabled mode
        results.append(("Disabled Mode", await test_disabled()))
        
        # Test enabled mode
        results.append(("Enabled Mode", await test_enabled()))
        
        # Test rollback
        results.append(("Rollback", await test_rollback()))
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{name:20} {status}")
    
    print("-" * 60)
    print(f"Total: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Persistence system is working correctly.")
        return True
    else:
        print(f"\n❌ {failed} tests failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)