import numpy as np
from typing import Dict, Any

class RainfallPartition:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        rp_config = self.config.get('rainfall_partition', {})
        self.zone_a_interception = rp_config.get('zone_a', {}).get('interception_fraction', 0.0)
        
        zb_config = rp_config.get('zone_b', {})
        self.panel_interception_enabled = zb_config.get('panel_interception', {}).get('enabled', True)
        self.panel_interception_fraction = zb_config.get('panel_interception', {}).get('nominal_fraction', 0.10)
        
        self.edge_concentration_enabled = zb_config.get('edge_concentration', {}).get('enabled', True)
        self.use_for_central_zone = zb_config.get('edge_concentration', {}).get('use_for_central_zone', False)
        
    def partition(self, p_incident: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculates the precipitation reaching the soil surface for Zone A and Zone B.
        Returns: (P_surface_A, P_surface_B)
        """
        # Zone A: Open field
        p_surface_a = p_incident * (1.0 - self.zone_a_interception)
        
        # Zone B: Under PV array
        if self.panel_interception_enabled:
            # Base interception
            interception_loss = p_incident * self.panel_interception_fraction
            p_surface_b = p_incident - interception_loss
            
            # If the sensor is at the edge and receives concentrated runoff
            if self.edge_concentration_enabled and self.use_for_central_zone:
                # Add back intercepted water (simplified)
                p_surface_b += interception_loss
        else:
            p_surface_b = np.copy(p_incident)
            
        return p_surface_a, p_surface_b
