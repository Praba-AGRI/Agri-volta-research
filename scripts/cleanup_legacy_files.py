import os
import shutil
from pathlib import Path

def cleanup_legacy_files():
    base_dir = Path("C:/Users/Prabakaran/Desktop/Agrivoltaics simulation")
    outputs_dir = base_dir / "outputs"

    # Remove temporary partial files in outputs
    to_delete_files = [
        outputs_dir / "run2_ablation_partial.csv",
        outputs_dir / "run2_fold_results_partial.csv",
        base_dir / "diagnose_fold3.py",
        base_dir / "diagnostic.py",
        base_dir / "persistence_diagnostic.py",
        base_dir / "out.txt",
        base_dir / "run1_final_audit.csv"
    ]

    to_delete_dirs = [
        outputs_dir / "run3",
        outputs_dir / "run3b"
    ]

    for f in to_delete_files:
        if f.exists():
            f.unlink()

    for d in to_delete_dirs:
        if d.exists():
            shutil.rmtree(d)

    print("Cleanup complete. All legacy and temporary files removed.")

if __name__ == '__main__':
    cleanup_legacy_files()
