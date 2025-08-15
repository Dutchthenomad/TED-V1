#!/usr/bin/env python3
"""
Quick verification script to check if persistence is properly set up.
Run this before starting the server to verify configuration.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

def check_environment():
    """Check environment variables"""
    print("\n📋 Environment Configuration:")
    print("-" * 40)
    
    vars_to_check = [
        ("MONGO_URL", "MongoDB connection string"),
        ("DB_NAME", "Database name"),
        ("PERSISTENCE_ENABLED", "Persistence feature flag"),
        ("PERSISTENCE_INTERVAL_SECONDS", "Save interval"),
        ("PERSISTENCE_BATCH_SIZE", "Batch size"),
    ]
    
    all_good = True
    for var, desc in vars_to_check:
        value = os.getenv(var, "NOT SET")
        if value == "NOT SET":
            print(f"❌ {var}: NOT SET ({desc})")
            all_good = False
        else:
            # Hide sensitive parts of connection string
            display_value = value
            if var == "MONGO_URL" and "@" in value:
                parts = value.split("@")
                display_value = "mongodb://***@" + parts[-1]
            print(f"✓ {var}: {display_value}")
    
    return all_good

def check_imports():
    """Check if all required modules can be imported"""
    print("\n📦 Module Imports:")
    print("-" * 40)
    
    modules_to_check = [
        ("models.storage", "Data models"),
        ("repositories.game_repository", "Repository layer"),
        ("tasks.persistence_manager", "Background tasks"),
        ("persistence_integration", "Integration module"),
    ]
    
    all_good = True
    for module, desc in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module}: OK ({desc})")
        except ImportError as e:
            print(f"❌ {module}: FAILED ({desc})")
            print(f"   Error: {e}")
            all_good = False
    
    return all_good

def check_mongodb_connection():
    """Check MongoDB connection"""
    print("\n🗄️  MongoDB Connection:")
    print("-" * 40)
    
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def test_connection():
            mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
            client = AsyncIOMotorClient(mongo_url)
            
            try:
                # Ping the server
                await client.admin.command('ping')
                print(f"✓ MongoDB connection successful")
                
                # List databases
                dbs = await client.list_database_names()
                print(f"✓ Available databases: {', '.join(dbs[:5])}")
                
                # Check our database
                db_name = os.getenv("DB_NAME", "rugs_tracker")
                if db_name in dbs:
                    db = client[db_name]
                    collections = await db.list_collection_names()
                    print(f"✓ Database '{db_name}' exists with {len(collections)} collections")
                else:
                    print(f"ℹ️  Database '{db_name}' does not exist yet (will be created)")
                
                client.close()
                return True
                
            except Exception as e:
                print(f"❌ MongoDB connection failed: {e}")
                client.close()
                return False
        
        return asyncio.run(test_connection())
        
    except Exception as e:
        print(f"❌ Could not test MongoDB: {e}")
        return False

def check_persistence_status():
    """Check persistence system status"""
    print("\n⚙️  Persistence System Status:")
    print("-" * 40)
    
    enabled = os.getenv("PERSISTENCE_ENABLED", "false").lower() == "true"
    
    if enabled:
        print("✓ Persistence is ENABLED")
        print("  - Data will be saved to MongoDB")
        print("  - Background tasks will run")
        print("  - Historical data will accumulate")
    else:
        print("ℹ️  Persistence is DISABLED")
        print("  - Running in memory-only mode")
        print("  - No data will be saved to MongoDB")
        print("  - Set PERSISTENCE_ENABLED=true to enable")
    
    return True

def main():
    """Main verification"""
    print("=" * 50)
    print("TED System - Persistence Setup Verification")
    print("=" * 50)
    
    checks = []
    
    # Run checks
    checks.append(("Environment", check_environment()))
    checks.append(("Imports", check_imports()))
    checks.append(("MongoDB", check_mongodb_connection()))
    checks.append(("Status", check_persistence_status()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Summary:")
    print("-" * 50)
    
    all_passed = True
    for name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:15} {status}")
        if not passed:
            all_passed = False
    
    print("=" * 50)
    
    if all_passed:
        print("\n✅ System is ready!")
        print("\nNext steps:")
        print("1. Run migration: python scripts/migrate_to_persistent.py")
        print("2. Enable persistence: export PERSISTENCE_ENABLED=true")
        print("3. Start server: python backend/server.py")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("\nTroubleshooting:")
        print("1. Check .env file exists and has required variables")
        print("2. Ensure MongoDB is running")
        print("3. Verify all Python packages are installed")
        return 1

if __name__ == "__main__":
    sys.exit(main())