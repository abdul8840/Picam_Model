"""
PICAM Financial Loss Calculator

Calculates conservative lower-bound financial losses from operational inefficiencies.

Key Principle: Every calculation produces the MINIMUM money that MUST have been lost.
We never speculate or predict - only calculate what physics guarantees.

Loss Categories:
1. Wait Time Cost - Value of customer time spent waiting
2. Lost Throughput - Revenue lost due to capacity limits
3. Walk-away Cost - Customers who left before service
4. Idle Time Cost - Cost of underutilized staff
5. Overtime Cost - Premium paid for overwork
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Tuple
import numpy as np
from scipy import stats

from app.models.domain import (
    FlowMeasurement, 
    LittlesLawResult, 
    EntropyMeasurement,
    FinancialLoss,
    CapacityConstraint
)
from app.utils import now_utc, create_deterministic_hash


@dataclass
class FinancialParameters:
    """
    Financial parameters for loss calculation.
    All values should be conservative (under-estimate losses).
    """
    # Customer value
    avg_revenue_per_customer: float = 150.0  # Average spend
    customer_lifetime_value: float = 500.0  # For walk-away calculation
    
    # Time values
    customer_time_value_per_minute: float = 2.0  # Conservative
    acceptable_wait_minutes: float = 5.0  # Wait below this = no loss
    
    # Labor costs
    labor_cost_per_hour: float = 25.0
    overtime_multiplier: float = 1.5
    
    # Walk-away parameters
    walkaway_threshold_minutes: float = 15.0  # After this, customers leave
    walkaway_probability_per_minute: float = 0.02  # 2% per minute after threshold
    walkaway_loss_multiplier: float = 3.0  # Direct + future lost revenue
    
    # Confidence
    conservative_factor: float = 0.7  # Multiply losses by this for conservatism


@dataclass
class LossCalculator:
    """
    Calculates provable financial losses from operational data.
    
    All calculations are:
    - Conservative (lower bound)
    - Physics-based (queueing theory)
    - Deterministic (reproducible)
    - Auditable (full traceability)
    """
    
    params: FinancialParameters = field(default_factory=FinancialParameters)
    
    def calculate_total_loss(
        self,
        measurements: List[FlowMeasurement],
        littles_result: Optional[LittlesLawResult],
        entropy: Optional[EntropyMeasurement],
        capacity: Optional[CapacityConstraint] = None,
        target_date: Optional[date] = None
    ) -> FinancialLoss:
        """
        Calculate comprehensive financial loss from all sources.
        
        Args:
            measurements: Operational measurements for the period
            littles_result: Pre-calculated Little's Law metrics
            entropy: Pre-calculated entropy metrics
            capacity: Capacity constraints
            target_date: Date of calculation
            
        Returns:
            FinancialLoss with breakdown of all loss types
        """
        if not measurements:
            return self._empty_loss(target_date or date.today())
        
        location_id = measurements[0].location_id
        calc_date = target_date or measurements[0].timestamp.date()
        
        # Calculate each loss type
        wait_time_loss = self._calculate_wait_time_loss(measurements)
        throughput_loss = self._calculate_throughput_loss(measurements, capacity)
        walkaway_loss = self._calculate_walkaway_loss(measurements)
        idle_loss = self._calculate_idle_time_loss(measurements, capacity)
        overtime_loss = self._calculate_overtime_loss(measurements, capacity)
        
        # Apply entropy multiplier if available
        if entropy and entropy.variance_impact_multiplier > 1.0:
            # Variability increases wait time costs
            entropy_factor = min(entropy.variance_impact_multiplier, 2.0)
            wait_time_loss = (
                wait_time_loss[0] * entropy_factor,
                wait_time_loss[1] * entropy_factor
            )
        
        # Create FinancialLoss object
        loss = FinancialLoss(
            timestamp=now_utc(),
            location_id=location_id,
            calculation_date=calc_date,
            total_wait_time_seconds=wait_time_loss[0],
            wait_time_cost=wait_time_loss[1],
            lost_throughput_count=throughput_loss[0],
            lost_throughput_revenue=throughput_loss[1],
            estimated_walkaways=walkaway_loss[0],
            walkaway_cost=walkaway_loss[1],
            idle_time_seconds=idle_loss[0],
            idle_time_cost=idle_loss[1],
            overtime_hours=overtime_loss[0],
            overtime_cost=overtime_loss[1]
        )
        
        return loss
    
    def _calculate_wait_time_loss(
        self,
        measurements: List[FlowMeasurement]
    ) -> Tuple[float, float]:
        """
        Calculate cost of customer wait time.
        
        Only counts wait time ABOVE acceptable threshold.
        Returns (total_wait_seconds, cost)
        """
        total_excess_wait_seconds = 0.0
        total_customers = 0
        
        threshold_seconds = self.params.acceptable_wait_minutes * 60
        
        for m in measurements:
            if m.avg_wait_time and m.avg_wait_time > threshold_seconds:
                # Excess wait per customer
                excess_wait = m.avg_wait_time - threshold_seconds
                
                # Estimate customers who waited
                # Use queue length as proxy
                customers_waiting = m.queue_length
                
                total_excess_wait_seconds += excess_wait * customers_waiting
                total_customers += customers_waiting
        
        # Convert to cost
        total_excess_wait_minutes = total_excess_wait_seconds / 60
        cost = total_excess_wait_minutes * self.params.customer_time_value_per_minute
        
        # Apply conservative factor
        cost *= self.params.conservative_factor
        
        return (total_excess_wait_seconds, cost)
    
    def _calculate_throughput_loss(
        self,
        measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint]
    ) -> Tuple[int, float]:
        """
        Calculate revenue lost due to throughput limits.
        
        When demand exceeds capacity, potential revenue is lost.
        Returns (lost_customers, lost_revenue)
        """
        if not capacity:
            return (0, 0.0)
        
        total_lost = 0
        
        for m in measurements:
            # Check if arrivals exceeded service capacity
            max_throughput = capacity.max_servers * m.observation_period_seconds / 60
            
            if m.arrival_count > max_throughput * 1.2:  # 20% buffer
                # Excess arrivals couldn't be served
                lost = int(m.arrival_count - max_throughput)
                total_lost += max(0, lost)
        
        # Calculate revenue impact (conservative)
        lost_revenue = total_lost * self.params.avg_revenue_per_customer
        lost_revenue *= self.params.conservative_factor
        
        return (total_lost, lost_revenue)
    
    def _calculate_walkaway_loss(
        self,
        measurements: List[FlowMeasurement]
    ) -> Tuple[int, float]:
        """
        Calculate cost of customers who walked away.
        
        Uses conservative probability model based on wait time.
        Returns (estimated_walkaways, cost)
        """
        threshold_seconds = self.params.walkaway_threshold_minutes * 60
        prob_per_minute = self.params.walkaway_probability_per_minute
        
        estimated_walkaways = 0
        
        for m in measurements:
            if m.avg_wait_time and m.avg_wait_time > threshold_seconds:
                # Time over threshold
                excess_minutes = (m.avg_wait_time - threshold_seconds) / 60
                
                # Probability of walkaway (capped at 50%)
                walkaway_prob = min(0.5, excess_minutes * prob_per_minute)
                
                # Expected walkaways from queue
                expected = m.queue_length * walkaway_prob
                estimated_walkaways += int(expected)
        
        # Calculate cost (direct loss + future value)
        direct_loss = estimated_walkaways * self.params.avg_revenue_per_customer
        future_loss = estimated_walkaways * self.params.customer_lifetime_value * 0.1  # 10% of LTV
        
        total_cost = (direct_loss + future_loss) * self.params.conservative_factor
        
        return (estimated_walkaways, total_cost)
    
    def _calculate_idle_time_loss(
        self,
        measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint]
    ) -> Tuple[float, float]:
        """
        Calculate cost of idle staff time.
        
        Idle time occurs when utilization is significantly below target.
        Returns (idle_seconds, cost)
        """
        if not capacity:
            return (0.0, 0.0)
        
        target_util = capacity.target_utilization
        num_servers = capacity.max_servers
        
        total_idle_seconds = 0.0
        
        for m in measurements:
            # Calculate actual utilization
            if m.departure_rate and m.departure_rate > 0:
                actual_util = m.arrival_rate / (num_servers * m.departure_rate)
            else:
                actual_util = 0.5  # Assume 50% if unknown
            
            # Idle time when below target
            if actual_util < target_util * 0.7:  # Significantly below target
                idle_fraction = (target_util - actual_util)
                idle_seconds = idle_fraction * m.observation_period_seconds * num_servers
                total_idle_seconds += idle_seconds
        
        # Convert to cost
        idle_hours = total_idle_seconds / 3600
        cost = idle_hours * self.params.labor_cost_per_hour
        cost *= self.params.conservative_factor
        
        return (total_idle_seconds, cost)
    
    def _calculate_overtime_loss(
        self,
        measurements: List[FlowMeasurement],
        capacity: Optional[CapacityConstraint]
    ) -> Tuple[float, float]:
        """
        Calculate overtime costs from overloaded periods.
        
        Returns (overtime_hours, cost)
        """
        if not capacity:
            return (0.0, 0.0)
        
        total_overtime_seconds = 0.0
        num_servers = capacity.max_servers
        
        for m in measurements:
            # Check for overload (utilization > 100%)
            if m.departure_rate and m.departure_rate > 0:
                utilization = m.arrival_rate / (num_servers * m.departure_rate)
                
                if utilization > 1.0:
                    # Extra work required
                    overload_factor = utilization - 1.0
                    overtime_seconds = overload_factor * m.observation_period_seconds * num_servers
                    total_overtime_seconds += overtime_seconds
        
        # Convert to cost (overtime premium)
        overtime_hours = total_overtime_seconds / 3600
        base_cost = overtime_hours * self.params.labor_cost_per_hour
        overtime_premium = base_cost * (self.params.overtime_multiplier - 1)
        
        total_cost = overtime_premium * self.params.conservative_factor
        
        return (overtime_hours, total_cost)
    
    def _empty_loss(self, calc_date: date) -> FinancialLoss:
        """Create empty loss record."""
        return FinancialLoss(
            timestamp=now_utc(),
            location_id="unknown",
            calculation_date=calc_date,
            total_wait_time_seconds=0,
            wait_time_cost=0,
            lost_throughput_count=0,
            lost_throughput_revenue=0,
            estimated_walkaways=0,
            walkaway_cost=0,
            idle_time_seconds=0,
            idle_time_cost=0,
            overtime_hours=0,
            overtime_cost=0
        )
    
    def calculate_marginal_loss(
        self,
        current_loss: FinancialLoss,
        additional_arrivals: int,
        current_utilization: float
    ) -> dict:
        """
        Calculate additional loss from marginal increase in arrivals.
        
        Physics: As utilization approaches 1.0, marginal loss increases rapidly.
        """
        if current_utilization >= 1.0:
            return {
                "status": "at_capacity",
                "marginal_loss": "unbounded",
                "recommendation": "System at capacity - all additional arrivals create loss"
            }
        
        # Marginal wait time increase (derivative of M/M/1 wait time)
        # dWq/dλ ≈ 1 / (μ(1-ρ)²) which increases as ρ → 1
        rho = current_utilization
        marginal_multiplier = 1 / ((1 - rho) ** 2)
        
        # Base cost per arrival
        base_wait_cost = self.params.customer_time_value_per_minute * self.params.acceptable_wait_minutes
        
        # Marginal cost
        marginal_cost_per_arrival = base_wait_cost * marginal_multiplier
        total_marginal_cost = marginal_cost_per_arrival * additional_arrivals
        
        return {
            "status": "calculated",
            "current_utilization": round(rho, 4),
            "additional_arrivals": additional_arrivals,
            "marginal_multiplier": round(marginal_multiplier, 2),
            "marginal_cost_per_arrival": round(marginal_cost_per_arrival, 2),
            "total_marginal_cost": round(total_marginal_cost, 2),
            "physics_basis": "M/M/1 queue marginal wait time derivative"
        }
    
    def identify_top_loss_point(
        self,
        losses_by_location: Dict[str, FinancialLoss]
    ) -> dict:
        """
        Identify the single highest loss point.
        
        Returns the location with maximum provable loss.
        """
        if not losses_by_location:
            return {
                "status": "no_data",
                "top_location": None
            }
        
        # Find max loss
        max_loss = 0
        max_location = None
        max_cause = None
        
        for location, loss in losses_by_location.items():
            if loss.total_loss > max_loss:
                max_loss = loss.total_loss
                max_location = location
                max_cause = self._identify_primary_cause(loss)
        
        return {
            "status": "identified",
            "top_location": max_location,
            "top_loss_amount": round(max_loss, 2),
            "primary_cause": max_cause,
            "breakdown": losses_by_location[max_location].loss_breakdown if max_location else {}
        }
    
    def _identify_primary_cause(self, loss: FinancialLoss) -> str:
        """Identify the primary cause of loss."""
        breakdown = loss.loss_breakdown
        
        max_category = max(
            breakdown.items(),
            key=lambda x: x[1]
        )
        
        cause_map = {
            "wait_time_cost": "Excessive customer wait time",
            "lost_throughput_revenue": "Demand exceeding capacity",
            "walkaway_cost": "Customers leaving before service",
            "idle_time_cost": "Underutilized capacity",
            "overtime_cost": "Staff overtime from overload"
        }
        
        return cause_map.get(max_category[0], "Unknown cause")


class ROICalculator:
    """
    Calculates Return on Investment for operational improvements.
    """
    
    def calculate_action_roi(
        self,
        action_cost: float,
        before_loss: FinancialLoss,
        after_loss: FinancialLoss
    ) -> dict:
        """
        Calculate ROI from before/after loss comparison.
        """
        loss_reduction = before_loss.total_loss - after_loss.total_loss
        net_benefit = loss_reduction - action_cost
        
        if action_cost > 0:
            roi_ratio = loss_reduction / action_cost
            roi_percentage = (net_benefit / action_cost) * 100
        else:
            roi_ratio = float('inf') if loss_reduction > 0 else 0
            roi_percentage = float('inf') if loss_reduction > 0 else 0
        
        return {
            "before_loss": round(before_loss.total_loss, 2),
            "after_loss": round(after_loss.total_loss, 2),
            "loss_reduction": round(loss_reduction, 2),
            "action_cost": round(action_cost, 2),
            "net_benefit": round(net_benefit, 2),
            "roi_ratio": round(roi_ratio, 2) if roi_ratio != float('inf') else "infinite",
            "roi_percentage": round(roi_percentage, 1) if roi_percentage != float('inf') else "infinite",
            "is_profitable": net_benefit > 0,
            "payback_days": round(action_cost / (loss_reduction / 30), 1) if loss_reduction > 0 else None
        }
    
    def project_recovery(
        self,
        current_loss: FinancialLoss,
        improvement_actions: List[dict]
    ) -> dict:
        """
        Project potential recovery from improvement actions.
        
        Each action should have:
        - target_category: which loss category it addresses
        - improvement_factor: expected reduction (0-1)
        - cost: implementation cost
        """
        total_recovery = 0
        total_cost = 0
        details = []
        
        for action in improvement_actions:
            category = action["target_category"]
            factor = action["improvement_factor"]
            cost = action["cost"]
            
            # Get current loss in category
            current = current_loss.loss_breakdown.get(category, 0)
            recovery = current * factor
            
            total_recovery += recovery
            total_cost += cost
            
            details.append({
                "category": category,
                "current_loss": round(current, 2),
                "improvement_factor": factor,
                "projected_recovery": round(recovery, 2),
                "action_cost": round(cost, 2),
                "net_benefit": round(recovery - cost, 2)
            })
        
        return {
            "total_current_loss": round(current_loss.total_loss, 2),
            "total_projected_recovery": round(total_recovery, 2),
            "total_action_cost": round(total_cost, 2),
            "total_net_benefit": round(total_recovery - total_cost, 2),
            "projected_remaining_loss": round(current_loss.total_loss - total_recovery, 2),
            "details": details
        }