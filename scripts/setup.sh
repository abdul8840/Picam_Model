#!/bin/bash

# PICAM Setup Script
# Initializes the complete PICAM system

set -e

echo "=========================================="
echo "PICAM Setup Script"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is installed${NC}"

# Create .env if not exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env file${NC}"
else
    echo -e "${YELLOW}⚠ .env file already exists, skipping${NC}"
fi

# Build containers
echo ""
echo "Building Docker containers..."
docker compose build

echo -e "${GREEN}✓ Containers built${NC}"

# Start services
echo ""
echo "Starting services..."
docker compose up -d mongodb
echo "Waiting for MongoDB to be ready..."
sleep 10

docker compose up -d backend
echo "Waiting for backend to be ready..."
sleep 15

docker compose up -d frontend
echo -e "${GREEN}✓ All services started${NC}"

# Health check
echo ""
echo "Checking system health..."
sleep 5

BACKEND_HEALTH=$(curl -s http://localhost:8000/health | grep -o '"status":"[^"]*"' | head -1)
if [[ $BACKEND_HEALTH == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
fi

# Seed data
echo ""
read -p "Do you want to seed sample data? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Seeding sample data..."
    docker compose --profile seed up seeder
    echo -e "${GREEN}✓ Sample data seeded${NC}"
fi

# Print access info
echo ""
echo "=========================================="
echo -e "${GREEN}PICAM Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Access points:"
echo "  • Dashboard:     http://localhost:3000"
echo "  • API:           http://localhost:8000"
echo "  • API Docs:      http://localhost:8000/api/docs"
echo ""
echo "To start development tools:"
echo "  docker compose --profile dev up -d"
echo ""
echo "To view logs:"
echo "  docker compose logs -f"
echo ""
echo "To stop:"
echo "  docker compose down"
echo ""