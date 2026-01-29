#!/bin/bash

# PICAM Test Script
# Runs all tests and verification

set -e

echo "=========================================="
echo "PICAM Test Suite"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Run backend tests
echo "Running backend tests..."
docker compose exec backend python -m pytest tests/ -v
echo -e "${GREEN}✓ Backend tests passed${NC}"
echo ""

# Run system verification
echo "Running system verification..."
docker compose exec backend python -m app.scripts.verify_system
echo ""

# Test API endpoints
echo "Testing API endpoints..."

# Health check
echo -n "  /health: "
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ "$HEALTH" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED ($HEALTH)${NC}"
fi

# Metrics endpoint
echo -n "  /api/v1/metrics/summary/$(date +%Y-%m-%d): "
METRICS=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/v1/metrics/summary/$(date +%Y-%m-%d)")
if [ "$METRICS" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED ($METRICS)${NC}"
fi

# Insights endpoint
echo -n "  /api/v1/insights/weekly: "
INSIGHTS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/insights/weekly)
if [ "$INSIGHTS" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED ($INSIGHTS)${NC}"
fi

# ROI endpoint
echo -n "  /api/v1/roi/summary: "
ROI=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/roi/summary)
if [ "$ROI" = "200" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED ($ROI)${NC}"
fi

# Privacy compliance
echo -n "  /api/v1/data/privacy-compliance: "
PRIVACY=$(curl -s http://localhost:8000/api/v1/data/privacy-compliance | grep -o '"compliant":true')
if [ -n "$PRIVACY" ]; then
    echo -e "${GREEN}OK (Privacy Compliant)${NC}"
else
    echo -e "${RED}FAILED${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All tests completed!${NC}"
echo "=========================================="