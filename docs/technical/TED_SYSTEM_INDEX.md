# TED System Index

## Overview
TED (Treasury Exploitation & Detection) System - Complete index of backend, frontend, and test components.

---

## Backend Components (`/backend/`)

### Core Server
- **server.py** - Main FastAPI server with WebSocket endpoints
  - WebSocket connection handling
  - Prediction endpoints
  - System status monitoring
  - Historical predictions management

### Core Module (`/backend/core/`)
- **__init__.py** - Core module initialization
- **connection_manager.py** - WebSocket connection management

### ML/AI Engines
- **ml_enhanced_engine.py** - Main ML prediction engine with pattern recognition
- **game_aware_ml_engine.py** - Game phase-aware ML model
- **enhanced_pattern_engine.py** - Advanced pattern detection algorithms
- **conformal_wrapper.py** - Conformal prediction wrapper for uncertainty quantification
- **hazard_head.py** - Hazard detection and risk assessment module
- **ultra_short_gate.py** - Ultra-short game detection and handling
- **drift_detectors.py** - Concept drift detection for model stability

### Configuration
- **requirements.txt** - Python dependencies
- **Dockerfile** - Docker containerization

---

## Frontend Components (`/frontend/`)

### Core Application (`/frontend/src/`)
- **index.js** - React application entry point
- **App.js** - Main application component with dashboard layout
- **index.css** - Global styles
- **App.css** - Application-specific styles

### Components
- **SideBetPanel.jsx** - Side bet display and management panel

### Hooks (`/frontend/src/hooks/`)
- **useSystemMonitoring.js** - Custom hook for real-time system monitoring

### Configuration
- **package.json** - Node.js dependencies and scripts
- **craco.config.js** - Create React App configuration override
- **tailwind.config.js** - Tailwind CSS configuration
- **postcss.config.js** - PostCSS configuration
- **Dockerfile** - Docker containerization

### Public Assets (`/frontend/public/`)
- **index.html** - HTML template

---

## Test Suite (`/tests/`)

### Unit Tests
- **test_epr.py** - Enhanced Pattern Recognition tests
- **test_sidebet.py** - Side bet logic and prediction tests
- **test_invariants.py** - System invariant validation tests
- **__init__.py** - Test module initialization

### Integration Tests (root level)
- **backend_test.py** - Backend integration tests
- **detailed_backend_test.py** - Comprehensive backend testing
- **regression_test.py** - Regression testing suite
- **detailed_regression_test.py** - Detailed regression tests
- **prediction_validation_test.py** - Prediction accuracy validation
- **test_patch_smoke.py** - Smoke tests for patches
- **ws_debug.py** - WebSocket debugging utilities
- **ws_system_status_test.py** - WebSocket system status tests
- **test_websocket.html** - Browser-based WebSocket testing interface

---

## Docker Configuration
- **docker-compose.yml** - Production Docker Compose configuration
- **docker-compose.dev.yml** - Development Docker Compose configuration
- **Makefile** - Build and deployment automation

---

## Documentation
- **README.md** - Main project documentation
- **README-DOCKER.md** - Docker setup and usage guide
- **FINAL_INTEGRATION_SUMMARY.md** - Integration completion summary
- **FRONTEND_UPGRADE_SUMMARY.md** - Frontend upgrade details
- **FUTURE_INTEGRATION_PLAN.md** - Roadmap for future enhancements
- **HISTORY_DISPLAY_FIX.md** - History display bug fixes
- **PATCH_INTEGRATION_SUMMARY.md** - Patch integration notes
- **PREDICTION_HISTORY_20_LIMIT_FIX.md** - Prediction history limit fix
- **PR_LAYOUT.md** - Pull request guidelines
- **SCROLLBAR_UPDATE.md** - UI scrollbar improvements
- **test_result.md** - Test execution results

---

## Key Features

### Backend Capabilities
- Real-time WebSocket communication
- ML-based prediction engine with multiple models
- Pattern recognition and anomaly detection
- Conformal prediction for uncertainty quantification
- Drift detection for model stability
- Game phase awareness
- Ultra-short game handling

### Frontend Features
- Real-time dashboard
- Side bet monitoring
- System status display
- Prediction history tracking
- WebSocket connection management
- Responsive UI with Tailwind CSS

### Testing Coverage
- Unit tests for core components
- Integration tests for system workflows
- WebSocket connection testing
- Regression testing suite
- Performance validation

---

## Technology Stack

### Backend
- Python 3.x
- FastAPI
- WebSocket (asyncio)
- NumPy/Pandas for data processing
- Machine Learning libraries

### Frontend
- React.js
- Tailwind CSS
- WebSocket client
- Create React App (with CRACO)

### Infrastructure
- Docker & Docker Compose
- Make for build automation

---

## Quick Start Commands

```bash
# Development
make dev

# Production
docker-compose up

# Run tests
python -m pytest tests/

# Backend only
cd backend && python server.py

# Frontend only
cd frontend && yarn start
```