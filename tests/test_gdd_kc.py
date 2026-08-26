import pytest
import numpy as np
from agronomy.gdd import GDDModel
from agronomy.phenology import PhenologyModel, PhenologyStage
from agronomy.kc import KcModel

@pytest.fixture
def config():
    return {
        'crop': {
            'phenology': {
                'base_temperature_c': 10.0,
                'max_temperature_c': 35.0,
                'gdd_thresholds': {
                    'emergence': 50.0,
                    'vegetative': 550.0,
                    'flowering': 800.0,
                    'pod_filling': 1100.0,
                    'maturity': 1350.0
                }
            },
            'crop_coefficients': {
                'kc_ini': 0.40,
                'kc_mid': 1.15,
                'kc_end': 0.35
            }
        }
    }

def test_gdd(config):
    gdd_model = GDDModel(config)
    
    # Test cases: [20, 40, 5] -> GDD should be [10, 25, 0]
    t_mean_daily = np.array([20.0, 40.0, 5.0])
    
    gdd = gdd_model.calculate_daily_gdd(t_mean_daily)
    np.testing.assert_allclose(gdd, [10.0, 25.0, 0.0])
    
    cum_gdd = gdd_model.calculate_cumulative_gdd(t_mean_daily)
    np.testing.assert_allclose(cum_gdd, [10.0, 35.0, 35.0])

def test_phenology(config):
    phen_model = PhenologyModel(config)
    
    cum_gdd = np.array([0.0, 100.0, 600.0, 900.0, 1200.0, 1400.0])
    stages = phen_model.determine_stage(cum_gdd)
    
    expected_stages = [
        PhenologyStage.PRE_EMERGENCE, # 0
        PhenologyStage.VEGETATIVE,    # 100
        PhenologyStage.VEGETATIVE,    # 600 (thresholds: 50=veg, 800=flowering) wait.
        # Let's check thresholds: 
        # >50: veg (1)
        # >800: flowering (2)
        # >1100: pod_filling (3)
        # >1350: maturity (4)
        # Ah, 600 is Vegetative according to logic:
        # stages[>=50]=1, stages[>=800]=2 -> wait, the user's thresholds say vegetative=550.0, flowering=800.
        # But emergence=50.0. After emergence, it's vegetative.
        # Wait, the code sets: >= emergence -> vegetative. >= flowering -> flowering. 
        # So 600 -> Vegetative. Correct.
    ]
    assert stages[0] == PhenologyStage.PRE_EMERGENCE
    assert stages[1] == PhenologyStage.VEGETATIVE
    assert stages[2] == PhenologyStage.VEGETATIVE
    assert stages[3] == PhenologyStage.FLOWERING
    assert stages[4] == PhenologyStage.POD_FILLING
    assert stages[5] == PhenologyStage.MATURITY

def test_kc(config):
    kc_model = KcModel(config)
    
    # GDD points
    # Initial phase: < 550
    # Dev phase: 550 - 800
    # Mid phase: 800 - 1100
    # Late phase: 1100 - 1350
    # Post maturity: > 1350
    cum_gdd = np.array([0, 200, 550, 675, 800, 900, 1100, 1225, 1350, 1500])
    kc = kc_model.calculate_kc(cum_gdd)
    
    assert kc[0] == 0.40
    assert kc[1] == 0.40
    assert kc[2] == 0.40 # exact start of dev phase
    # Midpoint of dev phase (675)
    assert np.isclose(kc[3], 0.40 + (1.15 - 0.40) * 0.5)
    assert kc[4] == 1.15
    assert kc[5] == 1.15
    assert kc[6] == 1.15
    # Midpoint of late phase (1225)
    assert np.isclose(kc[7], 1.15 + (0.35 - 1.15) * 0.5)
    assert kc[8] == 0.35
    assert kc[9] == 0.35
