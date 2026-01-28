"""
PICAM Little's Law Calculator

Little's Law: L = λW
- L = Average number of customers in the system
- λ (lambda) = Average arrival rate
- W = Average time a customer spends in the system

This is a fundamental law of queueing theory that holds for ANY system
in steady state, regardless of arrival distribution or service distribution.

References:
- Little, J.D.C. (1961). "A Proof for the Queuing Formula: L = λW"
- Little, J.D.C. & Graves, S.C. (2008). "Little's Law" in Building Intuition
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import List, Optional, Tuple
import numpy as np
from scipy import stats
import hashlib
import json

from app.models.domain import FlowMeasurement, LittlesLawResult, CapacityConstraint
from app.utils import now_utc, create_deterministic_hash


@dataclass
class LittlesLawCalculator:
    """
    Calculator for Little's Law and related queueing metrics.
    
    All calculations are:
    - Deterministic (same inputs → same outputs)
    - Conservative (uses confidence intervals)
    - Auditable (full traceability)
    """
    
    # Configuration
    confidence_level: float = 0.95
    min_data_points: int = 10
    
    # Calculation metadata
    calculation_id: str = field(default_factory=lambda: "")
    
    def __post_init__(self):
        if not self.calculation_id:
            self.calculation_id = f"ll_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    def calculate(
        self,
        measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint] = None
    ) -> Optional[LittlesLawResult]:
        """
        Calculate Little's Law metrics from flow measurements.
        
        Args:
            measurements: List of FlowMeasurement observations
            capacity: Optional capacity constraints for the location
            
        Returns:
            LittlesLawResult with all metrics, or None if insufficient data
        """
        if len(measurements) < self.min_data_points:
            return None
        
        # Extract time series data
        arrival_rates = np.array([m.arrival_rate for m in measurements])
        queue_lengths = np.array([m.queue_length for m in measurements])
        in_service = np.array([m.in_service_count for m in measurements])
        total_in_system = queue_lengths + in_service
        
        # Calculate average arrival rate (λ)
        lambda_rate = np.mean(arrival_rates)
        
        if lambda_rate <= 0:
            return None
        
        # Calculate average number in system (L)
        L = np.mean(total_in_system)
        L_q = np.mean(queue_lengths)
        
        # Apply Little's Law: W = L / λ
        W = L / lambda_rate if lambda_rate > 0 else 0
        W_q = L_q / lambda_rate if lambda_rate > 0 else 0
        
        # Calculate service rate (μ) from departures
        departure_rates = np.array([m.departure_rate for m in measurements])
        mu_rate = np.mean(departure_rates)
        
        # Calculate utilization (ρ = λ / μ)
        # For multi-server: ρ = λ / (c * μ) where c is number of servers
        num_servers = capacity.max_servers if capacity else 1
        if mu_rate > 0:
            rho = lambda_rate / (num_servers * mu_rate)
        else:
            rho = 1.0  # Assume fully utilized if no departure data
        
        # Calculate confidence intervals (conservative)
        ci_lower, ci_upper = self._calculate_confidence_interval(
            total_in_system, 
            self.confidence_level
        )
        
        # Get location info from first measurement
        location_id = measurements[0].location_id
        timestamp = measurements[-1].timestamp
        
        return LittlesLawResult(
            timestamp=timestamp,
            location_id=location_id,
            L=float(L),
            lambda_rate=float(lambda_rate),
            W=float(W),
            L_q=float(L_q),
            W_q=float(W_q),
            rho=float(min(rho, 2.0)),  # Cap at 200% for display
            data_points_used=len(measurements),
            confidence_interval_lower=float(ci_lower),
            confidence_interval_upper=float(ci_upper)
        )
    
    def calculate_from_raw_data(
        self,
        timestamps: List[datetime],
        arrival_counts: List[int],
        queue_lengths: List[int],
        in_service_counts: List[int],
        observation_period_seconds: float = 300,
        location_id: str = "unknown",
        location_type: str = "front_desk"
    ) -> Optional[LittlesLawResult]:
        """
        Calculate from raw data arrays (convenience method).
        """
        from app.models.domain import LocationType
        
        if len(timestamps) < self.min_data_points:
            return None
        
        measurements = []
        for i in range(len(timestamps)):
            m = FlowMeasurement(
                timestamp=timestamps[i],
                location_id=location_id,
                location_type=LocationType(location_type),
                arrival_count=arrival_counts[i],
                queue_length=queue_lengths[i],
                in_service_count=in_service_counts[i],
                observation_period_seconds=observation_period_seconds
            )
            measurements.append(m)
        
        return self.calculate(measurements)
    
    def _calculate_confidence_interval(
        self,
        data: np.ndarray,
        confidence: float
    ) -> Tuple[float, float]:
        """
        Calculate confidence interval for the mean.
        Uses t-distribution for small samples.
        """
        n = len(data)
        mean = np.mean(data)
        
        if n < 2:
            return (mean, mean)
        
        std_err = stats.sem(data)
        
        # Use t-distribution for confidence interval
        t_value = stats.t.ppf((1 + confidence) / 2, n - 1)
        margin = t_value * std_err
        
        return (mean - margin, mean + margin)
    
    def verify_littles_law(
        self,
        measurements: List[FlowMeasurement],
        tolerance: float = 0.15
    ) -> dict:
        """
        Verify that Little's Law holds for the data.
        
        In steady state, L should equal λW within tolerance.
        Large deviations indicate non-steady-state or data quality issues.
        
        Args:
            measurements: Flow measurements
            tolerance: Acceptable relative deviation (default 15%)
            
        Returns:
            Verification result with diagnostics
        """
        if len(measurements) < self.min_data_points:
            return {
                "verified": False,
                "reason": "Insufficient data points",
                "data_points": len(measurements)
            }
        
        # Calculate components
        arrival_rates = [m.arrival_rate for m in measurements]
        total_in_system = [m.queue_length + m.in_service_count for m in measurements]
        
        lambda_avg = np.mean(arrival_rates)
        L_observed = np.mean(total_in_system)
        
        # Get wait times if available
        wait_times = [m.avg_wait_time for m in measurements if m.avg_wait_time]
        
        if not wait_times:
            # Estimate W from L/λ
            W_estimated = L_observed / lambda_avg if lambda_avg > 0 else 0
            return {
                "verified": True,
                "method": "estimation",
                "L_observed": round(L_observed, 4),
                "lambda": round(lambda_avg, 6),
                "W_estimated": round(W_estimated, 2),
                "note": "W estimated from L/λ (no direct wait time data)"
            }
        
        W_observed = np.mean(wait_times)
        
        # Calculate expected L from λW
        L_expected = lambda_avg * W_observed
        
        # Calculate relative deviation
        if L_expected > 0:
            deviation = abs(L_observed - L_expected) / L_expected
        else:
            deviation = 0 if L_observed == 0 else float('inf')
        
        verified = deviation <= tolerance
        
        return {
            "verified": verified,
            "method": "direct_comparison",
            "L_observed": round(L_observed, 4),
            "L_expected": round(L_expected, 4),
            "lambda": round(lambda_avg, 6),
            "W_observed": round(W_observed, 2),
            "deviation": round(deviation, 4),
            "tolerance": tolerance,
            "diagnosis": self._diagnose_deviation(deviation, tolerance)
        }
    
    def _diagnose_deviation(self, deviation: float, tolerance: float) -> str:
        """Diagnose why Little's Law might not hold."""
        if deviation <= tolerance:
            return "System appears to be in steady state"
        elif deviation <= tolerance * 2:
            return "Minor deviation - possible transient effects or measurement noise"
        elif deviation <= tolerance * 4:
            return "Moderate deviation - system may not be in steady state"
        else:
            return "Large deviation - check data quality or system stability"
    
    def calculate_marginal_wait_impact(
        self,
        current_result: LittlesLawResult,
        additional_arrivals_per_hour: float
    ) -> dict:
        """
        Calculate impact of additional arrivals on wait time.
        
        Uses M/M/c queueing approximation for marginal impact.
        This is physics-based: more arrivals with fixed capacity = more waiting.
        """
        current_lambda = current_result.lambda_rate
        current_rho = current_result.rho
        
        # Convert additional arrivals to per-second rate
        delta_lambda = additional_arrivals_per_hour / 3600
        new_lambda = current_lambda + delta_lambda
        
        # New utilization (assuming same service rate)
        if current_lambda > 0:
            mu_rate = current_lambda / current_rho
            new_rho = new_lambda / mu_rate
        else:
            new_rho = current_rho
        
        # Approximate wait time increase
        # For M/M/1: Wq = ρ / (μ(1-ρ))
        # As ρ → 1, wait time → infinity
        
        if new_rho >= 1.0:
            return {
                "status": "unstable",
                "current_rho": round(current_rho, 4),
                "new_rho": round(new_rho, 4),
                "message": "System would become unstable - queue grows unbounded",
                "wait_time_impact": "infinite"
            }
        
        # Calculate wait time ratio
        if current_rho < 1.0:
            current_wait_factor = current_rho / (1 - current_rho)
            new_wait_factor = new_rho / (1 - new_rho)
            wait_multiplier = new_wait_factor / current_wait_factor if current_wait_factor > 0 else float('inf')
        else:
            wait_multiplier = float('inf')
        
        return {
            "status": "stable" if new_rho < 0.85 else "stressed",
            "current_lambda": round(current_lambda * 3600, 2),  # per hour
            "new_lambda": round(new_lambda * 3600, 2),  # per hour
            "current_rho": round(current_rho, 4),
            "new_rho": round(new_rho, 4),
            "wait_time_multiplier": round(wait_multiplier, 2),
            "current_W_q": round(current_result.W_q, 2),
            "estimated_new_W_q": round(current_result.W_q * wait_multiplier, 2)
        }


