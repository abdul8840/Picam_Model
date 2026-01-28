# PICAM - Physics-based Intelligent Capacity and Money

## Overview

PICAM converts real hotel operational data into **provable financial loss** using physics laws, not predictions or speculative AI.

### Core Principles

1. **Physics-Based**: Uses Little's Law (L = λW) and Queueing Theory
2. **Deterministic**: Every calculation is reproducible
3. **Conservative**: Always calculates minimum provable loss (lower bound)
4. **Privacy-First**: No personal data stored; video processed in-memory only
5. **Auditable**: Complete traceability for every output

### Key Calculations

| Law | Formula | Meaning |
|-----|---------|---------|
| Little's Law | L = λW | Customers in system = arrival rate × wait time |
| Utilization | ρ = λ/μ | How busy the system is (>1 = unstable) |
| Queue Length | Lq = ρ²/(1-ρ) | Expected queue given utilization |
| Wait Time | Wq = Lq/λ | Expected wait time |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend, Step 4)

### Run with Docker

```bash
# Start all services
docker-compose up -d

# Include development tools (Mongo Express)
docker-compose --profile dev up -d