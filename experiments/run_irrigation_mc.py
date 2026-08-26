import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
import torch
import joblib
import multiprocessing as mp
from functools import partial

from core.config_loader import load_all_configs
from core.random_state import SimulationRandomState
from simulation.solar_engine import SolarEngine
from simulation.weather_engine import WeatherEngine
from simulation.rainfall_model import RainfallModel
from simulation.rainfall_partition import RainfallPartition
from simulation.pv_shading import PVShading
from simulation.spectral_engine import SpectralEngine
from simulation.microclimate import Microclimate
from agronomy.et_demand import ETDemandModel
from agronomy.gdd import GDDModel
from agronomy.phenology import PhenologyModel
from agronomy.kc import KcModel
from agronomy.soil_water import SoilWaterBalance
from agronomy.crop_growth import CropGrowthModel
from agronomy.yield_model import YieldModel
from simulation.sensor_emulator import SensorEmulator
from ml.bilstm import BiLSTMModel
from irrigation.policies import FixedCalendarPolicy, ThresholdIoTPolicy, ProposedAIPolicy, PersistenceAIPolicy

def run_season(season_id, config):
    print(f"Starting Season {season_id}...")
    days = 70
    timestep = config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)
    timesteps_per_day = 1440 // timestep
    num_timesteps = days * timesteps_per_day
    
    rs = SimulationRandomState(42)
    rs.set_season(season_id)
    
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
    
    gdd_5min_B = np.repeat(cum_gdd_B, timesteps_per_day)
    daily_gdd_B = np.maximum(0, daily_tmean_B - 10.0)
    daily_gdd_5min_B = np.repeat(daily_gdd_B, timesteps_per_day)
    
    env_features_B = {
        'T': true_5min['T_B'].values,
        'RH': true_5min['RH_B'].values,
        'P': true_5min['P_B'].values,
        'Tsoil': true_5min['Tsoil_B'].values,
        'Rs': true_5min['Rs_B'].values,
        'solar_zenith_deg': true_5min['solar_zenith_deg'].values,
        'solar_azimuth_deg': true_5min['solar_azimuth_deg'].values,
        'solar_elevation_deg': true_5min['solar_elevation_deg'].values,
        'shade_fraction': true_5min['shade_fraction'].values,
        'full_shade_flag': (true_5min['shade_fraction'] > 0.99).astype(float).values,
        'VPD': true_5min['VPD_B'].values,
        'daily_GDD': daily_gdd_5min_B,
        'cumulative_GDD': gdd_5min_B
    }
    
    sensor_emulator = SensorEmulator(config, rs.get_generator(3))
    dummy_df = true_5min.copy()
    dummy_df['theta_v_A'] = 0.0
    dummy_df['theta_v_B'] = 0.0
    dummy_obs = sensor_emulator.emulate_sensors(dummy_df)
    sensor_noise_A = dummy_obs['theta_v_A'].values
    sensor_noise_B = dummy_obs['theta_v_B'].values
    
    checkpoint = torch.load('outputs/models/bilstm_model.pt', map_location='cpu', weights_only=True)
    bilstm = BiLSTMModel(input_dim=24, device='cpu')
    bilstm.model.load_state_dict(checkpoint['model_state_dict'])
    bilstm.model.eval()
    scaler = joblib.load('outputs/models/scaler.pkl')
    
    policies = {
        'A_FIX': ('A', FixedCalendarPolicy(config)),
        'A_IOT': ('A', ThresholdIoTPolicy(config)),
        'B_FIX': ('B', FixedCalendarPolicy(config)),
        'B_IOT': ('B', ThresholdIoTPolicy(config)),
        'B_AI_PERS': ('B', PersistenceAIPolicy(config)),
        'B_AI': ('B', ProposedAIPolicy(config, bilstm, scaler))
    }
    
    soil_model = SoilWaterBalance(config)
    results = {}
    
    for name, (zone, policy) in policies.items():
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
            'yield': yield_df['yield_g'].iloc[-1] if isinstance(yield_df['yield_g'], pd.Series) else yield_df['yield_g'],
            'p_surface': p_surface
        }
        
    metrics = []
    decision_metrics = []
    
    for name, res in results.items():
        soil = res['soil_df']
        ir_total = np.sum(soil['Irrigation_mm'])
        yield_val = res['yield']
        wue = yield_val / ir_total if ir_total > 0 else np.nan
        ir_events = np.sum(soil['Irrigation_mm'] > 0)
        
        metrics.append({
            'season_id': season_id,
            'Policy': name,
            'IR_mm': ir_total,
            'IR_Events': ir_events,
            'Yield_g': yield_val,
            'WUE': wue
        })
        
        if name == 'B_IOT':
            theta = soil['theta_v'].values
            min_theta = np.min(theta)
            n_below_crit = np.sum(theta < 0.2025)
            daily_min = theta.reshape(days, timesteps_per_day).min(axis=1)
            days_below = np.sum(daily_min < 0.2025)
            indices_0600 = np.arange(72, num_timesteps, 288)
            theta_0600 = theta[indices_0600]
            min_theta_0600 = np.min(theta_0600)
            
            decision_metrics.append({
                'season_id': season_id,
                'Policy': name,
                'min_theta': min_theta,
                'n_below_crit': n_below_crit,
                'days_below_crit': days_below,
                'min_theta_0600': min_theta_0600
            })
            
        if name in ['B_AI', 'B_AI_PERS']:
            decisions = soil['decision_type'].dropna()
            n_irrigate = np.sum(decisions == 'IRRIGATE')
            n_delay = np.sum(decisions == 'DELAY')
            n_hold = np.sum(decisions == 'HOLD')
            n_warmup_iot = np.sum(decisions == 'WARMUP_IOT')
            n_warmup_hold = np.sum(decisions == 'WARMUP_HOLD')
            
            forecasts = soil['forecast_theta'].dropna()
            n_fc_below_crit = np.sum(forecasts < 0.2025)
            n_fc_buffer = np.sum((forecasts >= 0.2025) & (forecasts < 0.2200))
            n_fc_high = np.sum(forecasts >= 0.2200)
            
            decision_metrics.append({
                'season_id': season_id,
                'Policy': name,
                'n_irrigate': n_irrigate,
                'n_delay': n_delay,
                'n_hold': n_hold,
                'n_warmup_iot': n_warmup_iot,
                'n_warmup_hold': n_warmup_hold,
                'n_fc_below_crit': n_fc_below_crit,
                'n_fc_buffer': n_fc_buffer,
                'n_fc_high': n_fc_high
            })
            
    timeseries = pd.DataFrame({
        'season_id': season_id,
        'timestamp': true_5min['timestamp'],
        'theta_B_FIX': results['B_FIX']['soil_df']['theta_v'],
        'theta_B_IOT': results['B_IOT']['soil_df']['theta_v'],
        'theta_B_AI': results['B_AI']['soil_df']['theta_v'],
        'IR_B_AI': results['B_AI']['soil_df']['Irrigation_mm'],
        'future_theta_B_AI': results['B_AI']['soil_df']['future_theta_24h'],
        'forecast_theta_B_AI': results['B_AI']['soil_df']['forecast_theta'],
        'error_B_AI': results['B_AI']['soil_df']['forecast_error'],
        'decision_B_AI': results['B_AI']['soil_df']['decision_type'],
        'Ks_B_AI': results['B_AI']['soil_df']['Ks']
    })
    
    return metrics, decision_metrics, timeseries

