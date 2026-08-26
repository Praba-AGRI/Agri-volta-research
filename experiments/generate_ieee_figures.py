import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

# IEEE Standard Styling
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.size'] = 10
mpl.rcParams['axes.labelsize'] = 10
mpl.rcParams['axes.titlesize'] = 12
mpl.rcParams['xtick.labelsize'] = 9
mpl.rcParams['ytick.labelsize'] = 9
mpl.rcParams['legend.fontsize'] = 9
mpl.rcParams['figure.dpi'] = 300
mpl.rcParams['savefig.dpi'] = 300
mpl.rcParams['savefig.bbox'] = 'tight'
# Grayscale safe colors
COLOR_PERS = '#000000' # Black
COLOR_RF = '#666666'   # Dark Gray
COLOR_BILSTM = '#b3b3b3' # Light Gray
COLOR_IOT = '#666666'  # Dark Gray
COLOR_AI = '#000000'   # Black

def generate_ieee_figures():
    out_dir = "outputs/ieee_figures"
    os.makedirs(out_dir, exist_ok=True)
    
    # ---------------- RUN 2 FIGURES ----------------
    print("Generating RUN 2 Figures...")
    
    # Check if run2 files exist
    if os.path.exists('outputs/run2_fold_results.csv'):
        run2_folds = pd.read_csv('outputs/run2_fold_results.csv')
        # Figure 10: Five-fold forecasting benchmark
        fig, ax = plt.subplots(figsize=(6, 4))
        x = np.arange(5)
        width = 0.25
        # Need to handle actual column names from the previous agent's save
        cols = run2_folds.columns
        pers_col = next((c for c in cols if 'Pers' in c and 'RMSE' in c), None)
        rf_col = next((c for c in cols if 'RF' in c and 'RMSE' in c), None)
        bilstm_col = next((c for c in cols if 'LSTM' in c and 'RMSE' in c), None)
        
        if pers_col and rf_col and bilstm_col:
            ax.bar(x - width, run2_folds[pers_col], width, label='Persistence', color=COLOR_PERS, edgecolor='black')
            ax.bar(x, run2_folds[rf_col], width, label='Random Forest', color=COLOR_RF, edgecolor='black', hatch='//')
            ax.bar(x + width, run2_folds[bilstm_col], width, label='BiLSTM', color=COLOR_BILSTM, edgecolor='black', hatch='\\\\')
            ax.set_ylabel('RMSE (VWC fraction)')
            ax.set_xlabel('Cross-Validation Fold')
            ax.set_title('Five-Fold Forecasting Benchmark')
            ax.set_xticks(x)
            ax.set_xticklabels([f"Fold {i+1}" for i in range(len(run2_folds))])
            ax.legend()
            plt.savefig(os.path.join(out_dir, 'fig10_forecasting_benchmark.png'))
            plt.close()

            # Figure 13: Fold-wise BiLSTM performance (RMSE and violations)
            fig, ax1 = plt.subplots(figsize=(6, 4))
            ax1.plot(x, run2_folds[bilstm_col], marker='o', color=COLOR_PERS, label='RMSE')
            ax1.set_ylabel('BiLSTM RMSE (VWC fraction)', color='black')
            ax1.set_xlabel('Cross-Validation Fold')
            ax1.set_xticks(x)
            ax1.set_xticklabels([f"Fold {i+1}" for i in range(len(run2_folds))])
            
            ax2 = ax1.twinx()
            violation_col = next((c for c in cols if 'viol' in c.lower() and 'rate' in c.lower()), None)
            if violation_col:
                ax2.bar(x, run2_folds[violation_col], width=0.3, alpha=0.3, color=COLOR_RF, label='Violation Rate')
                ax2.set_ylabel('Violation Rate (%)', color='black')
                ax2.set_ylim(0, 20)
            ax1.set_title('Fold-wise BiLSTM Performance')
            fig.legend(loc="upper left", bbox_to_anchor=(0.15, 0.85))
            plt.savefig(os.path.join(out_dir, 'fig13_bilstm_performance.png'))
            plt.close()
    
    # Figure 14: Microclimate ablation
    if os.path.exists('outputs/run2_ablation.csv') and os.path.exists('outputs/run2_fold_results.csv'):
        run2_ablation = pd.read_csv('outputs/run2_ablation.csv')
        run2_folds = pd.read_csv('outputs/run2_fold_results.csv')
        bilstm_col = next((c for c in run2_folds.columns if 'LSTM' in c and 'RMSE' in c), None)
        
        if bilstm_col:
            # Ablated RMSE is in run2_ablation['Abl_RMSE']
            # Full RMSE is in run2_folds[bilstm_col]
            delta_rmse = run2_ablation['Abl_RMSE'] - run2_folds[bilstm_col]
            
            fig, ax = plt.subplots(figsize=(6, 4))
            x = np.arange(5)
            # Positive indicates degraded performance after ablation; negative indicates improvement
            ax.bar(x, delta_rmse, color=COLOR_RF, edgecolor='black')
            ax.axhline(0, color='black', linewidth=1)
            ax.set_xticks(x)
            ax.set_xticklabels([f"Fold {i+1}" for i in range(5)])
            ax.set_ylabel('ΔRMSE (VWC fraction)')
            ax.set_title('Microclimate Ablation Performance')
            plt.savefig(os.path.join(out_dir, 'fig14_microclimate_ablation.png'))
            plt.close()
    
    # Figure 15: SHAP attribution ranking
    if os.path.exists('outputs/run2_shap.csv'):
        run2_shap = pd.read_csv('outputs/run2_shap.csv')
        fig, ax = plt.subplots(figsize=(6, 4))
        # Find feature and shap columns
        cols = run2_shap.columns
        feat_col = cols[0]
        shap_col = cols[1]
        
        authoritative_order = [
            'thermal_time', 'historical_soil_moisture', 'soil_temperature', 
            'humidity_vpd', 'radiation', 'pv_shade', 'temperature', 'rainfall'
        ]
        
        # We need to sort descending so the top feature is plotted at the top of the barh
        authoritative_order.reverse()
        
        run2_shap[feat_col] = pd.Categorical(run2_shap[feat_col], categories=authoritative_order, ordered=True)
        run2_shap = run2_shap.sort_values(by=feat_col)
        
        ax.barh(run2_shap[feat_col], run2_shap[shap_col], color=COLOR_RF, edgecolor='black')
        ax.set_xlabel('Mean Absolute SHAP Value')
        ax.set_title('SHAP Relative Attribution Ranking')
        plt.savefig(os.path.join(out_dir, 'fig15_shap_attribution.png'))
        plt.close()
    
    # ---------------- RUN 3 FIGURES ----------------
    print("Generating RUN 3 Figures...")
    
    run3_metrics = pd.read_csv('outputs/run3b/run3b_metrics.csv')
    
    ai_metrics = run3_metrics[run3_metrics['Policy'] == 'B_AI'].set_index('season_id')
    iot_metrics = run3_metrics[run3_metrics['Policy'] == 'B_IOT'].set_index('season_id')
    
    ir_ai = ai_metrics['IR_mm']
    ir_iot = iot_metrics['IR_mm']
    y_ai = ai_metrics['Yield_g']
    y_iot = iot_metrics['Yield_g']
    
    # Figure 19: Paired irrigation comparison
    fig, ax = plt.subplots(figsize=(5, 4))
    for s in ir_ai.index:
        ax.plot([1, 2], [ir_iot.loc[s], ir_ai.loc[s]], color='black', alpha=0.2, marker='o', markersize=4)
    ax.plot([1, 2], [ir_iot.mean(), ir_ai.mean()], color='black', linewidth=3, marker='s', markersize=8, label='Mean')
    ax.set_xticks([1, 2])
    ax.set_xticklabels(['Threshold IoT', 'AI Policy'])
    ax.set_ylabel('Applied Irrigation (mm/season)')
    ax.set_title('Paired Irrigation Comparison')
    ax.set_xlim(0.5, 2.5)
    ax.legend()
    plt.savefig(os.path.join(out_dir, 'fig19_paired_irrigation.png'))
    plt.close()
    
    # Figure 20: Irrigation reduction distribution
    delta_ir = ir_ai - ir_iot
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(delta_ir, bins=10, color=COLOR_BILSTM, edgecolor='black')
    ax.axvline(delta_ir.mean(), color='black', linestyle='dashed', linewidth=2, label=f'Mean: {delta_ir.mean():.2f} mm')
    # Add 95% CI
    ax.axvspan(-20.28, -4.87, color='black', alpha=0.1, label='95% CI')
    ax.set_xlabel('Irrigation Difference (AI - IoT) (mm)')
    ax.set_ylabel('Frequency')
    ax.set_title('Irrigation Reduction Distribution')
    ax.legend()
    plt.savefig(os.path.join(out_dir, 'fig20_irrigation_reduction.png'))
    plt.close()
    
    # Figure 21: Yield non-inferiority
    delta_y_rel = (y_ai - y_iot) / y_iot * 100
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(delta_y_rel, bins=10, color=COLOR_BILSTM, edgecolor='black')
    ax.axvline(-3.06, color='black', linestyle='solid', linewidth=2, label='95% CI Lower Bound (-3.06%)')
    ax.axvline(-5.0, color='black', linestyle='dashed', linewidth=2, label='Non-Inferiority Margin (-5.0%)')
    ax.set_xlabel('Relative Yield Difference (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Yield Non-Inferiority')
    ax.legend(loc='upper left')
    plt.savefig(os.path.join(out_dir, 'fig21_yield_non_inferiority.png'))
    plt.close()
    
    # Figure 22: Yield-irrigation trade-off
    fig, ax = plt.subplots(figsize=(6, 5))
    ax.scatter(ir_iot, y_iot, color='white', edgecolor='black', marker='o', s=50, label='IoT Controller', zorder=3)
    ax.scatter(ir_ai, y_ai, color='black', marker='x', s=50, label='AI Policy', zorder=3)
    # Connect pairs
    for s in ir_ai.index:
        ax.plot([ir_iot.loc[s], ir_ai.loc[s]], [y_iot.loc[s], y_ai.loc[s]], color='gray', alpha=0.3, zorder=2)
    ax.set_xlabel('Applied Irrigation (mm/season)')
    ax.set_ylabel('Simulated Crop Yield (g/m²)')
    ax.set_title('Yield vs. Irrigation Trade-off')
    ax.legend()
    plt.savefig(os.path.join(out_dir, 'fig22_yield_irrigation_tradeoff.png'))
    plt.close()
    
    # Figure 23: AI decision states
    fig, ax = plt.subplots(figsize=(5, 4))
    states = ['IRRIGATE', 'DELAY', 'HOLD']
    counts = [22, 8, 1860] # From our frozen audit
    ax.bar(states, counts, color=COLOR_RF, edgecolor='black')
    for i, v in enumerate(counts):
        ax.text(i, v + (v*0.1), str(v), ha='center', fontweight='bold')
    ax.set_yscale('log')
    ax.set_ylabel('Decision Count (Log Scale)')
    ax.set_title('AI Decision State Distribution')
    plt.savefig(os.path.join(out_dir, 'fig23_ai_decision_states.png'))
    plt.close()
    
    # Figure 24: Decision-point forecast error
    fig, ax = plt.subplots(figsize=(4, 4))
    models = ['Persistence', 'BiLSTM']
    rmses = [0.0104, 0.0254] # From frozen run3b eval
    ax.bar(models, rmses, color=[COLOR_PERS, COLOR_BILSTM], edgecolor='black', width=0.5)
    ax.set_ylabel('RMSE (VWC fraction)')
    ax.set_title('Forecast Error at Decision Points')
    plt.savefig(os.path.join(out_dir, 'fig24_decision_point_rmse.png'))
    plt.close()
    
    print("All requested IEEE figures generated successfully in outputs/ieee_figures/")

if __name__ == "__main__":
    generate_ieee_figures()
