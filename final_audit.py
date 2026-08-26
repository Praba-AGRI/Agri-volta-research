import os
import pandas as pd
import numpy as np

def generate_audit():
    df_5min = pd.read_parquet(os.path.join("outputs", "truth_5min.parquet"))
    df_daily = pd.read_parquet(os.path.join("outputs", "daily_agro.parquet"))

    audit = {}

    # Masks
    is_day = df_5min['Rs_A'] > 0
    sf25 = df_5min['shade_fraction'] > 0.25
    sf50 = df_5min['shade_fraction'] > 0.50
    sf75 = df_5min['shade_fraction'] > 0.75
    rs600 = df_5min['Rs_A'] > 600
    rs800 = df_5min['Rs_A'] > 800

    def get_diff(col1, col2, mask):
        sub = df_5min[mask]
        if len(sub) == 0: return np.nan
        return (sub[col1] - sub[col2]).mean()

    # Microclimate T (A - B)
    audit['daytime_delta_T'] = get_diff('T_A', 'T_B', is_day)
    audit['shade25_delta_T'] = get_diff('T_A', 'T_B', sf25)
    audit['shade50_delta_T'] = get_diff('T_A', 'T_B', sf50)
    audit['shade75_delta_T'] = get_diff('T_A', 'T_B', sf75)
    audit['highRs_delta_T'] = get_diff('T_A', 'T_B', rs600)

    # Microclimate RH (B - A)
    audit['daytime_delta_RH'] = get_diff('RH_B', 'RH_A', is_day)
    audit['shade25_delta_RH'] = get_diff('RH_B', 'RH_A', sf25)
    audit['shade50_delta_RH'] = get_diff('RH_B', 'RH_A', sf50)
    audit['shade75_delta_RH'] = get_diff('RH_B', 'RH_A', sf75)
    audit['highRs_delta_RH'] = get_diff('RH_B', 'RH_A', rs600)

    # Microclimate VPD (A - B)
    audit['daytime_delta_VPD'] = get_diff('VPD_A', 'VPD_B', is_day)
    audit['shade25_delta_VPD'] = get_diff('VPD_A', 'VPD_B', sf25)
    audit['shade50_delta_VPD'] = get_diff('VPD_A', 'VPD_B', sf50)
    audit['shade75_delta_VPD'] = get_diff('VPD_A', 'VPD_B', sf75)

    # Radiation
    audit['Rs_direct_A'] = df_5min['Rs_dir_A'].mean()
    audit['Rs_direct_B'] = df_5min['Rs_dir_B'].mean()
    audit['Rs_diffuse_A'] = df_5min['Rs_dif_A'].mean()
    audit['Rs_diffuse_B'] = df_5min['Rs_dif_B'].mean()
    audit['Rs_total_A'] = df_5min['Rs_A'].mean()
    audit['Rs_total_B'] = df_5min['Rs_B'].mean()
    
    audit['shade_mean'] = df_5min['shade_fraction'].mean()
    audit['shade_p95'] = df_5min['shade_fraction'].quantile(0.95)
    audit['shade_max'] = df_5min['shade_fraction'].max()
    audit['full_shade_fraction'] = df_5min['full_shade_flag'].sum() / len(df_5min)

    # Hydrology (Using Zone B for the general structure, but I will make it explicit)
    # The user asked for P_above_array, P_intercepted, P_surface.
    # In my code, P_A is incident (open), P_B is surface (shaded).
    p_incident_A = df_5min['P_A'].sum()
    p_surface_B = df_5min['P_B'].sum()
    
    audit['P_above_array'] = p_incident_A
    audit['P_intercepted'] = p_incident_A - p_surface_B
    audit['P_surface_A'] = p_incident_A
    audit['P_surface_B'] = p_surface_B
    
    audit['runoff_A'] = df_5min['Runoff_mm_A'].sum()
    audit['runoff_B'] = df_5min['Runoff_mm_B'].sum()
    audit['drainage_A'] = df_5min['Drainage_mm_A'].sum()
    audit['drainage_B'] = df_5min['Drainage_mm_B'].sum()
    audit['ETc_A'] = df_5min['ETc_mm_A'].sum()
    audit['ETc_B'] = df_5min['ETc_mm_B'].sum()
    audit['irrigation'] = 0.0
    
    ds_a = df_5min['S_mm_A'].iloc[-1] - df_5min['S_mm_A'].iloc[0]
    ds_b = df_5min['S_mm_B'].iloc[-1] - df_5min['S_mm_B'].iloc[0]
    audit['delta_storage_A'] = ds_a
    audit['delta_storage_B'] = ds_b
    
    audit['water_balance_residual_A'] = audit['P_surface_A'] - audit['ETc_A'] - audit['drainage_A'] - audit['runoff_A'] - ds_a
    audit['water_balance_residual_B'] = audit['P_surface_B'] - audit['ETc_B'] - audit['drainage_B'] - audit['runoff_B'] - ds_b

    # Crop
    apar_a = df_daily['APAR_MJ_A'].sum()
    apar_b = df_daily['APAR_MJ_B'].sum()
    audit['APAR_A'] = apar_a
    audit['APAR_B'] = apar_b
    audit['APAR_reduction_percent'] = (apar_a - apar_b) / apar_a * 100 if apar_a > 0 else 0.0
    
    c_stages_a = (df_daily['phenology_stage_A'] == 2) | (df_daily['phenology_stage_A'] == 3)
    c_stages_b = (df_daily['phenology_stage_B'] == 2) | (df_daily['phenology_stage_B'] == 3)
    
    audit['Ks_A'] = df_daily.loc[c_stages_a, 'Ks_A'].mean() if c_stages_a.any() else 1.0
    audit['Ks_B'] = df_daily.loc[c_stages_b, 'Ks_B'].mean() if c_stages_b.any() else 1.0
    
    audit['stress_days_A'] = (df_daily['Ks_A'] < 0.8).sum()
    audit['stress_days_B'] = (df_daily['Ks_B'] < 0.8).sum()
    
    audit['biomass_A'] = df_daily['Biomass_g_A'].iloc[-1]
    audit['biomass_B'] = df_daily['Biomass_g_B'].iloc[-1]
    
    # We must recompute Yield exactly as generate_physics_report did
    hi_base = 0.35
    audit['yield_A'] = audit['biomass_A'] * hi_base * (0.5 + 0.5 * audit['Ks_A'])
    audit['yield_B'] = audit['biomass_B'] * hi_base * (0.5 + 0.5 * audit['Ks_B'])

    # Save to CSV
    df_audit = pd.DataFrame([audit]).T
    df_audit.columns = ['Value']
    df_audit.to_csv('run1_final_audit.csv')
    
    print("run1_final_audit.csv generated successfully.")
    
    # Also print beautifully for quick inspection
    for k, v in audit.items():
        print(f"{k}: {v:.4f}")

if __name__ == "__main__":
    generate_audit()
