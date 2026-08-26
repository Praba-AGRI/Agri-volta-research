import pytest
from pathlib import Path
import numpy as np

from core.config_loader import load_all_configs, ImmutableConfig
from core.constants import MINUTES_PER_DAY, DEFAULT_TIMESTEP_MINUTES, TIMESTEPS_PER_DAY
from core.random_state import SimulationRandomState

def test_constants():
    assert MINUTES_PER_DAY == 1440
    assert TIMESTEPS_PER_DAY == 288
    assert DEFAULT_TIMESTEP_MINUTES == 5

def test_config_loader(tmp_path):
    # Setup temporary config files
    experiment_yaml = """
project:
  name: "Test"
experiment:
  duration:
    days: 70
    """
    (tmp_path / "experiment.yaml").write_text(experiment_yaml)
    
    # Touch other required files with minimal or empty content
    files = [
        "pv_geometry.yaml", "weather.yaml", "soil.yaml", 
        "crop.yaml", "sensors.yaml", "models.yaml", "irrigation.yaml"
    ]
    for f in files:
        (tmp_path / f).write_text("")

    config = load_all_configs(tmp_path)
    
    assert isinstance(config, ImmutableConfig)
    assert config.project.name == "Test"
    assert config.experiment.duration.days == 70

def test_config_immutability(tmp_path):
    # Setup temporary config files
    (tmp_path / "experiment.yaml").write_text("project:\n  name: 'Test'\n")
    for f in ["pv_geometry.yaml", "weather.yaml", "soil.yaml", "crop.yaml", "sensors.yaml", "models.yaml", "irrigation.yaml"]:
        (tmp_path / f).write_text("")

    config = load_all_configs(tmp_path)
    
    with pytest.raises(AttributeError):
        config.project.name = "Modified"

def test_random_state_determinism():
    master_seed = 42
    rs1 = SimulationRandomState(master_seed)
    rs1.set_season(1)
    
    val1 = np.random.rand()
    
    rs2 = SimulationRandomState(master_seed)
    rs2.set_season(1)
    
    val2 = np.random.rand()
    
    assert val1 == val2
    
def test_random_state_independence():
    master_seed = 42
    rs = SimulationRandomState(master_seed)
    rs.set_season(1)
    
    gen1 = rs.get_generator(module_offset=1)
    gen2 = rs.get_generator(module_offset=2)
    
    val1 = gen1.random()
    val2 = gen2.random()
    
    assert val1 != val2
