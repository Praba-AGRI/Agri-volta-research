# RUN 2B - Enhanced BiLSTM Development Report

### Summary statistics (5-Fold CV)
| Metric             |        Mean |         SD |
|:-------------------|------------:|-----------:|
| Pers_RMSE          |  0.00973802 | 0.00387997 |
| RF_RMSE            |  0.014594   | 0.00648971 |
| Orig_RMSE          |  0.0170823  | 0.00667673 |
| Enh_RMSE           |  0.0102254  | 0.00400643 |
| Transfer_RMSE      |  0.0101932  | 0.00422623 |
| Shuffled_RMSE      |  0.010172   | 0.00394488 |
| Enh_Skill          | -0.058588   | 0.194372   |
| Direction_Accuracy |  0.336544   | 0.108468   |

### Gate Distribution Analysis
- **overall_mean**: 0.0060
- **overall_std**: 0.0209
- **p5**: 0.0000
- **p95**: 0.0536
- **rain_mean**: 0.0044
- **dry_mean**: 0.0098
- **boundary_mean**: 0.0493

### Event-Level Performance (Threshold < 0.2025)
- Mean Critical Recall: 1.0000
- Mean Critical Precision: 1.0000
- Mean Critical F1: 1.0000

