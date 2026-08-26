import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np
import pandas as pd

def audit_yield_distribution():
    df_mc = pd.read_csv('outputs/RUN_3B/mc_policy_comparison_30seasons.csv')
    
    p_ai = df_mc[df_mc['policy'] == 'B-AI-EN'].sort_values('season')['yield_kg_ha'].values
    p_iot = df_mc[df_mc['policy'] == 'B-IOT'].sort_values('season')['yield_kg_ha'].values
    
    paired_rel_yield = 100.0 * (p_ai - p_iot) / (p_iot + 1e-5)
    
    mean_dy = np.mean(paired_rel_yield)
    med_dy = np.median(paired_rel_yield)
    p5_dy = np.percentile(paired_rel_yield, 5)
    p95_dy = np.percentile(paired_rel_yield, 95)
    min_dy = np.min(paired_rel_yield)
    max_dy = np.max(paired_rel_yield)
    
    print("=== PAIRED YIELD DIFFERENCE DISTRIBUTION (N=30 Seasons) ===")
    print(f"Mean Delta Y:   +{mean_dy:.4f}%")
    print(f"Median Delta Y: +{med_dy:.4f}%")
    print(f"5th Percentile: +{p5_dy:.4f}%")
    print(f"95th Percentile: +{p95_dy:.4f}%")
    print(f"Min Delta Y:    +{min_dy:.4f}%")
    print(f"Max Delta Y:    +{max_dy:.4f}%")
    
    # Save distribution summary
    with open('outputs/RUN_3B/yield_distribution_summary.txt', 'w') as f:
        f.write(f"Mean Delta Y: +{mean_dy:.4f}%\n")
        f.write(f"Median Delta Y: +{med_dy:.4f}%\n")
        f.write(f"5th Percentile: +{p5_dy:.4f}%\n")
        f.write(f"95th Percentile: +{p95_dy:.4f}%\n")

if __name__ == '__main__':
    audit_yield_distribution()
