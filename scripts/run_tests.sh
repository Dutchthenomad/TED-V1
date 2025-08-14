#!/bin/bash

# TED System - Test Runner Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "TED System - Test Suite Runner"
echo "========================================="

# Check if we're in the right directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Must run from TED-V1 root directory${NC}"
    exit 1
fi

# Parse command line arguments
TEST_TYPE=${1:-all}
COVERAGE=${2:-false}

# Function to run tests
run_tests() {
    local test_path=$1
    local test_name=$2
    
    echo -e "\n${YELLOW}Running $test_name...${NC}"
    
    if [ "$COVERAGE" == "coverage" ]; then
        pytest --cov=backend --cov-report=html --cov-report=term $test_path
    else
        pytest -v $test_path
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $test_name passed${NC}"
    else
        echo -e "${RED}✗ $test_name failed${NC}"
        exit 1
    fi
}

# Main test execution
case $TEST_TYPE in
    unit)
        run_tests "tests/unit/" "Unit Tests"
        ;;
    integration)
        run_tests "tests/integration/" "Integration Tests"
        ;;
    regression)
        run_tests "tests/regression/" "Regression Tests"
        ;;
    validation)
        run_tests "tests/validation/" "Validation Tests"
        ;;
    smoke)
        run_tests "tests/smoke/" "Smoke Tests"
        ;;
    all)
        echo "Running all test suites..."
        run_tests "tests/unit/" "Unit Tests"
        run_tests "tests/integration/" "Integration Tests"
        run_tests "tests/regression/" "Regression Tests"
        run_tests "tests/validation/" "Validation Tests"
        run_tests "tests/smoke/" "Smoke Tests"
        ;;
    *)
        echo "Usage: $0 [unit|integration|regression|validation|smoke|all] [coverage]"
        echo "Example: $0 unit        # Run unit tests"
        echo "         $0 all coverage # Run all tests with coverage"
        exit 1
        ;;
esac

echo -e "\n========================================="
echo -e "${GREEN}All tests completed successfully!${NC}"
echo "========================================="

# Show coverage report location if generated
if [ "$COVERAGE" == "coverage" ]; then
    echo -e "\n${YELLOW}Coverage report generated at: htmlcov/index.html${NC}"
fi