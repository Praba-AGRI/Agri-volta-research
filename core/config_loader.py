import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any

class ImmutableConfig:
    def __init__(self, data: Dict[str, Any]):
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, ImmutableConfig(value))
            else:
                setattr(self, key, value)

    def __setattr__(self, key, value):
        if hasattr(self, key):
            raise AttributeError(f"Configuration is immutable. Cannot modify {key}")
        super().__setattr__(key, value)

    def to_dict(self) -> Dict[str, Any]:
        result = {}
        for key, value in self.__dict__.items():
            if isinstance(value, ImmutableConfig):
                result[key] = value.to_dict()
            else:
                result[key] = value
        return result

def load_yaml(file_path: Path) -> Dict[str, Any]:
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    with open(file_path, 'r') as f:
        return yaml.safe_load(f) or {}

def load_all_configs(config_dir: Path) -> ImmutableConfig:
    config_data = {}
    
    files = [
        "experiment.yaml",
        "pv_geometry.yaml",
        "weather.yaml",
        "soil.yaml",
        "crop.yaml",
        "sensors.yaml",
        "models.yaml",
        "irrigation.yaml"
    ]
    
    for filename in files:
        file_path = config_dir / filename
        data = load_yaml(file_path)
        # Deep merge could be implemented here if top level keys clash, 
        # but based on our structure, the top level keys are mostly distinct.
        # However, to be safe we iterate and add them.
        for key, value in data.items():
            if key in config_data and isinstance(config_data[key], dict) and isinstance(value, dict):
                config_data[key].update(value)
            else:
                config_data[key] = value
                
    return ImmutableConfig(config_data)

if __name__ == "__main__":
    # Test loader
    config_path = Path(__file__).parent.parent / "config"
    try:
        config = load_all_configs(config_path)
        print("Configuration successfully loaded and frozen.")
        print(f"Project Name: {config.project.name}")
    except Exception as e:
        print(f"Error loading configuration: {e}")
