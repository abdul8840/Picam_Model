"""
PICAM Entropy Calculator

Operational entropy measures variability/unpredictability in hotel operations.
Higher entropy = higher operational cost due to:
- Staffing buffer requirements
- Customer dissatisfaction from unpredictability
- Reduced efficiency from variability

Based on:
- Coefficient of Variation (CV) analysis
- Kingman's Formula for queue impact
- Information entropy concepts
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict
import numpy as np
from scipy import stats

from app.models.domain import FlowMeasurement, EntropyMeasurement
from app.utils import now_utc


@dataclass
class EntropyCalculator:
    """
    Calculates operational entropy (variability) and its cost impact.
    
    Key insight: In queueing systems, variability directly increases wait times.
    Kingman's Formula: Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)
    
    Where:
    - Ca = Coefficient of variation of arrivals
    - Cs = Coefficient of variation of service
    
    Higher CV = Higher wait times = Higher costs
    """
    
    min_data_points: int = 10
    
    def calculate_entropy(
        self,
        measurements: List[FlowMeasurement],
        location_id: str
    ) -> Optional[EntropyMeasurement]:
        """
        Calculate entropy metrics from flow measurements.
        
        Args:
            measurements: List of flow measurements
            location_id: Location identifier
            
        Returns:
            EntropyMeasurement with variability metrics
        """
        if len(measurements) < self.min_data_points:
            return None
        
        # Extract arrival data
        arrivals = np.array([m.arrival_count for m in measurements])
        
        # Extract service duration data (if available)
        service_times = np.array([
            m.avg_service_duration 
            for m in measurements 
            if m.avg_service_duration is not None
        ])
        
        # Calculate Coefficient of Variation for arrivals
        arrival_cv = self._calculate_cv(arrivals)
        
        # Calculate CV for service times
        if len(service_times) >= self.min_data_points:
            service_cv = self._calculate_cv(service_times)
        else:
            # Assume moderate variability if no service data
            service_cv = 0.5
        
        # Calculate entropy score (normalized 0-1)
        entropy_score = self._calculate_entropy_score(arrivals)
        
        # Calculate variance impact multiplier (Kingman's approximation)
        variance_impact = (arrival_cv ** 2 + service_cv ** 2) / 2
        
        return EntropyMeasurement(
            timestamp=measurements[-1].timestamp,
            location_id=location_id,
            arrival_cv=float(arrival_cv),
            service_cv=float(service_cv),
            entropy_score=float(entropy_score),
            variance_impact_multiplier=float(max(1.0, 1 + variance_impact))
        )
    
    def _calculate_cv(self, data: np.ndarray) -> float:
        """
        Calculate Coefficient of Variation (CV = σ/μ).
        
        CV interpretation:
        - CV < 0.5: Low variability
        - CV 0.5-1.0: Moderate variability
        - CV > 1.0: High variability
        """
        if len(data) < 2:
            return 0.0
        
        mean = np.mean(data)
        std = np.std(data, ddof=1)  # Sample std deviation
        
        if mean <= 0:
            return 0.0
        
        return std / mean
    
    def _calculate_entropy_score(self, data: np.ndarray) -> float:
        """
        Calculate normalized entropy score (0-1).
        
        Uses binned histogram to estimate probability distribution,
        then calculates Shannon entropy normalized by maximum possible entropy.
        """
        if len(data) < 2:
            return 0.0
        
        # Bin the data
        num_bins = min(10, len(data) // 2)
        if num_bins < 2:
            return 0.0
        
        hist, _ = np.histogram(data, bins=num_bins, density=True)
        
        # Remove zero bins and normalize
        hist = hist[hist > 0]
        hist = hist / hist.sum()
        
        # Calculate Shannon entropy
        entropy = -np.sum(hist * np.log2(hist))
        
        # Normalize by maximum possible entropy (uniform distribution)
        max_entropy = np.log2(num_bins)
        
        if max_entropy <= 0:
            return 0.0
        
        return entropy / max_entropy
    
    def analyze_patterns(
        self,
        measurements: List[FlowMeasurement]
    ) -> Dict[str, any]:
        """
        Analyze temporal patterns in the data.
        
        Identifies:
        - Peak hours
        - High variability periods
        - Predictable vs unpredictable patterns
        """
        if len(measurements) < self.min_data_points:
            return {"status": "insufficient_data"}
        
        # Group by hour
        hourly_data: Dict[int, List[int]] = {h: [] for h in range(24)}
        
        for m in measurements:
            hour = m.timestamp.hour
            hourly_data[hour].append(m.arrival_count)
        
        # Calculate hourly statistics
        hourly_stats = {}
        for hour, arrivals in hourly_data.items():
            if arrivals:
                hourly_stats[hour] = {
                    "mean": float(np.mean(arrivals)),
                    "std": float(np.std(arrivals)) if len(arrivals) > 1 else 0,
                    "cv": float(self._calculate_cv(np.array(arrivals))) if len(arrivals) > 1 else 0,
                    "count": len(arrivals)
                }
        
        # Identify peak hours (top 3 by mean arrivals)
        sorted_hours = sorted(
            hourly_stats.items(),
            key=lambda x: x[1]["mean"],
            reverse=True
        )
        peak_hours = [h for h, _ in sorted_hours[:3] if hourly_stats[h]["mean"] > 0]
        
        # Identify high variability hours
        high_var_hours = [
            h for h, s in hourly_stats.items()
            if s.get("cv", 0) > 1.0 and s.get("count", 0) >= 3
        ]
        
        # Calculate overall pattern predictability
        all_cvs = [s["cv"] for s in hourly_stats.values() if s.get("count", 0) >= 3]
        avg_cv = np.mean(all_cvs) if all_cvs else 0
        
        predictability = "high" if avg_cv < 0.5 else "medium" if avg_cv < 1.0 else "low"
        
        return {
            "status": "analyzed",
            "peak_hours": peak_hours,
            "high_variability_hours": high_var_hours,
            "predictability": predictability,
            "avg_cv": round(avg_cv, 4),
            "hourly_stats": hourly_stats
        }
    
    def calculate_kingman_impact(
        self,
        arrival_cv: float,
        service_cv: float,
        utilization: float
    ) -> dict:
        """
        Calculate the Kingman approximation impact.
        
        Kingman's Formula (G/G/1 approximation):
        Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)
        
        The variability term ((Ca² + Cs²)/2) is the multiplier on base wait time.
        """
        if utilization >= 1.0:
            return {
                "status": "unstable",
                "message": "System at or above capacity - wait time unbounded"
            }
        
        # Variability multiplier
        variability_term = (arrival_cv ** 2 + service_cv ** 2) / 2
        
        # Utilization impact
        utilization_term = utilization / (1 - utilization)
        
        # Combined multiplier on base service time
        wait_multiplier = utilization_term * variability_term
        
        # Compare to ideal (CV = 1 for both, Poisson process)
        ideal_variability = (1.0 + 1.0) / 2  # Both CVs = 1
        actual_vs_ideal = variability_term / ideal_variability
        
        # Interpretation
        if variability_term < 0.5:
            interpretation = "Low variability - efficient operations"
        elif variability_term < 1.0:
            interpretation = "Moderate variability - typical for most systems"
        elif variability_term < 2.0:
            interpretation = "High variability - significant wait time impact"
        else:
            interpretation = "Very high variability - major operational challenge"
        
        return {
            "status": "calculated",
            "arrival_cv": round(arrival_cv, 4),
            "service_cv": round(service_cv, 4),
            "utilization": round(utilization, 4),
            "variability_term": round(variability_term, 4),
            "utilization_term": round(utilization_term, 4),
            "wait_multiplier": round(wait_multiplier, 4),
            "vs_ideal_ratio": round(actual_vs_ideal, 4),
            "interpretation": interpretation,
            "formula": "Wq ≈ (ρ/(1-ρ)) × ((Ca² + Cs²)/2) × (1/μ)"
        }
    
    def estimate_variability_cost(
        self,
        entropy_measurement: EntropyMeasurement,
        base_wait_cost_per_minute: float,
        daily_customers: int,
        base_wait_minutes: float
    ) -> dict:
        """
        Estimate the cost impact of variability.
        
        Compares actual variability to ideal (CV=1) scenario.
        """
        # Actual variability impact
        actual_multiplier = entropy_measurement.variance_impact_multiplier
        
        # Ideal scenario (Poisson arrivals, exponential service)
        ideal_multiplier = 1.0  # (1² + 1²) / 2 = 1
        
        # Extra wait time due to variability
        extra_multiplier = max(0, actual_multiplier - ideal_multiplier)
        extra_wait_per_customer = base_wait_minutes * extra_multiplier
        
        # Total extra wait
        total_extra_wait = extra_wait_per_customer * daily_customers
        
        # Cost of extra wait
        variability_cost = total_extra_wait * base_wait_cost_per_minute
        
        return {
            "actual_multiplier": round(actual_multiplier, 4),
            "ideal_multiplier": ideal_multiplier,
            "extra_multiplier": round(extra_multiplier, 4),
            "extra_wait_per_customer_minutes": round(extra_wait_per_customer, 2),
            "daily_customers": daily_customers,
            "total_extra_wait_minutes": round(total_extra_wait, 2),
            "variability_cost": round(variability_cost, 2),
            "interpretation": self._interpret_variability_cost(variability_cost, daily_customers)
        }
    
    def _interpret_variability_cost(self, cost: float, customers: int) -> str:
        """Interpret the variability cost."""
        cost_per_customer = cost / customers if customers > 0 else 0
        
        if cost_per_customer < 0.5:
            return "Low variability cost - operations are efficient"
        elif cost_per_customer < 2.0:
            return "Moderate variability cost - room for improvement"
        elif cost_per_customer < 5.0:
            return "High variability cost - consider smoothing demand"
        else:
            return "Very high variability cost - urgent attention needed"


class OperationalStabilityAnalyzer:
    """
    Analyzes operational stability over time.
    
    Identifies periods of:
    - Stability (steady state)
    - Transition (changing conditions)
    - Crisis (system overload)
    """
    
    def analyze_stability(
        self,
        measurements: List[FlowMeasurement],
        window_size: int = 12  # 1 hour with 5-min intervals
    ) -> Dict[str, any]:
        """
        Analyze stability using rolling window analysis.
        """
        if len(measurements) < window_size * 2:
            return {"status": "insufficient_data"}
        
        arrivals = [m.arrival_count for m in measurements]
        queues = [m.queue_length for m in measurements]
        
        # Calculate rolling statistics
        stability_periods = []
        
        for i in range(len(measurements) - window_size):
            window_arrivals = arrivals[i:i + window_size]
            window_queues = queues[i:i + window_size]
            
            # Stability indicators
            arrival_trend = self._calculate_trend(window_arrivals)
            queue_trend = self._calculate_trend(window_queues)
            arrival_cv = np.std(window_arrivals) / np.mean(window_arrivals) if np.mean(window_arrivals) > 0 else 0
            
            # Classify period
            if abs(arrival_trend) < 0.1 and abs(queue_trend) < 0.2:
                state = "stable"
            elif queue_trend > 0.5:
                state = "degrading"
            elif queue_trend < -0.5:
                state = "recovering"
            else:
                state = "transition"
            
            # Check for crisis (queue growing rapidly)
            if np.mean(window_queues) > 10 and queue_trend > 0.3:
                state = "crisis"
            
            stability_periods.append({
                "index": i,
                "timestamp": measurements[i].timestamp.isoformat(),
                "state": state,
                "arrival_trend": round(arrival_trend, 4),
                "queue_trend": round(queue_trend, 4),
                "arrival_cv": round(arrival_cv, 4)
            })
        
        # Summarize
        state_counts = {}
        for p in stability_periods:
            state = p["state"]
            state_counts[state] = state_counts.get(state, 0) + 1
        
        total = len(stability_periods)
        
        return {
            "status": "analyzed",
            "total_periods": total,
            "state_distribution": {
                state: round(count / total, 4)
                for state, count in state_counts.items()
            },
            "crisis_periods": sum(1 for p in stability_periods if p["state"] == "crisis"),
            "stable_percentage": round(
                state_counts.get("stable", 0) / total * 100, 2
            ),
            "periods": stability_periods[:20]  # First 20 for detail
        }
    
    def _calculate_trend(self, data: List[float]) -> float:
        """Calculate linear trend (slope) of data."""
        if len(data) < 2:
            return 0.0
        
        x = np.arange(len(data))
        slope, _, _, _, _ = stats.linregress(x, data)
        
        # Normalize by mean
        mean = np.mean(data)
        if mean > 0:
            return slope / mean
        return 0.0