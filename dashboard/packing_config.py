"""
Packing Engine Configuration Module

This module provides configuration options for selecting and configuring
different packing engines (LIFO vs DBL).
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class PackingEngineType(Enum):
    """Available packing engine types."""
    LIFO = "lifo"  # Legacy First-Fit Decreasing with LIFO sorting
    DBL = "dbl"    # Deepest-Bottom-Left with gravity constraints


@dataclass
class PackingConfig:
    """
    Configuration for packing engine behavior.
    
    This configuration allows switching between different packing algorithms
    and adjusting their parameters.
    """
    # Engine selection
    engine_type: PackingEngineType = PackingEngineType.DBL
    
    # DBL-specific parameters
    support_threshold: float = 0.80  # 80% support requirement
    weight_ratio_max: float = 1.5    # Maximum weight ratio for stacking
    tolerance: float = 0.001         # Floating-point comparison tolerance
    max_contact_points: Optional[int] = None  # Limit contact points for performance (None = unlimited)
    
    # Future: Package rotation
    enable_rotation: bool = False    # Allow package rotation (not yet implemented)
    
    def __post_init__(self):
        """Validate configuration parameters."""
        if not isinstance(self.engine_type, PackingEngineType):
            raise ValueError(f"engine_type must be PackingEngineType, got {type(self.engine_type)}")
        
        if not 0.0 < self.support_threshold <= 1.0:
            raise ValueError(f"support_threshold must be in (0, 1], got {self.support_threshold}")
        
        if self.weight_ratio_max <= 0:
            raise ValueError(f"weight_ratio_max must be positive, got {self.weight_ratio_max}")
        
        if self.tolerance <= 0:
            raise ValueError(f"tolerance must be positive, got {self.tolerance}")
        
        if self.max_contact_points is not None and self.max_contact_points <= 0:
            raise ValueError(f"max_contact_points must be positive or None, got {self.max_contact_points}")
    
    @classmethod
    def create_lifo_config(cls) -> 'PackingConfig':
        """Create configuration for legacy LIFO engine."""
        return cls(engine_type=PackingEngineType.LIFO)
    
    @classmethod
    def create_dbl_config(
        cls,
        support_threshold: float = 0.80,
        weight_ratio_max: float = 1.5,
        max_contact_points: Optional[int] = None
    ) -> 'PackingConfig':
        """
        Create configuration for DBL engine with custom parameters.
        
        Args:
            support_threshold: Minimum support ratio (0-1)
            weight_ratio_max: Maximum weight ratio for stacking
            max_contact_points: Maximum number of contact points to maintain.
                              None (default) = unlimited for best quality.
                              Lower values (e.g., 10-30) improve speed but may reduce quality.
            
        Returns:
            PackingConfig configured for DBL engine
        """
        return cls(
            engine_type=PackingEngineType.DBL,
            support_threshold=support_threshold,
            weight_ratio_max=weight_ratio_max,
            max_contact_points=max_contact_points
        )
    
    def get_display_name(self) -> str:
        """Get human-readable name for the selected engine."""
        if self.engine_type == PackingEngineType.LIFO:
            return "LIFO (First-Fit Decreasing)"
        elif self.engine_type == PackingEngineType.DBL:
            return "DBL (Deepest-Bottom-Left with Gravity)"
        else:
            return "Unknown Engine"
    
    def get_description(self) -> str:
        """Get description of the selected engine."""
        if self.engine_type == PackingEngineType.LIFO:
            return (
                "Legacy packing algorithm using First-Fit Decreasing heuristic. "
                "Sorts packages by volume and places them at the first available position. "
                "Fast but may not respect gravity constraints."
            )
        elif self.engine_type == PackingEngineType.DBL:
            cp_limit = "unlimited" if self.max_contact_points is None else str(self.max_contact_points)
            return (
                f"Advanced packing algorithm with strict physics constraints. "
                f"Enforces {int(self.support_threshold * 100)}% support rule and "
                f"{self.weight_ratio_max}x weight ratio limit. "
                f"Contact point limit: {cp_limit}. "
                f"Produces stable, realistic load configurations."
            )
        else:
            return "Unknown packing engine"


def get_default_config() -> PackingConfig:
    """Get the default packing configuration (DBL engine)."""
    return PackingConfig.create_dbl_config()


def get_lifo_config() -> PackingConfig:
    """Get configuration for legacy LIFO engine."""
    return PackingConfig.create_lifo_config()
