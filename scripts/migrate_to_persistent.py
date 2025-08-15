#!/usr/bin/env python3
"""
Migration script to initialize MongoDB for persistent storage.
Creates indexes and validates database setup.

Usage:
    python scripts/migrate_to_persistent.py [--check-only]
"""

import asyncio
import os
import sys
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import logging
import argparse

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from dotenv import load_dotenv

# Load environment - try backend/.env first, then current directory
env_path = Path(__file__).parent.parent / "backend" / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PersistenceMigration:
    """Handle database setup and migration for persistence"""
    
    def __init__(self, mongo_url: str, db_name: str):
        self.client = AsyncIOMotorClient(mongo_url)
        self.db = self.client[db_name]
        self.collections_created = []
        self.indexes_created = []
    
    async def check_connection(self) -> bool:
        """Verify MongoDB connection"""
        try:
            # Ping the server
            await self.client.admin.command('ping')
            logger.info("✓ MongoDB connection successful")
            return True
        except Exception as e:
            logger.error(f"✗ MongoDB connection failed: {e}")
            return False
    
    async def create_collections(self) -> bool:
        """Create required collections if they don't exist"""
        try:
            existing = await self.db.list_collection_names()
            
            required_collections = [
                "games",
                "predictions", 
                "side_bets",
                "metrics_hourly",
                "tick_samples"
            ]
            
            for collection in required_collections:
                if collection not in existing:
                    await self.db.create_collection(collection)
                    self.collections_created.append(collection)
                    logger.info(f"✓ Created collection: {collection}")
                else:
                    logger.info(f"  Collection exists: {collection}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error creating collections: {e}")
            return False
    
    async def create_indexes(self) -> bool:
        """Create all required indexes for optimal performance"""
        try:
            # Games collection indexes
            games_indexes = [
                ("game_id", {"unique": True}),
                ([("created_at", -1)], {}),
                ([("duration_ticks", 1)], {}),
                ([("created_at", -1), ("had_predictions", 1)], {})
            ]
            
            for index_spec in games_indexes:
                if isinstance(index_spec[0], str):
                    index_name = await self.db.games.create_index(index_spec[0], **index_spec[1])
                else:
                    index_name = await self.db.games.create_index(index_spec[0], **index_spec[1])
                self.indexes_created.append(f"games.{index_name}")
            
            logger.info("✓ Created indexes for games collection")
            
            # Predictions collection indexes
            pred_indexes = [
                ("game_id", {}),
                ([("created_at", -1)], {}),
                ([("game_id", 1), ("predicted_at_tick", 1)], {}),
                ("error_metrics.e40", {})
            ]
            
            for index_spec in pred_indexes:
                if isinstance(index_spec[0], str):
                    index_name = await self.db.predictions.create_index(index_spec[0], **index_spec[1])
                else:
                    index_name = await self.db.predictions.create_index(index_spec[0], **index_spec[1])
                self.indexes_created.append(f"predictions.{index_name}")
            
            logger.info("✓ Created indexes for predictions collection")
            
            # Side bets collection indexes
            bet_indexes = [
                ("game_id", {}),
                ([("created_at", -1)], {}),
                ([("game_id", 1), ("placed_at_tick", 1)], {}),
                ("actual_outcome", {})
            ]
            
            for index_spec in bet_indexes:
                if isinstance(index_spec[0], str):
                    index_name = await self.db.side_bets.create_index(index_spec[0], **index_spec[1])
                else:
                    index_name = await self.db.side_bets.create_index(index_spec[0], **index_spec[1])
                self.indexes_created.append(f"side_bets.{index_name}")
            
            logger.info("✓ Created indexes for side_bets collection")
            
            # Metrics collection indexes
            metrics_indexes = [
                ([("hour_start", -1)], {}),
                ([("hour_start", -1), ("hour_end", -1)], {})
            ]
            
            for index_spec in metrics_indexes:
                index_name = await self.db.metrics_hourly.create_index(index_spec[0], **index_spec[1])
                self.indexes_created.append(f"metrics_hourly.{index_name}")
            
            logger.info("✓ Created indexes for metrics_hourly collection")
            
            # Tick samples collection indexes
            tick_indexes = [
                ([("game_id", 1), ("tick", 1)], {"unique": True}),
                ([("created_at", -1)], {})
            ]
            
            for index_spec in tick_indexes:
                index_name = await self.db.tick_samples.create_index(index_spec[0], **index_spec[1])
                self.indexes_created.append(f"tick_samples.{index_name}")
            
            logger.info("✓ Created indexes for tick_samples collection")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Error creating indexes: {e}")
            return False
    
    async def verify_setup(self) -> bool:
        """Verify database is properly set up"""
        try:
            # Check collections exist
            collections = await self.db.list_collection_names()
            required = ["games", "predictions", "side_bets", "metrics_hourly", "tick_samples"]
            
            missing = set(required) - set(collections)
            if missing:
                logger.warning(f"Missing collections: {missing}")
                return False
            
            # Check indexes
            for collection_name in required:
                collection = self.db[collection_name]
                indexes = await collection.list_indexes().to_list(None)
                logger.info(f"  {collection_name}: {len(indexes)} indexes")
            
            # Test write/read
            test_doc = {"test": True, "timestamp": datetime.utcnow()}
            result = await self.db.games.insert_one(test_doc)
            await self.db.games.delete_one({"_id": result.inserted_id})
            
            logger.info("✓ Database verification complete")
            return True
            
        except Exception as e:
            logger.error(f"✗ Database verification failed: {e}")
            return False
    
    async def get_stats(self) -> dict:
        """Get current database statistics"""
        stats = {}
        
        try:
            # Get collection counts
            stats["games"] = await self.db.games.count_documents({})
            stats["predictions"] = await self.db.predictions.count_documents({})
            stats["side_bets"] = await self.db.side_bets.count_documents({})
            stats["metrics_hourly"] = await self.db.metrics_hourly.count_documents({})
            stats["tick_samples"] = await self.db.tick_samples.count_documents({})
            
            # Get database size
            db_stats = await self.db.command("dbStats")
            stats["db_size_mb"] = round(db_stats.get("dataSize", 0) / (1024 * 1024), 2)
            stats["index_size_mb"] = round(db_stats.get("indexSize", 0) / (1024 * 1024), 2)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}
    
    async def close(self):
        """Close database connection"""
        self.client.close()


