# TED System - Persistence Feature Deployment Guide

## Overview

This guide covers the deployment of the new persistent storage feature for the TED system. The feature adds MongoDB-based historical data storage while maintaining full backward compatibility and safe rollback capability.

## Key Features

- **Safe Rollback**: Single environment variable (`PERSISTENCE_ENABLED`) controls entire feature
- **Zero Downtime**: Can be enabled/disabled without restarting the service
- **Backward Compatible**: System continues to work with in-memory storage if persistence fails
- **Automatic Cleanup**: Configurable data retention policies
- **Performance Optimized**: Async background tasks don't impact real-time operations

## Pre-Deployment Checklist

- [ ] MongoDB is installed and accessible
- [ ] Backup of current `.env` file exists
- [ ] Test environment available for validation
- [ ] Monitoring tools ready to check system health

## Deployment Steps

### Step 1: Update Environment Configuration

Add the following to your `.env` file (keep `PERSISTENCE_ENABLED=false` initially):

```bash
# === Persistence Configuration ===

# Master switch for persistence (keep false for initial deploy)
PERSISTENCE_ENABLED=false

# Persistence intervals and batch sizes
PERSISTENCE_INTERVAL_SECONDS=30
PERSISTENCE_BATCH_SIZE=100

# Data retention policies (in days)
TICK_RETENTION_DAYS=7
PREDICTION_RETENTION_DAYS=90
SIDEBET_RETENTION_DAYS=90
GAME_RETENTION_DAYS=180
METRICS_RETENTION_DAYS=365

# Cleanup schedule (hour in UTC when cleanup runs)
CLEANUP_HOUR_UTC=3
```

### Step 2: Run Database Migration

Initialize the MongoDB database with required collections and indexes:

```bash
# Check current database state (dry run)
python scripts/migrate_to_persistent.py --check-only

# Run the actual migration
python scripts/migrate_to_persistent.py

# Expected output:
# ✓ MongoDB connection successful
# ✓ Created collection: games
# ✓ Created collection: predictions
# ✓ Created indexes for all collections
# ✓ Database verification complete
# ✓ Migration completed successfully!
```

### Step 3: Deploy Code Updates

Deploy the new code with persistence disabled:

```bash
# If using Docker
docker-compose build backend
docker-compose up -d backend

# If running locally
# Just restart your server - the new code will load
```

### Step 4: Verify System Health

With persistence still disabled, verify the system is working normally:

```bash
# Check system status
curl http://localhost:8000/api/persistence/status

# Expected response:
{
  "enabled": false,
  "message": "Persistence is disabled"
}

# Verify normal operations continue
curl http://localhost:8000/api/status
```

### Step 5: Enable Persistence

Once confirmed the system is stable, enable persistence:

```bash
# Update .env file
sed -i 's/PERSISTENCE_ENABLED=false/PERSISTENCE_ENABLED=true/' .env

# Restart the backend
docker-compose restart backend
# OR
# Restart your local server
```

### Step 6: Verify Persistence is Active

```bash
# Check persistence status
curl http://localhost:8000/api/persistence/status

# Expected response:
{
  "enabled": true,
  "repository": {
    "enabled": true,
    "last_save": "2024-08-14T10:30:00",
    "records_saved": 42,
    "errors": 0
  },
  "manager": {
    "enabled": true,
    "running": true,
    "persist_interval": 30
  }
}

# Monitor logs for persistence activity
docker-compose logs -f backend | grep -i persist

# You should see:
# "Persistence is ENABLED. Data will be saved to MongoDB."
# "Background persistence tasks started"
# "Persisted: {'predictions': 5, 'side_bets': 3, 'tick_samples': 10}"
```

### Step 7: Validate Data is Being Stored

```bash
# Connect to MongoDB and check data
docker-compose exec mongodb mongosh rugs_tracker

# In MongoDB shell:
db.games.countDocuments()
db.predictions.countDocuments()
db.side_bets.countDocuments()

# Check a recent game
db.games.findOne({}, {game_id: 1, start_tick: 1, end_tick: 1})
```

## Rollback Procedure

If any issues occur, you can immediately disable persistence:

### Quick Rollback (No Restart)

The system will continue running with in-memory storage only:

