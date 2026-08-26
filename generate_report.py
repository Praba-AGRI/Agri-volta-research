import pandas as pd
import shutil
import os

output_prefix = "run2"

df_folds = pd.read_csv(f'outputs/{output_prefix}_fold_results.csv')
df_abl = pd.read_csv(f'outputs/{output_prefix}_ablation.csv')
df_summary = pd.read_csv(f'outputs/{output_prefix}_summary.csv')
df_shap = pd.read_csv(f'outputs/{output_prefix}_shap.csv')

raw_A = 20160
raw_B = 20160
final_A = 19584  # Based on expected drops, I will just recompute or skip this
final_B = 19584

report_content = "# RUN 2 Statistical Report\n\n"

report_content += "### Model Performance (5-Fold CV)\n"
report_content += df_summary.to_markdown() + "\n\n"

report_content += "### Bounds Violations\n"
v_rate_mean = df_folds['Violation_Rate'].mean()
report_content += f"Mean Physical Violation Rate: {v_rate_mean:.2f}%\n\n"

report_content += "### SHAP Feature Group Importance\n"
report_content += df_shap.to_markdown() + "\n\n"

report_content += "### Full Fold Results\n"
report_content += df_folds.to_markdown() + "\n\n"

report_content += "### Ablation Results\n"
report_content += df_abl.to_markdown() + "\n"

with open(f'outputs/{output_prefix}_report.md', 'w') as f:
    f.write(report_content)
    
shutil.copy(f'outputs/{output_prefix}_report.md', f'C:/Users/Prabakaran/.gemini/antigravity/brain/e6615bad-2ef1-47eb-a938-c0e4bda28a31/{output_prefix}_report.md')

print("Report generated successfully.")
