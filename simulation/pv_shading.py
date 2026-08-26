import numpy as np
import pandas as pd
from typing import Dict, Any

class PVShading:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        geom = self.config.get('pv_geometry', {}).get('baseline_virtual_geometry', {})
        panel = geom.get('panel', {})
        self.tilt_deg = panel.get('tilt_deg', 15.0)
        self.azimuth_deg = panel.get('azimuth_deg', 180.0)
        self.length_m = panel.get('length_m', 2.0)  # slanted length
        
        mounting = geom.get('mounting', {})
        self.h_lower = mounting.get('lower_edge_height_m', 2.5)
        
        array = geom.get('array', {})
        self.pitch_m = array.get('row_pitch_m', 6.0)
        
        shading_cfg = self.config.get('pv_geometry', {}).get('shading', {})
        self.full_shade_threshold = shading_cfg.get('full_shade_threshold', 0.80)

    def calculate_shade_fraction(self, solar_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates the shade fraction (0 to 1) for the Zone B sensor area.
        We'll use a 1D shadow band approach for infinite rows.
        """
        solar_elevation = np.radians(solar_df['solar_elevation_deg'].values)
        solar_azimuth = np.radians(solar_df['solar_azimuth_deg'].values)
        
        panel_tilt = np.radians(self.tilt_deg)
        panel_az = np.radians(self.azimuth_deg)
        
        # Calculate shadow length on horizontal ground cast by a single row
        # Height of the upper edge
        h_upper = self.h_lower + self.length_m * np.sin(panel_tilt)
        
        # The horizontal projection of the panel width
        w_proj = self.length_m * np.cos(panel_tilt)
        
        shade_fraction = np.zeros(len(solar_df))
        
        for i in range(len(solar_df)):
            if solar_elevation[i] <= 0:
                shade_fraction[i] = 0.0 # Night time
                continue
                
            # Angle of the sun relative to the panel azimuth
            az_diff = solar_azimuth[i] - panel_az
            
            # If sun is behind the panels, it's complex, but for 15 deg tilt facing South (180),
            # in summer morning/evening sun is north of E/W. 
            # We simplify to the projected length of the shadow along the ground perpendicular to the rows.
            
            # Profile angle (angle of sun projected onto a N-S vertical plane if rows are E-W)
            # Tan(profile_angle) = Tan(elevation) / Cos(az_diff)
            cos_az_diff = np.cos(az_diff)
            if cos_az_diff == 0:
                cos_az_diff = 1e-6
                
            tan_profile = np.tan(solar_elevation[i]) / np.abs(cos_az_diff)
            profile_angle = np.arctan(tan_profile)
            
            if profile_angle <= 0:
                # Sun is behind the array or below horizon
                shade_fraction[i] = 1.0
                continue
                
            # Shadow length perpendicular to the row
            shadow_length = h_upper / np.tan(profile_angle)
            
            # The shadow covers a certain width on the ground.
            # Due to overlapping rows, the shadow band width is min(shadow_length, pitch)
            # Actually, the shadow starts at the lower edge projection and ends at the upper edge shadow.
            # The base shadow width on the horizontal ground is the projection of the panel
            # plus the length cast by the vertical height of the tilted panel.
            shadow_width = self.length_m * np.cos(panel_tilt) + (self.length_m * np.sin(panel_tilt)) / np.tan(profile_angle)
            
            # This is a simplification. For a representative area under the panels,
            # the fraction of ground shaded is approximately the shadow width divided by pitch.
            sf = min(1.0, max(0.0, shadow_width / self.pitch_m))
            
            # In real agrivoltaics, the shadow moves over the sensor. 
            # To emulate a continuous fraction (e.g. spatial average over the plot), we use sf.
            shade_fraction[i] = sf

        df = pd.DataFrame({'shade_fraction': shade_fraction})
        df['full_shade_flag'] = (df['shade_fraction'] >= self.full_shade_threshold).astype(int)
        
        return df