async def main(check_only: bool = False):
    """Main migration function"""
    
    # Get configuration
    mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017/rugs_tracker")
    db_name = os.getenv("DB_NAME", "rugs_tracker")
    
    # Extract DB name from URL if not specified
    if "/" in mongo_url and not db_name:
        db_name = mongo_url.split("/")[-1].split("?")[0]
    
    logger.info("=" * 60)
    logger.info("TED System - Persistence Migration")
    logger.info("=" * 60)
    logger.info(f"MongoDB URL: {mongo_url.split('@')[-1] if '@' in mongo_url else mongo_url}")
    logger.info(f"Database: {db_name}")
    logger.info("")
    
    # Create migration handler
    migration = PersistenceMigration(mongo_url, db_name)
    
    # Check connection
    if not await migration.check_connection():
        logger.error("Cannot proceed without database connection")
        await migration.close()
        return False
    
    if check_only:
        # Just verify current state
        logger.info("\n--- Verification Mode ---")
        success = await migration.verify_setup()
        
        if success:
            stats = await migration.get_stats()
            logger.info("\n--- Database Statistics ---")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
    else:
        # Perform migration
        logger.info("\n--- Creating Collections ---")
        if not await migration.create_collections():
            await migration.close()
            return False
        
        logger.info("\n--- Creating Indexes ---")
        if not await migration.create_indexes():
            await migration.close()
            return False
        
        logger.info("\n--- Verifying Setup ---")
        success = await migration.verify_setup()
        
        if success:
            stats = await migration.get_stats()
            logger.info("\n--- Database Statistics ---")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")
            
            logger.info("\n" + "=" * 60)
            logger.info("✓ Migration completed successfully!")
            logger.info("=" * 60)
            logger.info("\nNext steps:")
            logger.info("1. Set PERSISTENCE_ENABLED=true in your .env file")
            logger.info("2. Restart the TED backend server")
            logger.info("3. Monitor logs for persistence activity")
        else:
            logger.error("\n✗ Migration failed - please check errors above")
    
    await migration.close()
    return success


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize MongoDB for TED persistence")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only verify setup without making changes"
    )
    
    args = parser.parse_args()
    
    # Run migration
    success = asyncio.run(main(check_only=args.check_only))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)