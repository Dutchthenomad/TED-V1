# TED-V1 Project Structure Cleanup Plan

## Current Issues Identified

### 1. Test File Organization ❌
**Problem**: Test files scattered between root and `/tests` directory
- Root level: 8 test files (70KB+ total)
- `/tests` directory: Only 3 proper test files

**Files to Move**:
```
backend_test.py → tests/integration/test_backend.py
detailed_backend_test.py → tests/integration/test_backend_detailed.py
detailed_regression_test.py → tests/regression/test_regression_detailed.py
prediction_validation_test.py → tests/validation/test_prediction_validation.py
regression_test.py → tests/regression/test_regression.py
test_patch_smoke.py → tests/smoke/test_patch_smoke.py
ws_debug.py → tests/tools/ws_debug.py
ws_system_status_test.py → tests/integration/test_ws_system_status.py
test_websocket.html → tests/tools/test_websocket.html
```

### 2. Documentation Overload ❌
**Problem**: 13 markdown files in root directory (70KB+)
- Many patch/fix summaries that should be in a docs folder
- Multiple integration summaries that could be consolidated

**Files to Reorganize**:
```
docs/
├── architecture/
│   ├── TED_SYSTEM_INDEX.md (keep in root or here)
│   └── README-DOCKER.md
├── updates/
│   ├── PHASE_ROLLOUT_SUMMARY.md (latest)
│   ├── FINAL_INTEGRATION_SUMMARY.md
│   ├── PATCH_INTEGRATION_SUMMARY.md
│   └── FRONTEND_UPGRADE_SUMMARY.md
├── fixes/
│   ├── HISTORY_DISPLAY_FIX.md
│   ├── PREDICTION_HISTORY_20_LIMIT_FIX.md
│   └── SCROLLBAR_UPDATE.md
└── planning/
    ├── FUTURE_INTEGRATION_PLAN.md
    └── PR_LAYOUT.md
```

### 3. Environment Files ⚠️
**Issue**: Multiple .env files across directories
```
.env.docker (root)
.env.phase2 (root)
backend/.env
frontend/.env
```

**Recommendation**:
```
config/
├── .env.example (template with all vars)
├── .env.docker
├── .env.phase2
└── README.md (explaining each env file)
```

### 4. Duplicate Files ❌
- `yarn.lock` exists in both root and frontend/
- Root level yarn.lock should be removed

### 5. Missing Structure ❌
**Need to Add**:
- `.gitignore` file
- `requirements-dev.txt` for test dependencies
- `scripts/` directory for automation scripts
- `CHANGELOG.md` for version tracking

---

## Recommended Project Structure

```
TED-V1/
├── backend/
│   ├── core/
│   ├── *.py (ML engines, server, etc.)
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── public/
│   ├── src/
│   ├── package.json
│   ├── yarn.lock
│   └── Dockerfile
├── tests/
│   ├── unit/
│   │   ├── test_epr.py
│   │   ├── test_invariants.py
│   │   └── test_sidebet.py
│   ├── integration/
│   │   ├── test_backend.py
│   │   ├── test_backend_detailed.py
│   │   └── test_ws_system_status.py
│   ├── regression/
│   │   ├── test_regression.py
│   │   └── test_regression_detailed.py
│   ├── validation/
│   │   └── test_prediction_validation.py
│   ├── smoke/
│   │   └── test_patch_smoke.py
│   ├── tools/
│   │   ├── ws_debug.py
│   │   └── test_websocket.html
│   └── __init__.py
├── docs/
│   ├── architecture/
│   ├── updates/
│   ├── fixes/
│   └── planning/
├── config/
│   ├── .env.example
│   ├── .env.docker
│   ├── .env.phase2
│   └── README.md
├── scripts/
│   ├── run_tests.sh
│   ├── deploy.sh
│   └── setup.sh
├── docker-compose.yml
├── docker-compose.dev.yml
├── Makefile
├── README.md
├── CHANGELOG.md
├── .gitignore
└── CLAUDE.md
```

