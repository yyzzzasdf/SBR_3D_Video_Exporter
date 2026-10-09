"""Regenerate the bundled synthetic dataset with NumPy alone."""
import argparse
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from video_export.samples import generate_synthetic

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "examples" / "synthetic")
    args = parser.parse_args()
    print(generate_synthetic(args.out))