class MultiServerQueueCalculator:
    """
    M/M/c Queue Calculator for multi-server scenarios.
    
    Models:
    - Front desk with multiple agents
    - Restaurant with multiple tables
    - Any service point with parallel servers
    """
    
    def __init__(self, num_servers: int, service_rate_per_server: float):
        """
        Args:
            num_servers: Number of parallel servers (c)
            service_rate_per_server: Service rate per server (μ)
        """
        self.c = num_servers
        self.mu = service_rate_per_server
        self.total_capacity = num_servers * service_rate_per_server
    
    def calculate_metrics(self, arrival_rate: float) -> dict:
        """
        Calculate M/M/c queue metrics.
        
        Args:
            arrival_rate: λ - arrivals per time unit
            
        Returns:
            Dictionary of queue metrics
        """
        lambda_rate = arrival_rate
        c = self.c
        mu = self.mu
        
        # Traffic intensity
        rho = lambda_rate / (c * mu)
        
        if rho >= 1.0:
            return {
                "status": "unstable",
                "rho": rho,
                "message": "Arrival rate exceeds capacity - queue grows unbounded"
            }
        
        # Erlang C formula for P(wait)
        # This gives probability that an arriving customer must wait
        p0 = self._calculate_p0(lambda_rate, mu, c)
        erlang_c = self._calculate_erlang_c(lambda_rate, mu, c, p0)
        
        # Expected queue length: Lq = (Erlang_C * ρ) / (1 - ρ)
        L_q = (erlang_c * rho) / (1 - rho)
        
        # Expected wait time in queue: Wq = Lq / λ
        W_q = L_q / lambda_rate if lambda_rate > 0 else 0
        
        # Expected time in system: W = Wq + 1/μ
        W = W_q + (1 / mu)
        
        # Expected number in system: L = λW
        L = lambda_rate * W
        
        return {
            "status": "stable",
            "servers": c,
            "rho": round(rho, 4),
            "p_wait": round(erlang_c, 4),  # Probability of waiting
            "L": round(L, 4),
            "L_q": round(L_q, 4),
            "W": round(W, 2),
            "W_q": round(W_q, 2),
            "service_rate": mu,
            "arrival_rate": lambda_rate
        }
    
    def _calculate_p0(self, lambda_rate: float, mu: float, c: int) -> float:
        """Calculate probability of empty system (P0)."""
        rho = lambda_rate / (c * mu)
        a = lambda_rate / mu  # Offered load
        
        sum_term = sum((a ** n) / np.math.factorial(n) for n in range(c))
        last_term = ((a ** c) / np.math.factorial(c)) * (1 / (1 - rho))
        
        p0 = 1 / (sum_term + last_term)
        return p0
    
    def _calculate_erlang_c(
        self, 
        lambda_rate: float, 
        mu: float, 
        c: int, 
        p0: float
    ) -> float:
        """Calculate Erlang C (probability of waiting)."""
        a = lambda_rate / mu
        rho = lambda_rate / (c * mu)
        
        erlang_c = ((a ** c) / np.math.factorial(c)) * (1 / (1 - rho)) * p0
        return erlang_c
    
    def find_optimal_servers(
        self,
        arrival_rate: float,
        target_wait_time: float,
        max_servers: int = 20
    ) -> dict:
        """
        Find minimum servers needed to achieve target wait time.
        
        Args:
            arrival_rate: Expected arrival rate
            target_wait_time: Maximum acceptable wait time
            max_servers: Maximum servers to consider
            
        Returns:
            Optimal configuration
        """
        for c in range(1, max_servers + 1):
            calc = MultiServerQueueCalculator(c, self.mu)
            metrics = calc.calculate_metrics(arrival_rate)
            
            if metrics.get("status") == "stable" and metrics["W_q"] <= target_wait_time:
                return {
                    "optimal_servers": c,
                    "achieved_wait_time": metrics["W_q"],
                    "target_wait_time": target_wait_time,
                    "utilization": metrics["rho"],
                    "metrics": metrics
                }
        
        return {
            "optimal_servers": None,
            "message": f"Cannot achieve target with <= {max_servers} servers",
            "target_wait_time": target_wait_time
        }


def create_audit_log(
    calculation_type: str,
    inputs: dict,
    outputs: dict,
    formula: str
) -> dict:
    """
    Create audit log entry for a calculation.
    """
    timestamp = now_utc()
    
    audit_entry = {
        "calculation_type": calculation_type,
        "timestamp": timestamp.isoformat(),
        "inputs": inputs,
        "outputs": outputs,
        "formula": formula,
        "is_deterministic": True
    }
    
    # Create hash for verification
    audit_entry["hash"] = create_deterministic_hash(audit_entry)
    
    return audit_entry