def run_irrigation_mc(config_dir="config", output_dir="outputs/run3b"):
    print("Starting RUN 3B (Monte Carlo 30 seasons)...")
    config_obj = load_all_configs(Path(config_dir))
    config = config_obj.to_dict()
    os.makedirs(output_dir, exist_ok=True)
    
    seasons = list(range(1, 31))
    
    with mp.Pool(mp.cpu_count()) as pool:
        results = pool.map(partial(run_season, config=config), seasons)
        
    all_metrics = []
    all_decisions = []
    all_ts = []
    
    for m, d, ts in results:
        all_metrics.extend(m)
        all_decisions.extend(d)
        all_ts.append(ts)
        
    df_metrics = pd.DataFrame(all_metrics)
    df_metrics.to_csv(os.path.join(output_dir, 'run3b_metrics.csv'), index=False)
    
    df_decisions = pd.DataFrame(all_decisions)
    df_decisions.to_csv(os.path.join(output_dir, 'run3b_decisions.csv'), index=False)
    
    df_ts = pd.concat(all_ts, ignore_index=True)
    df_ts.to_parquet(os.path.join(output_dir, 'run3b_timeseries.parquet'))
    
    print("RUN 3B completed successfully.")

if __name__ == "__main__":
    run_irrigation_mc()
