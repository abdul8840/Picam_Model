"""
PICAM Core Physics Engine Package

This package contains the physics-based calculation engine that converts
operational data into provable financial losses.

Key Components:
- LittlesLawCalculator: L = λW calculations
- EntropyCalculator: Variability and its cost impact
- LossCalculator: Conservative financial loss estimation
- PhysicsEngine: Unified orchestrator

All calculations are:
- Deterministic
- Conservative (lower bounds)
- Physics-based (no ML/AI)
- Fully auditable
"""

from app.core.littles_law import (
    LittlesLawCalculator,
    MultiServerQueueCalculator,
    create_audit_log
)

from app.core.entropy_calculator import (
    EntropyCalculator,
    OperationalStabilityAnalyzer
)

from app.core.loss_calculator import (
    LossCalculator,
    FinancialParameters,
    ROICalculator
)

from app.core.physics_engine import (
    PhysicsEngine,
    get_physics_engine
)

__all__ = [
    # Little's Law
    "LittlesLawCalculator",
    "MultiServerQueueCalculator",
    "create_audit_log",
    
    # Entropy
    "EntropyCalculator",
    "OperationalStabilityAnalyzer",
    
    # Loss Calculation
    "LossCalculator",
    "FinancialParameters",
    "ROICalculator",
    
    # Main Engine
    "PhysicsEngine",
    "get_physics_engine"
]