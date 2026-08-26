import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
import torch

from core.config_loader import load_all_configs
from core.random_state import SimulationRandomState
from simulation.solar_engine import SolarEngine
from simulation.weather_engine import WeatherEngine
from simulation.rainfall_model import RainfallModel
from simulation.rainfall_partition import RainfallPartition
from simulation.pv_shading import PVShading
from simulation.spectral_engine import SpectralEngine
from simulation.microclimate import Microclimate
from agronomy.et0 import ET0Model
from agronomy.et_demand import ETDemandModel
from agronomy.gdd import GDDModel
from agronomy.phenology import PhenologyModel
from agronomy.kc import KcModel
from agronomy.soil_water import SoilWaterBalance
from agronomy.crop_growth import CropGrowthModel
from agronomy.yield_model import YieldModel
from simulation.sensor_emulator import SensorEmulator
from ml.bilstm import BiLSTMModel
from irrigation.policies import FixedCalendarPolicy, ThresholdIoTPolicy, ProposedAIPolicy

def calculate_water_balance_residual(soil_df, p_surface):
    # ΔS = P_eff + IR - ETc - D - R
    # P_eff is just infiltration = min(P + IR, Ksat)
    # wait, P_eff is already P_surface - Runoff if there's no irrigation.
    # Actually, df gives S_mm, Runoff, Drainage, ETc, Irrigation
    # Initial storage is at t=0 before process, but let's just sum fluxes:
    delta_S = soil_df['S_mm'].iloc[-1] - soil_df['S_mm'].iloc[0]
    total_P = np.sum(p_surface)
    total_IR = np.sum(soil_df['Irrigation_mm'])
    total_ETc = np.sum(soil_df['ETc_mm'])
    total_D = np.sum(soil_df['Drainage_mm'])
    total_R = np.sum(soil_df['Runoff_mm'])
    
    residual = delta_S - (total_P + total_IR - total_ETc - total_D - total_R)
    return residual

