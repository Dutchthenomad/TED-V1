# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TED (Treasury Exploitation & Detection) System - A production-ready ML-based prediction service for the rugs.fun gambling game. The system connects to rugs.fun WebSocket backend, processes real-time game data, and provides predictions for trading and side bet strategies using survival analysis and pattern recognition.

**Current Version**: V2.1.0 (Beta)
**Architecture**: Docker-based microservices (FastAPI backend + React frontend + MongoDB)

## Key Commands

### Development Commands

```bash
# Docker-based development (recommended)
make build        # Build all Docker images
make up           # Start all services (Frontend: localhost:3000, Backend: localhost:8000)
make down         # Stop all services
make logs         # View logs from all services
make shell        # Open shell in backend container
make test         # Run pytest tests in Docker container
make clean        # Remove containers and volumes

# Backend (Python/FastAPI) - Local development
cd backend
python3 server.py  # Run backend directly (requires MongoDB running)

# Frontend (React) - Local development
cd frontend
yarn install      # Install dependencies (uses yarn 1.22.22)
yarn start        # Start development server with craco
yarn build        # Build production bundle
yarn test         # Run frontend tests

# Testing
./scripts/run_tests.sh all           # Run all test suites
./scripts/run_tests.sh unit          # Run unit tests only
./scripts/run_tests.sh integration   # Run integration tests
./scripts/run_tests.sh all coverage  # Run with coverage report
pytest tests/unit/                   # Direct pytest usage for specific category
pytest -v tests/integration/         # Verbose test output
```

## High-Level Architecture

### System Components & Data Flow

1. **WebSocket Ingestion Layer** (`backend/core/connection_manager.py`)
   - Connects to rugs.fun WebSocket API
   - Processes game events every 250ms (tick rate)
   - Maintains connection health with automatic reconnection

2. **ML Prediction Pipeline** (Multiple engines work in ensemble)
   - `ml_enhanced_engine.py`: Core prediction logic with hazard modeling
   - `game_aware_ml_engine.py`: Game phase-aware predictions with EPR detection
   - `enhanced_pattern_engine.py`: Pattern recognition for treasury exploitation
   - `hazard_head.py`: Survival analysis and risk assessment
   - `conformal_wrapper.py`: Uncertainty quantification with PID control
   - `drift_detectors.py`: Concept drift detection for model stability
   - `ultra_short_gate.py`: Specialized handling for games <100 ticks
   - `tick_features.py`: O(1) streaming feature computation

3. **API Layer** (`backend/server.py`)
   - FastAPI server with WebSocket endpoints
   - RESTful endpoints for metrics and history
   - `IntegratedPatternTracker` class manages all in-memory data storage
   - MongoDB integration (minimal usage - only status_checks collection)

4. **Frontend Dashboard** (`frontend/src/`)
   - Real-time React dashboard with WebSocket connection
   - Components use custom hooks for system monitoring
   - Tailwind CSS for styling

### Critical Data Structures

**In-Memory Storage** (No persistent game history):
- `prediction_history`: deque(maxlen=200) - Recent game predictions
- `side_bet_history`: deque(maxlen=200) - Recent bet outcomes  
- `tick_ring`: deque(maxlen=1200) - Streaming tick snapshots
- All data lost on server restart - MongoDB only stores status checks

### Game Mechanics Context

Understanding rugs.fun mechanics is crucial for the codebase:
- **Tick**: Atomic time unit (250ms), games measured in ticks
- **Candle**: 5 ticks = 1 candle for OHLC visualization
- **Rug Event**: Game termination with ~0.005 probability per tick
- **Side Bets**: 40-tick window bets on rug occurrence (5:1 payout)
- **Mean Duration**: ~280 ticks empirically (theoretical: 200 ticks)
- **EPR (Early Peak Regime)**: Special handling when peak/baseline > 2.8

### Key Algorithms & Thresholds

1. **Pattern Detection Thresholds**
   - `EPR_RATIO_THRESHOLD`: 2.8 (triggers early peak regime)
   - `EPR_HAZARD_SCALE`: 0.70 (hazard adjustment factor)
   - `MAX_PAYOUT_THRESHOLD`: 50x (moonshot detection)
   - Ultra-short boundary: 100 ticks

2. **Dynamic Quantile Adjustment**
   - Formula: `qt = 0.5 + clip(medE40, -0.3, 0.3) * 0.3`
   - E40: Window-normalized error metric (signed_error / 40)
   - Corrects systematic prediction bias

3. **Side Bet Strategy**
   - Break-even hazard: p* ≈ 0.005563
   - 40-tick analysis window
   - 4-tick cooldown between bets

## Environment Configuration

Required `.env` file (copy from `config/.env.example`):
```bash
# Database
MONGO_URL=mongodb://localhost:27017/rugs_tracker
DB_NAME=rugs_tracker  # Optional, extracted from URL if not set

# Server
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

# ML Tuning (Phase 2 settings)
EPR_RATIO_THRESHOLD=2.8
EPR_HAZARD_SCALE=0.70
QUANTILE_ADJUSTMENT_ENABLED=true
STREAM_FEATURES_ENABLED=false  # Set true for tick feature activation

# Performance
STREAM_RING_SIZE=1200
PREDICTION_HISTORY_SIZE=200
STREAM_MAX_CPU_MS=15
```

## Testing Strategy

Tests are organized by category in `/tests/`:
- `unit/`: Core logic validation (invariants, EPR, sidebets)
- `integration/`: WebSocket and API testing
- `regression/`: Historical accuracy validation
- `validation/`: Model performance metrics
- `smoke/`: Quick health checks
- `tools/`: Test utilities and fixtures

Run single test file:
```bash
pytest tests/unit/test_invariants.py -v
pytest tests/unit/test_epr.py::test_specific_function
```

## Performance Targets

- WebSocket throughput: ~1000 events/second
- Prediction latency: <50ms end-to-end
- Frontend update rate: 4Hz (throttled)
- Memory usage: <500MB typical
- CPU usage: <30% single core

## Project Structure

```
TED-V1/
├── backend/              # FastAPI server & ML engines
│   ├── server.py        # Main API & WebSocket endpoints
│   ├── *_engine.py      # ML prediction engines
│   ├── tick_features.py # Streaming feature computation
│   └── core/            # WebSocket connection management
├── frontend/            # React dashboard
│   ├── src/App.js      # Main dashboard component
│   └── src/components/ # UI components
├── tests/              # Organized test suites
├── docs/               # Documentation
│   ├── user/          # Beta tester guides
│   ├── technical/     # Developer docs
│   └── updates/       # Release notes
├── config/            # Environment configurations
├── scripts/           # Automation scripts
├── docker-compose.yml # Container orchestration
├── Makefile          # Development commands
└── CLAUDE.md         # This file
```

## Current Known Issues

- No persistent storage of game history (all in-memory)
- Side bet cooldown enforces 4-tick minimum between bets
- Presale tick handling requires special -1 mapping
- God candle events (0.001% chance) need separate detection
- Test imports may fail after file reorganization (add parent to sys.path)

## V2.1.0 Recent Changes

- Added directional metrics (E40) for bias measurement
- Dynamic quantile adjustment to correct systematic early bias
- EPR threshold tuning (3.0 → 2.8) for better accuracy
- Tick feature engine in shadow mode for future activation
- Comprehensive project reorganization with `/docs` and `/tests` structure