---

## Cleanup Commands (Step by Step)

### Step 1: Create New Directories
```bash
mkdir -p tests/{unit,integration,regression,validation,smoke,tools}
mkdir -p docs/{architecture,updates,fixes,planning}
mkdir -p config
mkdir -p scripts
```

### Step 2: Move Test Files
```bash
# Integration tests
mv backend_test.py tests/integration/test_backend.py
mv detailed_backend_test.py tests/integration/test_backend_detailed.py
mv ws_system_status_test.py tests/integration/test_ws_system_status.py

# Regression tests
mv regression_test.py tests/regression/test_regression.py
mv detailed_regression_test.py tests/regression/test_regression_detailed.py

# Validation tests
mv prediction_validation_test.py tests/validation/test_prediction_validation.py

# Smoke tests
mv test_patch_smoke.py tests/smoke/test_patch_smoke.py

# Test tools
mv ws_debug.py tests/tools/
mv test_websocket.html tests/tools/

# Keep existing unit tests
mv tests/test_*.py tests/unit/
```

### Step 3: Organize Documentation
```bash
# Architecture docs
mv TED_SYSTEM_INDEX.md docs/architecture/
mv README-DOCKER.md docs/architecture/

# Update summaries
mv PHASE_ROLLOUT_SUMMARY.md docs/updates/
mv FINAL_INTEGRATION_SUMMARY.md docs/updates/
mv PATCH_INTEGRATION_SUMMARY.md docs/updates/
mv FRONTEND_UPGRADE_SUMMARY.md docs/updates/

# Fix documentation
mv HISTORY_DISPLAY_FIX.md docs/fixes/
mv PREDICTION_HISTORY_20_LIMIT_FIX.md docs/fixes/
mv SCROLLBAR_UPDATE.md docs/fixes/

# Planning docs
mv FUTURE_INTEGRATION_PLAN.md docs/planning/
mv PR_LAYOUT.md docs/planning/

# Test results
mv test_result.md docs/
```

### Step 4: Consolidate Config Files
```bash
# Move env files
mv .env.docker config/
mv .env.phase2 config/

# Create example env file
cat backend/.env > config/.env.example
echo "# Add frontend vars" >> config/.env.example
cat frontend/.env >> config/.env.example
```

### Step 5: Remove Duplicates
```bash
rm yarn.lock  # Keep only frontend/yarn.lock
```

### Step 6: Create Missing Files
```bash
# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# Docker
*.log

# Testing
.coverage
htmlcov/
.pytest_cache/

# OS
.DS_Store
Thumbs.db
EOF

# Create CHANGELOG
echo "# Changelog

## [Current] - 2024-08-13
### Added
- Phase 1-4 rollout for bias correction
- Directional metrics tracking
- Tick-by-tick feature engine

## [1.0.0] - 2024-08-12
- Initial TED system release" > CHANGELOG.md
```

---

## Benefits After Cleanup

1. **Clear Separation**: Tests, docs, and config separated from code
2. **Easier Navigation**: Logical grouping of related files
3. **Better CI/CD**: Test discovery simplified for pytest
4. **Documentation**: All docs in one place, easier to maintain
5. **Configuration**: Centralized config management
6. **Development**: Cleaner root directory, focus on core code

---

## Migration Safety

Before executing cleanup:
1. **Commit all current changes**
2. **Create a backup branch**: `git checkout -b pre-cleanup-backup`
3. **Run tests after each step** to ensure nothing breaks
4. **Update import paths** in Python files after moving tests
5. **Update Makefile** paths if needed

---

## Post-Cleanup Tasks

1. Update `pytest.ini` or test configuration
2. Update Docker volumes in `docker-compose.yml`
3. Update CI/CD pipelines if they exist
4. Update README.md with new structure
5. Update CLAUDE.md paths if needed