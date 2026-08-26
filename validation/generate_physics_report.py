import os
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def generate_report(input_dir="outputs", output_dir="outputs", artifact_dir=None):
    os.makedirs(output_dir, exist_ok=True)
    if artifact_dir:
        os.makedirs(artifact_dir, exist_ok=True)
        
    print(f"Loading data from {input_dir}...")
    df_5min = pd.read_parquet(os.path.join(input_dir, "truth_5min.parquet"))
    df_daily = pd.read_parquet(os.path.join(input_dir, "daily_agro.parquet"))
    
    print("Calculating validation statistics...")
    
    # Validation Statistics
    is_day = df_5min['Rs_A'] > 0
    is_night = ~is_day
    
    # Calculate Water Balance Components
    # Delta S = P_eff + IR - ETc - D - R
    # In 5-min, P_surface is what reaches the ground (P_incident - interception)
    # Wait, df_5min doesn't explicitly store P_eff, it stores P_surface as 'P_A'/'P_B' maybe?
    # Let's check columns: 'P_A', 'P_B', 'Runoff_mm_A', 'Drainage_mm_A', 'ETc_mm_A'
    
    stats = []
    
    for zone in ['A', 'B']:
        z = {}
        z['Zone'] = zone
        z['Mean T'] = df_5min[f'T_{zone}'].mean()
        z['Mean daytime T'] = df_5min.loc[is_day, f'T_{zone}'].mean()
        z['Mean nighttime T'] = df_5min.loc[is_night, f'T_{zone}'].mean()
        z['Mean RH'] = df_5min[f'RH_{zone}'].mean()
        z['Mean VPD'] = df_5min[f'VPD_{zone}'].mean()
        z['Mean Rs'] = df_5min[f'Rs_{zone}'].mean()
        
        if zone == 'B':
            z['Mean shade fraction'] = df_5min['shade_fraction'].mean()
            z['% full-shade timesteps'] = (df_5min['full_shade_flag'].sum() / len(df_5min)) * 100.0
        else:
            z['Mean shade fraction'] = 0.0
            z['% full-shade timesteps'] = 0.0
            
        z['Mean soil temperature'] = df_5min[f'Tsoil_{zone}'].mean()
        z['Mean soil moisture'] = df_5min[f'theta_v_{zone}'].mean()
        z['Min soil moisture'] = df_5min[f'theta_v_{zone}'].min()
        z['Max soil moisture'] = df_5min[f'theta_v_{zone}'].max()
        
        # Hydrology (Sum over 5-min)
        # Note: P_A / P_B was stored in weather_engine but wait, did we store it?
        # In run_physics_validation.py we did: weather_df['P_A'] = p_surface_A
        z['Total incident precipitation'] = df_5min[f'P_{zone}'].sum()
        z['Effective precipitation (surface)'] = z['Total incident precipitation']
        z['Total ETc'] = df_5min[f'ETc_mm_{zone}'].sum()
        z['Total drainage'] = df_5min[f'Drainage_mm_{zone}'].sum()
        z['Total runoff'] = df_5min[f'Runoff_mm_{zone}'].sum()
        
        # Soil storage change
        S_start = df_5min[f'S_mm_{zone}'].iloc[0]
        S_end = df_5min[f'S_mm_{zone}'].iloc[-1]
        delta_S = S_end - S_start
        
        z['Water-balance residual'] = z['Effective precipitation (surface)'] - z['Total ETc'] - z['Total drainage'] - z['Total runoff'] - delta_S
        
        # Agronomy
        z['Final biomass'] = df_daily[f'Biomass_g_{zone}'].iloc[-1]
        
        # Yield is not directly in daily_agro, it's calculated at the end. We can recompute HI * Biomass
        hi_base = 0.35
        # Sum of APAR
        z['Cumulative APAR (MJ/m2)'] = df_daily[f'APAR_{zone}'].sum() if f'APAR_{zone}' in df_daily.columns else 0.0
        
        critical_stages = (df_daily[f'phenology_stage_{zone}'] == 2) | (df_daily[f'phenology_stage_{zone}'] == 3)
        mean_ks = df_daily.loc[critical_stages, f'Ks_{zone}'].mean() if critical_stages.any() else 1.0
        z['Mean Ks (critical stages)'] = mean_ks
        z['Stress days (Ks < 0.8)'] = (df_daily[f'Ks_{zone}'] < 0.8).sum()
        
        hi_actual = hi_base * (0.5 + 0.5 * mean_ks)
        z['Final yield'] = z['Final biomass'] * hi_actual
        
        stats.append(z)
        
    df_stats = pd.DataFrame(stats).set_index('Zone').T
    
    # Calculate Deltas
    df_stats['Delta (A - B)'] = df_stats['A'] - df_stats['B']
    
    csv_path = os.path.join(output_dir, "physics_validation_report.csv")
    df_stats.to_csv(csv_path)
    print(f"Saved validation report to {csv_path}")
    
    # --- Generate Figures ---
    print("Generating Figures A-H...")
    
    # Subset for 5 days for clarity in some plots
    idx_5d = df_5min.index[:288*5]
    df_5d = df_5min.iloc[:288*5]
    
    # Helper to save figure
    def save_fig(fig, filename):
        fig.tight_layout()
        filepath = os.path.join(output_dir, filename)
        fig.savefig(filepath, dpi=150)
        if artifact_dir:
            fig.savefig(os.path.join(artifact_dir, filename), dpi=150)
        plt.close(fig)

    # Figure A: Dual-zone air microclimate (3-day snippet)
    df_3d = df_5min.iloc[288*10:288*13] # Pick days 10-13 to avoid start transients
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.plot(df_3d['timestamp'], df_3d['T_A'], label='Zone A (Open)', color='orange')
    ax1.plot(df_3d['timestamp'], df_3d['T_B'], label='Zone B (Panels)', color='blue', alpha=0.7)
    ax1.set_ylabel('Air Temperature (°C)')
    ax1.legend()
    ax1.set_title('Figure A - Air Microclimate (3-day window)')
    
    ax2.plot(df_3d['timestamp'], df_3d['RH_A'], label='Zone A', color='orange')
    ax2.plot(df_3d['timestamp'], df_3d['RH_B'], label='Zone B', color='blue', alpha=0.7)
    ax2.set_ylabel('Relative Humidity (%)')
    save_fig(fig, 'figure_a.png')

    # Figure B: Radiation and PV Shading
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.plot(df_3d['timestamp'], df_3d['Rs_A'], label='Rs Zone A', color='orange')
    ax1.plot(df_3d['timestamp'], df_3d['Rs_B'], label='Rs Zone B', color='blue', alpha=0.7)
    ax1.set_ylabel('Total Irradiance (W/m2)')
    ax1.set_title('Figure B - Radiation and Shading')
    ax1.legend()
    
    ax2.plot(df_3d['timestamp'], df_3d['shade_fraction'], label='Shade Fraction', color='black')
    ax2.fill_between(df_3d['timestamp'], 0, df_3d['full_shade_flag'], color='gray', alpha=0.3, label='Full Shade Flag')
    ax2.set_ylabel('Fraction [0-1]')
    ax2.legend()
    save_fig(fig, 'figure_b.png')
    
    # Figure C: VPD
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df_3d['timestamp'], df_3d['VPD_A'], label='VPD A', color='orange')
    ax.plot(df_3d['timestamp'], df_3d['VPD_B'], label='VPD B', color='blue', alpha=0.7)
    ax.set_ylabel('VPD (kPa)')
    ax.set_title('Figure C - Vapor Pressure Deficit')
    ax.legend()
    save_fig(fig, 'figure_c.png')
    
    # Figure D: Soil thermal response (full 70 days or 10 days?)
    df_10d = df_5min.iloc[:288*10]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_10d['timestamp'], df_10d['T_A'], label='Air Temp A', color='gray', alpha=0.3)
    ax.plot(df_10d['timestamp'], df_10d['Tsoil_A'], label='Soil Temp A', color='orange')
    ax.plot(df_10d['timestamp'], df_10d['Tsoil_B'], label='Soil Temp B', color='blue')
    ax.set_ylabel('Temperature (°C)')
    ax.set_title('Figure D - Soil Thermal Response (10 days)')
    ax.legend()
    save_fig(fig, 'figure_d.png')
    
    # Figure E: Soil moisture dynamics
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_5min['timestamp'], df_5min['theta_v_A'], label='Moisture A', color='orange')
    ax.plot(df_5min['timestamp'], df_5min['theta_v_B'], label='Moisture B', color='blue')
    ax.axhline(0.27, color='green', linestyle='--', label='Field Capacity')
    ax.axhline(0.12, color='red', linestyle='--', label='Wilting Point')
    ax.set_ylabel('Volumetric Water Content')
    ax.set_title('Figure E - Soil Moisture Dynamics')
    ax.legend()
    save_fig(fig, 'figure_e.png')
    
    # Figure F: GDD, Phenology, Kc
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    ax1.plot(df_daily.index, df_daily['cumulative_gdd_A'], label='GDD A', color='orange')
    ax1.plot(df_daily.index, df_daily['cumulative_gdd_B'], label='GDD B', color='blue')
    ax1.set_ylabel('Cumulative GDD')
    ax1.set_title('Figure F - Crop Development')
    ax1.legend()
    
    ax2.plot(df_daily.index, df_daily['phenology_stage_A'], label='Stage A', color='orange', linestyle='--')
    ax2.plot(df_daily.index, df_daily['phenology_stage_B'], label='Stage B', color='blue', linestyle='--')
    ax2.set_ylabel('Phenology Stage')
    ax2.legend()
    save_fig(fig, 'figure_f.png')
    
    # Figure G: Water demand components (10 days)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(df_10d['timestamp'], df_10d['ET_demand_5min_A'], label='Demand A', color='orange')
    ax.plot(df_10d['timestamp'], df_10d['ET_demand_5min_B'], label='Demand B', color='blue')
    ax.plot(df_10d['timestamp'], df_10d['ETc_mm_A'], label='ETc A', color='red', alpha=0.5)
    ax.plot(df_10d['timestamp'], df_10d['ETc_mm_B'], label='ETc B', color='purple', alpha=0.5)
    ax.set_ylabel('ET (mm/5min)')
    ax.set_title('Figure G - Water Demand Components (10 days)')
    ax.legend()
    save_fig(fig, 'figure_g.png')
    
    # Figure H: Water balance (Cumulative)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    for ax, zone, color in zip([ax1, ax2], ['A', 'B'], ['orange', 'blue']):
        p_cum = df_5min[f'P_{zone}'].cumsum()
        etc_cum = df_5min[f'ETc_mm_{zone}'].cumsum()
        drain_cum = df_5min[f'Drainage_mm_{zone}'].cumsum()
        runoff_cum = df_5min[f'Runoff_mm_{zone}'].cumsum()
        ds_cum = df_5min[f'S_mm_{zone}'] - df_5min[f'S_mm_{zone}'].iloc[0]
        
        ax.plot(df_5min['timestamp'], p_cum, label='Cumulative Rainfall', color='blue')
        ax.plot(df_5min['timestamp'], etc_cum, label='Cumulative ETc', color='green')
        ax.plot(df_5min['timestamp'], drain_cum, label='Cumulative Drainage', color='purple')
        ax.plot(df_5min['timestamp'], runoff_cum, label='Cumulative Runoff', color='red')
        ax.plot(df_5min['timestamp'], ds_cum, label='Change in Storage', color='brown')
        ax.set_title(f'Figure H - Water Balance (Zone {zone})')
        ax.set_ylabel('mm')
        ax.legend()
        
    save_fig(fig, 'figure_h.png')
    print("All figures generated successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="outputs")
    parser.add_argument("--output_dir", default="outputs")
    parser.add_argument("--artifact_dir", default=None)
    args = parser.parse_args()
    
    generate_report(args.input_dir, args.output_dir, args.artifact_dir)
