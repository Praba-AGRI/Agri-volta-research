"""
Physical and structural constants for the Agrivoltaic Simulation.
"""

# Physics
STEFAN_BOLTZMANN = 4.903e-9  # MJ K^-4 m^-2 day^-1
PSYCHROMETRIC_CONSTANT = 0.066  # kPa / degC at sea level (approximate, ET0 will calculate exactly if elevation given, else use nominal)
LATENT_HEAT_VAPORIZATION = 2.45  # MJ / kg
SPECIFIC_HEAT_AIR = 1.013e-3  # MJ kg^-1 degC^-1

# Time
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
MINUTES_PER_DAY = 1440
SECONDS_PER_DAY = 86400

# Defaults
DEFAULT_TIMESTEP_MINUTES = 5
TIMESTEPS_PER_DAY = MINUTES_PER_DAY // DEFAULT_TIMESTEP_MINUTES
