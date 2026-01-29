# PICAM - Physics-based Intelligent Capacity and Money

A hotel operational loss detection system that converts real operational data into **provable financial loss** using physics laws, not predictions or speculative AI.

![PICAM Dashboard](docs/dashboard-preview.png)

## 🎯 Core Principles

1. **Physics-Based**: Uses Little's Law (L = λW) and Queueing Theory
2. **Deterministic**: Every calculation is reproducible
3. **Conservative**: Always calculates minimum provable loss (lower bound)
4. **Privacy-First**: No personal data stored; video processed in-memory only
5. **Auditable**: Complete traceability for every output

## 📊 Key Calculations

| Law | Formula | Meaning |
|-----|---------|---------|
| Little's Law | `L = λW` | Customers in system = arrival rate × wait time |
| Utilization | `ρ = λ/(cμ)` | How busy the system is (>1 = unstable) |
| Kingman's Formula | `Wq ∝ (Ca² + Cs²)/2` | Variability increases wait time |
| Queue Length | `Lq = λ × Wq` | Expected queue given utilization |

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/picam.git
cd picam

# Run setup script
chmod +x scripts/setup.sh
./scripts/setup.sh