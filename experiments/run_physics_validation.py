import os
import argparse
import numpy as np
import pandas as pd
from pathlib import Path

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
from simulation.rtc import RTCModel

def run_simulation(mode="smoke", config_dir="config", output_dir="outputs"):
    print(f"Starting physics validation in {mode} mode...")
    
    # Load configuration
    config_obj = load_all_configs(Path(config_dir))
    config = config_obj.to_dict()
    
    print("\n--- Configuration Audit ---")
    soil_props = config.get('soil', {}).get('hydraulic_properties', {})
    print(f"Active Field Capacity: {soil_props.get('theta_field_capacity', {}).get('nominal')}")
    print(f"Active Wilting Point: {soil_props.get('theta_wilting_point', {}).get('nominal')}")
    mc_cfg = config.get('microclimate', {}).get('zone_b', {})
    print(f"Active T_B Daytime Cooling Max: {mc_cfg.get('air_temperature', {}).get('daytime_cooling_c', {}).get('maximum')}")
    print(f"Active RH_B Increase Max: {mc_cfg.get('relative_humidity', {}).get('increase_percent', {}).get('maximum')}")
    rad_cfg = config.get('radiation', {}).get('zone_b', {})
    print(f"Active PV Transmission (Direct): {rad_cfg.get('direct_beam', {}).get('panel_transmission', {}).get('nominal')}")
    print(f"Active PV Transmission (Diffuse): {rad_cfg.get('diffuse', {}).get('transmission', {}).get('nominal')}")
    print("---------------------------\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Set duration
    if mode == "smoke":
        days = 1
    else:
        days = config.get('experiment', {}).get('duration', {}).get('days', 70)
        
    timestep = config.get('experiment', {}).get('temporal_resolution', {}).get('timestep_minutes', 5)
    timesteps_per_day = 1440 // timestep
    num_timesteps = days * timesteps_per_day
    
    # Random State
    seed = config.get('experiment', {}).get('monte_carlo', {}).get('master_seed', 42)
    rs = SimulationRandomState(seed)
    # Use season_id = 1 for validation
    rs.set_season(1)
    
    # 1. Weather and Solar Geometry
    print("Generating Weather and Solar Geometry...")
    solar_engine = SolarEngine(config)
    solar_df = solar_engine.calculate_solar_position(num_timesteps)
    
    weather_engine = WeatherEngine(config, rs.get_generator(0))
    weather_df = weather_engine.generate_weather(num_timesteps, mode=mode)
    
    rain_model = RainfallModel(config, rs.get_generator(1))
    p_incident = rain_model.generate_incident_rainfall(weather_df, mode=mode)
    
    rain_partition = RainfallPartition(config)
    p_surface_A, p_surface_B = rain_partition.partition(p_incident)
    
    weather_df['P_A'] = p_surface_A
    weather_df['P_B'] = p_surface_B # Internal, wait, the microclimate expects P_A to be incident or surface?
    # Actually microclimate doesn't use P_A. Soil water balance uses P_surface.
    
    # 2. PV Shading
    print("Calculating PV Shading...")
    shading_engine = PVShading(config)
    shading_df = shading_engine.calculate_shade_fraction(solar_df)
    
    # 3. Radiation and Spectral
    print("Calculating Radiation...")
    spectral_engine = SpectralEngine(config, rs.get_generator(2))
    rad_df = spectral_engine.calculate_radiation(weather_df, solar_df, shading_df)
    
    # 4. Microclimate
    print("Calculating Microclimate...")
    microclimate = Microclimate(config)
    mc_df = microclimate.calculate_microclimate(weather_df, rad_df, shading_df)
    
    # Combine true physics at 5-min
    true_5min = pd.concat([weather_df, solar_df, shading_df, rad_df, mc_df], axis=1)
    true_5min['season_id'] = 1
    # Adding timestamp
    true_5min['timestamp'] = pd.date_range("2026-06-01 00:00:00", periods=num_timesteps, freq=f"{timestep}min")
    
    # 5. Agronomy
    print("Calculating Agronomic Demand...")
    et_demand_model = ETDemandModel(config)
    et_demand_A = et_demand_model.calculate_zone_demand(true_5min, 'A')
    et_demand_B = et_demand_model.calculate_zone_demand(true_5min, 'B')
    
    true_5min = pd.concat([true_5min, et_demand_A, et_demand_B], axis=1)
    
    # Daily aggregation for GDD, Phenology, Kc
    # We need T_mean_A and T_mean_B daily
    daily_tmean_A = true_5min['T_A'].values.reshape(days, timesteps_per_day).mean(axis=1)
    daily_tmean_B = true_5min['T_B'].values.reshape(days, timesteps_per_day).mean(axis=1)
    
    gdd_model = GDDModel(config)
    cum_gdd_A = gdd_model.calculate_cumulative_gdd(daily_tmean_A)
    cum_gdd_B = gdd_model.calculate_cumulative_gdd(daily_tmean_B)
    
    phen_model = PhenologyModel(config)
    stage_A = phen_model.determine_stage(cum_gdd_A)
    stage_B = phen_model.determine_stage(cum_gdd_B)
    
    kc_model = KcModel(config)
    kc_A_daily = kc_model.calculate_kc(cum_gdd_A)
    kc_B_daily = kc_model.calculate_kc(cum_gdd_B)
    
    # Expand daily Kc to 5-min
    kc_A_5min = np.repeat(kc_A_daily, timesteps_per_day)
    kc_B_5min = np.repeat(kc_B_daily, timesteps_per_day)
    
    # Soil Water Balance
    print("Simulating Soil Water Balance...")
    soil_model = SoilWaterBalance(config)
    soil_df_A = soil_model.simulate_zone(p_surface_A, true_5min['ET_demand_5min_A'].values, kc_A_5min)
    soil_df_B = soil_model.simulate_zone(p_surface_B, true_5min['ET_demand_5min_B'].values, kc_B_5min)
    
    # Rename columns
    soil_df_A = soil_df_A.add_suffix('_A')
    soil_df_B = soil_df_B.add_suffix('_B')
    
    true_5min = pd.concat([true_5min, soil_df_A, soil_df_B], axis=1)
    
    # Crop Growth
    print("Simulating Crop Growth...")
    daily_rs_A = true_5min['Rs_A'].values.reshape(days, timesteps_per_day).sum(axis=1) * (timestep * 60) / 1e6
    daily_rs_B = true_5min['Rs_B'].values.reshape(days, timesteps_per_day).sum(axis=1) * (timestep * 60) / 1e6
    
    daily_ks_A = true_5min['Ks_A'].values.reshape(days, timesteps_per_day).mean(axis=1)
    daily_ks_B = true_5min['Ks_B'].values.reshape(days, timesteps_per_day).mean(axis=1)
    
    daily_A = pd.DataFrame({
        'cumulative_gdd': cum_gdd_A,
        'phenology_stage': stage_A,
        'Rs': daily_rs_A,
        'Ks': daily_ks_A
    })
    
    daily_B = pd.DataFrame({
        'cumulative_gdd': cum_gdd_B,
        'phenology_stage': stage_B,
        'Rs': daily_rs_B,
        'Ks': daily_ks_B
    })
    
    crop_model = CropGrowthModel(config)
    growth_A = crop_model.calculate_daily_growth(daily_A).add_suffix('_A')
    growth_B = crop_model.calculate_daily_growth(daily_B).add_suffix('_B')
    
    daily_agro = pd.concat([daily_A.add_suffix('_A'), daily_B.add_suffix('_B'), growth_A, growth_B], axis=1)
    
    # Yield
    yield_model = YieldModel(config)
    yield_A = yield_model.calculate_yield(pd.concat([daily_A, growth_A.rename(columns=lambda x: x[:-2])], axis=1))
    yield_B = yield_model.calculate_yield(pd.concat([daily_B, growth_B.rename(columns=lambda x: x[:-2])], axis=1))
    
    print(f"Zone A Yield: {yield_A['yield_g']:.2f} g/m2")
    print(f"Zone B Yield: {yield_B['yield_g']:.2f} g/m2")
    
    # 6. Sensors
    print("Emulating Sensors...")
    sensor_emulator = SensorEmulator(config, rs.get_generator(3))
    # We must melt into two zones for the sensor emulator if it uses generic names, 
    # but my sensor emulator uses the prefixed names.
    obs_5min = sensor_emulator.emulate_sensors(true_5min)
    
    rtc_model = RTCModel(config, rs.get_generator(4))
    rtc_df = rtc_model.generate_timestamps(true_5min['timestamp'])
    obs_5min['rtc_timestamp'] = rtc_df['rtc_timestamp']
    
    # Check physics bounds (Validation Phase A assertions)
    assert (true_5min['Rs_A'] >= 0).all()
    assert (true_5min['RH_A'] <= 100.0).all()
    # Timestamps exactly 5 mins apart
    diffs = true_5min['timestamp'].diff().dropna()
    assert (diffs == pd.Timedelta(minutes=5)).all()
    
    # Save outputs
    print("Saving outputs...")
    true_5min.to_parquet(os.path.join(output_dir, "truth_5min.parquet"))
    obs_5min.to_parquet(os.path.join(output_dir, "sensor_5min.parquet"))
    daily_agro.to_parquet(os.path.join(output_dir, "daily_agro.parquet"))
    
    print("Validation run complete!")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["smoke", "stochastic"], default="smoke")
    parser.add_argument("--config_dir", default="config")
    parser.add_argument("--output_dir", default="outputs")
    args = parser.parse_args()
    
    run_simulation(args.mode, args.config_dir, args.output_dir)

if __name__ == "__main__":
    main()
