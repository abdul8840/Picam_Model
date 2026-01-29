# PICAM Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 20GB disk space

## Quick Deployment

```bash
# Clone and setup
git clone https://github.com/your-org/picam.git
cd picam
cp .env.example .env

# Build and start
docker compose up -d

# Seed sample data (optional)
docker compose --profile seed up seeder