def run_irrigation_smoke(config_dir="config", output_dir="outputs/run3"):
    print("Starting RUN 3A (Irrigation Smoke Test)...")
    config_obj = load_all_configs(Path(config_dir))
    config = config_obj.to_dict()
    os.makedirs(output_dir, exist_ok=True)
    
    days = 70
    timestep = config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)
    timesteps_per_day = 1440 // timestep
    num_timesteps = days * timesteps_per_day
    
    rs = SimulationRandomState(42)
    rs.set_season(1)
    
    print("Pre-computing environmental variables...")
    solar_engine = SolarEngine(config)
    solar_df = solar_engine.calculate_solar_position(num_timesteps)
    weather_engine = WeatherEngine(config, rs.get_generator(0))
    weather_df = weather_engine.generate_weather(num_timesteps, mode="full")
    rain_model = RainfallModel(config, rs.get_generator(1))
    p_incident = rain_model.generate_incident_rainfall(weather_df, mode="full")
    rain_partition = RainfallPartition(config)
    p_surface_A, p_surface_B = rain_partition.partition(p_incident)
    weather_df['P_A'] = p_surface_A
    weather_df['P_B'] = p_surface_B
    shading_engine = PVShading(config)
    shading_df = shading_engine.calculate_shade_fraction(solar_df)
    spectral_engine = SpectralEngine(config, rs.get_generator(2))
    rad_df = spectral_engine.calculate_radiation(weather_df, solar_df, shading_df)
    microclimate = Microclimate(config)
    mc_df = microclimate.calculate_microclimate(weather_df, rad_df, shading_df)
    
    true_5min = pd.concat([weather_df, solar_df, shading_df, rad_df, mc_df], axis=1)
    true_5min['timestamp'] = pd.date_range("2026-06-01 00:00:00", periods=num_timesteps, freq=f"{timestep}min")
    
    et_demand_model = ETDemandModel(config)
    et_demand_A = et_demand_model.calculate_zone_demand(true_5min, 'A')
    et_demand_B = et_demand_model.calculate_zone_demand(true_5min, 'B')
    true_5min = pd.concat([true_5min, et_demand_A, et_demand_B], axis=1)
    
    daily_tmean_A = true_5min['T_A'].values.reshape(days, timesteps_per_day).mean(axis=1)
    daily_tmean_B = true_5min['T_B'].values.reshape(days, timesteps_per_day).mean(axis=1)
    gdd_model = GDDModel(config)
    cum_gdd_A = gdd_model.calculate_cumulative_gdd(daily_tmean_A)
    cum_gdd_B = gdd_model.calculate_cumulative_gdd(daily_tmean_B)
    kc_model = KcModel(config)
    kc_A_daily = kc_model.calculate_kc(cum_gdd_A)
    kc_B_daily = kc_model.calculate_kc(cum_gdd_B)
    kc_A_5min = np.repeat(kc_A_daily, timesteps_per_day)
    kc_B_5min = np.repeat(kc_B_daily, timesteps_per_day)
    
    # Pre-compute environmental features for AI (Zone B)
    # GDD needs to be expanded to 5min
    gdd_5min_B = np.repeat(cum_gdd_B, timesteps_per_day)
    daily_gdd_5min_B = np.repeat(daily_tmean_B, timesteps_per_day) # rough proxy or accurate? Actually we can pass daily_gdd
    # We need daily_gdd properly. It is calculated by GDDModel.
    daily_gdd_B_val = gdd_model.calculate_cumulative_gdd(daily_tmean_B) # This is cumulative
    # Wait, daily GDD is just daily_tmean - 10, clipped.
    daily_gdd_B = np.maximum(0, daily_tmean_B - 10.0)
    daily_gdd_5min_B = np.repeat(daily_gdd_B, timesteps_per_day)
    
    env_features_B = {
        'T': true_5min['T_B'].values,
        'RH': true_5min['RH_B'].values,
        'P': true_5min['P_B'].values,
        'Tsoil': true_5min['Tsoil_B'].values,
        # theta_v is handled in soil_water.py
        'Rs': true_5min['Rs_B'].values,
        'solar_zenith_deg': true_5min['solar_zenith_deg'].values,
        'solar_azimuth_deg': true_5min['solar_azimuth_deg'].values,
        'solar_elevation_deg': true_5min['solar_elevation_deg'].values,
        'shade_fraction': true_5min['shade_fraction'].values,
        'full_shade_flag': (true_5min['shade_fraction'] > 0.99).astype(float).values,
        'VPD': true_5min['VPD_B'].values,
        # Missing flags are 0
        'daily_GDD': daily_gdd_5min_B,
        'cumulative_GDD': gdd_5min_B
    }
    
    # Sensor noise realization
    sensor_emulator = SensorEmulator(config, rs.get_generator(3))
    # We'll just extract the noise by emulating zero arrays and taking the difference
    dummy_df = true_5min.copy()
    dummy_df['theta_v_A'] = 0.0
    dummy_df['theta_v_B'] = 0.0
    dummy_obs = sensor_emulator.emulate_sensors(dummy_df)
    sensor_noise_A = dummy_obs['theta_v_A'].values
    sensor_noise_B = dummy_obs['theta_v_B'].values
    
    import joblib
    print("Loading Frozen BiLSTM Model...")
    # Load model
    checkpoint = torch.load('outputs/models/bilstm_model.pt', map_location='cpu', weights_only=True)
    # Extract dimensions
    input_size = 24 # updated for exact causal features
    bilstm = BiLSTMModel(input_dim=input_size, device='cpu')
    bilstm.model.load_state_dict(checkpoint['model_state_dict'])
    bilstm.model.eval()
    scaler = joblib.load('outputs/models/scaler.pkl')
    
    policies = {
        'A_FIX': ('A', FixedCalendarPolicy(config)),
        'A_IOT': ('A', ThresholdIoTPolicy(config)),
        'B_FIX': ('B', FixedCalendarPolicy(config)),
        'B_IOT': ('B', ThresholdIoTPolicy(config)),
        'B_AI': ('B', ProposedAIPolicy(config, bilstm, scaler))
    }
    
    soil_model = SoilWaterBalance(config)
    results = {}
    
    for name, (zone, policy) in policies.items():
        print(f"Simulating {name}...")
        p_surface = p_surface_A if zone == 'A' else p_surface_B
        et_demand = true_5min[f'ET_demand_5min_{zone}'].values
        kc = kc_A_5min if zone == 'A' else kc_B_5min
        sensor_noise = sensor_noise_A if zone == 'A' else sensor_noise_B
        env_feat = env_features_B if zone == 'B' else None
        
        soil_df = soil_model.simulate_zone(
            p_surface=p_surface,
            et_demand=et_demand,
            kc=kc,
            policy=policy,
            sensor_noise=sensor_noise,
            env_features=env_feat,
            initial_theta=0.27
        )
        
        # Crop Yield
        daily_rs = true_5min[f'Rs_{zone}'].values.reshape(days, timesteps_per_day).sum(axis=1) * (timestep * 60) / 1e6
        daily_ks = soil_df['Ks'].values.reshape(days, timesteps_per_day).mean(axis=1)
        phen_model = PhenologyModel(config)
        cum_gdd = cum_gdd_A if zone == 'A' else cum_gdd_B
        stage = phen_model.determine_stage(cum_gdd)
        
        daily_df = pd.DataFrame({
            'cumulative_gdd': cum_gdd,
            'phenology_stage': stage,
            'Rs': daily_rs,
            'Ks': daily_ks
        })
        
        crop_model = CropGrowthModel(config)
        growth = crop_model.calculate_daily_growth(daily_df)
        yield_model = YieldModel(config)
        yield_df = yield_model.calculate_yield(pd.concat([daily_df, growth], axis=1))
        
        results[name] = {
            'soil_df': soil_df,
            'yield': yield_df['yield_g'],
            'p_surface': p_surface
        }
        
    print("\n--- RUN 3A Results ---")
    metrics = []
    for name, res in results.items():
        soil = res['soil_df']
        ir_total = np.sum(soil['Irrigation_mm'])
        yield_val = res['yield']
        wue = yield_val / ir_total if ir_total > 0 else 0
        residual = calculate_water_balance_residual(soil, res['p_surface'])
        
        ir_events = np.sum(soil['Irrigation_mm'] > 0)
        
        metrics.append({
            'Policy': name,
            'IR_mm': ir_total,
            'IR_Events': ir_events,
            'Yield_g': yield_val,
            'WUE': wue,
            'Residual': residual
        })
        
    df_metrics = pd.DataFrame(metrics)
    print(df_metrics.to_string(index=False))
    df_metrics.to_csv(os.path.join(output_dir, 'run3a_metrics.csv'), index=False)
    
if __name__ == "__main__":
    run_irrigation_smoke()
