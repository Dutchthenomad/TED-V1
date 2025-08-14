# Changelog

All notable changes to the TED system will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive project reorganization
- Beta tester documentation suite (README, Getting Started, How It Works)
- Technical architecture documentation for developers
- Organized test structure with categories
- Configuration management system

### Changed
- Moved all tests to organized `/tests` subdirectories
- Relocated documentation to `/docs` with categorization
- Centralized configuration files in `/config`
- Cleaned up root directory

## [2.1.0] - 2024-08-13

### Added
- Phase 1: Directional error metrics (E40, signed errors, coverage rates)
- Phase 2: EPR configuration tuning for better accuracy
- Phase 3: Dynamic quantile adjustment based on bias
- Phase 4: Tick-by-tick feature engine (shadow mode)
- Frontend directional metrics display
- `/api/tick-history` endpoint for streaming features
- `/api/metrics` enhanced with multi-window analysis

### Changed
- EPR threshold reduced from 3.0 to 2.8
- EPR hazard scale reduced from 0.75 to 0.70
- Side bet thresholds now dynamic based on peak detection

### Fixed
- Systematic early bias on long games (reduced from -435 to target <-250 ticks)
- Poor accuracy on high-peak games
- Coverage rate calibration

## [2.0.0] - 2024-08-12

### Added
- Early Peak Regime (EPR) detection and adaptation
- Conformal prediction with PID control
- Ultra-short game gating mechanism
- Drift detection with Page-Hinkley test
- WebSocket system status monitoring
- Prediction history tracking with accuracy metrics
- Side bet performance analytics

### Changed
- Complete ML engine overhaul with hazard modeling
- Improved pattern detection algorithms
- Enhanced WebSocket connection management
- Frontend upgraded to real-time dashboard

### Fixed
- Prediction history display limit
- WebSocket reconnection issues
- Scrollbar functionality in frontend

## [1.0.0] - 2024-08-01

### Added
- Initial TED system release
- Basic pattern recognition engine
- Three core patterns: Post-Max Payout, Ultra-Short, Momentum
- FastAPI backend with WebSocket support
- React frontend dashboard
- MongoDB integration for data persistence
- Docker containerization

### Security
- Input validation for all API endpoints
- CORS configuration for security
- Environment variable management for credentials

---

## Version History Summary

- **2.1.0** - Bias correction and directional metrics
- **2.0.0** - ML enhancements and EPR
- **1.0.0** - Initial release

## Upcoming (Planned)

### Version 3.0.0 (Q4 2024)
- [ ] Full tick feature influence activation
- [ ] Advanced pattern discovery with AutoML
- [ ] Mobile application support
- [ ] API for automated trading
- [ ] Community-driven pattern contributions