```bash
# Update .env
sed -i 's/PERSISTENCE_ENABLED=true/PERSISTENCE_ENABLED=false/' .env

# Restart backend
docker-compose restart backend
```

### Full Rollback (If Needed)

```bash
# 1. Disable persistence
sed -i 's/PERSISTENCE_ENABLED=true/PERSISTENCE_ENABLED=false/' .env

# 2. Revert to previous code version (if needed)
git checkout <previous-commit>

# 3. Rebuild and restart
docker-compose build backend
docker-compose up -d backend
```

## Monitoring

### Health Checks

Monitor these endpoints regularly:

```bash
# Overall system status
curl http://localhost:8000/api/status

# Persistence status
curl http://localhost:8000/api/persistence/status

# Recent metrics (last 24 hours)
curl http://localhost:8000/api/persistence/metrics?hours=24
```

### Log Monitoring

Watch for these log patterns:

```bash
# Success patterns
grep "Persisted:" logs/backend.log
grep "Calculated hourly metrics" logs/backend.log

# Error patterns (investigate if found)
grep "Error persisting" logs/backend.log
grep "Error in persist_memory_buffers" logs/backend.log
```

### MongoDB Monitoring

```javascript
// Connect to MongoDB
docker-compose exec mongodb mongosh rugs_tracker

// Check collection sizes
db.stats()

// Check recent inserts
db.predictions.find().sort({created_at: -1}).limit(5)

// Check index usage
db.predictions.aggregate([{$indexStats: {}}])
```

## Performance Tuning

### Adjust Persistence Intervals

If you see high CPU or memory usage:

```bash
# Increase interval (reduce frequency)
PERSISTENCE_INTERVAL_SECONDS=60  # Default is 30

# Reduce batch size
PERSISTENCE_BATCH_SIZE=50  # Default is 100
```

### Adjust Retention Policies

To reduce storage usage:

```bash
# Reduce tick sample retention (highest volume)
TICK_RETENTION_DAYS=3  # Default is 7

# Reduce prediction retention
PREDICTION_RETENTION_DAYS=30  # Default is 90
```

## Troubleshooting

### Issue: "MongoDB connection failed"

```bash
# Check MongoDB is running
docker-compose ps mongodb

# Test connection
docker-compose exec mongodb mongosh --eval "db.adminCommand('ping')"

# Check connection string
echo $MONGO_URL
```

### Issue: "Persistence enabled but no data saved"

```bash
# Check feature flag
grep PERSISTENCE_ENABLED .env

# Check repository status
curl http://localhost:8000/api/persistence/status | jq '.repository'

# Check for errors in logs
docker-compose logs backend | grep -i error
```

### Issue: "High memory usage"

```bash
# Reduce in-memory buffer sizes
PREDICTION_HISTORY_SIZE=100  # Default is 200
STREAM_RING_SIZE=600  # Default is 1200

# Increase persistence frequency
PERSISTENCE_INTERVAL_SECONDS=15  # Default is 30
```

## Post-Deployment Validation

After 24 hours, validate the system:

1. **Check Data Volume**:
   ```bash
   # In MongoDB
   db.games.countDocuments()
   db.predictions.countDocuments()
   ```

2. **Verify Hourly Metrics**:
   ```bash
   # Should have ~24 records
   db.metrics_hourly.countDocuments()
   ```

3. **Test Historical Queries**:
   ```bash
   curl "http://localhost:8000/api/persistence/metrics?hours=24"
   ```

4. **Verify Cleanup is Working**:
   ```bash
   # Check oldest records
   db.tick_samples.findOne({}, {created_at: 1}, {sort: {created_at: 1}})
   ```

## Success Criteria

The deployment is successful when:

- ✅ System continues normal operations
- ✅ MongoDB contains growing collection of games/predictions
- ✅ No increase in error rates
- ✅ Performance metrics remain stable
- ✅ Hourly metrics are being calculated
- ✅ Old data is being cleaned up per retention policy

## Support

If issues persist after following this guide:

1. Disable persistence (safe rollback)
2. Collect logs from last hour
3. Document the issue with:
   - Error messages
   - Time of occurrence
   - System metrics
   - MongoDB status

---

*Remember: The system is designed to fail gracefully. If persistence has any issues, the core TED functionality continues with in-memory storage.*