# Configuration Files

This directory contains environment configuration files for the TED system.

## Files

### `.env.example`
Template configuration file with all available environment variables. Copy this to `.env` in the appropriate directory (backend/, frontend/, or root for Docker) and update with your values.

### `.env.docker`
Docker-specific environment configuration. Used when running the system via Docker Compose.

### `.env.phase2`
Phase 2 rollout configuration with optimized EPR settings based on performance audits. Use these settings when deploying Phase 2 improvements.

## Usage

### Local Development
```bash
# Backend
cp config/.env.example backend/.env
# Edit backend/.env with your settings

# Frontend
cp config/.env.example frontend/.env
# Edit frontend/.env (only REACT_APP_* variables needed)
```

### Docker Deployment
```bash
cp config/.env.docker .env
# Edit .env with production values
docker-compose up
```

### Phase 2 Rollout
```bash
# Merge Phase 2 settings into your current .env
cat config/.env.phase2 >> backend/.env
# Review and adjust as needed
```

## Key Configuration Groups

### 1. Database Settings
- `MONGO_URL`: MongoDB connection string
- `DB_NAME`: Database name for game data

### 2. ML/Prediction Tuning
- `EPR_*`: Early Peak Regime detection parameters
- `QUANTILE_*`: Dynamic quantile adjustment settings
- `SIDEBET_*`: Side bet recommendation thresholds

### 3. Feature Flags
- `STREAM_FEATURES_ENABLED`: Enable tick-by-tick analysis
- `QUANTILE_ADJUSTMENT_ENABLED`: Enable dynamic bias correction
- `REACT_APP_FEATURE_TICK_PANEL`: Show tick panel in frontend

### 4. Performance Settings
- `STREAM_MAX_CPU_MS`: CPU budget for tick processing
- `PREDICTION_HISTORY_SIZE`: Number of predictions to keep
- `STREAM_RING_SIZE`: Tick history buffer size

## Security Notes

⚠️ **Never commit `.env` files with real credentials**
- Add `.env` to `.gitignore`
- Use environment-specific values
- Rotate credentials regularly
- Use secrets management in production