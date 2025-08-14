# TED System - Treasury Exploitation & Detection

Advanced prediction system for Rugs.fun game analysis using ML-driven pattern recognition and statistical modeling.

## 🎯 Quick Links

- **For Beta Testers**: [User Guide](docs/user/README.md) | [Getting Started](docs/user/GETTING_STARTED.md) | [How It Works](docs/user/HOW_IT_WORKS.md)
- **For Developers**: [Technical Architecture](docs/technical/TECHNICAL_ARCHITECTURE.md) | [System Index](docs/technical/TED_SYSTEM_INDEX.md)
- **Updates**: [Latest Changes](CHANGELOG.md) | [Phase Rollout](docs/updates/PHASE_ROLLOUT_SUMMARY.md)

## 🚀 Quick Start

### Using Docker (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd TED-V1

# Copy environment configuration
cp config/.env.example .env
# Edit .env with your settings

# Start the system
docker-compose up

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/api/docs
```

### Local Development
```bash
# Backend setup
cd backend
pip install -r requirements.txt
cp ../config/.env.example .env
python server.py

# Frontend setup (new terminal)
cd frontend
yarn install
cp ../config/.env.example .env
yarn start
```

## 📁 Project Structure

```
TED-V1/
├── backend/          # Python FastAPI server & ML engines
├── frontend/         # React dashboard application
├── tests/            # Organized test suites
│   ├── unit/        # Unit tests
│   ├── integration/ # Integration tests
│   └── tools/       # Testing utilities
├── docs/            # Documentation
│   ├── user/        # Beta tester guides
│   ├── technical/   # Developer documentation
│   └── updates/     # Release notes
├── config/          # Configuration files
├── scripts/         # Automation scripts
└── docker-compose.yml
```

## 🔧 Key Features

- **Real-time Predictions**: Rug timing predictions with confidence intervals
- **Side Bet Optimization**: EV-based recommendations for 40-tick windows
- **Pattern Recognition**: Three proven patterns for game analysis
- **Adaptive Learning**: Dynamic bias correction and drift detection
- **Performance Metrics**: Comprehensive accuracy tracking

## 📊 Current Performance

- **Prediction Accuracy**: 65-70% within 2 betting windows
- **Side Bet EV**: Positive in favorable conditions
- **Latency**: <50ms end-to-end
- **Uptime Target**: 99.9%

## 🛠️ Technology Stack

- **Backend**: Python 3.10+, FastAPI, NumPy/Pandas
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Database**: MongoDB
- **Infrastructure**: Docker, WebSockets
- **ML/Stats**: Survival Analysis, Conformal Prediction

## 📈 Version

Current: **v2.1.0** (Beta)
- See [CHANGELOG.md](CHANGELOG.md) for version history
- See [Phase Rollout](docs/updates/PHASE_ROLLOUT_SUMMARY.md) for latest updates

## 🧪 Testing

```bash
# Run all tests
make test

# Run specific test category
pytest tests/unit/
pytest tests/integration/
pytest tests/regression/

# Run with coverage
pytest --cov=backend tests/
```

## 📝 Documentation

### For Users
- [User Guide](docs/user/README.md) - Overview and features
- [Getting Started](docs/user/GETTING_STARTED.md) - Step-by-step setup
- [How It Works](docs/user/HOW_IT_WORKS.md) - System explanation

### For Developers
- [Technical Architecture](docs/technical/TECHNICAL_ARCHITECTURE.md) - ML methods & algorithms
- [System Index](docs/technical/TED_SYSTEM_INDEX.md) - Component overview
- [Docker Setup](docs/technical/README-DOCKER.md) - Container configuration

## 🤝 Contributing

As a beta tester, your feedback is invaluable:
- Report bugs with game ID and timestamp
- Share accuracy observations
- Suggest feature improvements
- Note any UI/UX issues

## ⚠️ Disclaimer

This system provides statistical analysis for entertainment purposes. It does not guarantee profits and should not be considered financial advice. Always gamble responsibly.

## 📄 License

Proprietary - All rights reserved

## 🔗 Links

- [API Documentation](http://localhost:8000/api/docs) (when running)
- [Support & Feedback](#) (TBD)

---

*Built with precision for Rugs.fun players who appreciate data-driven decisions.*