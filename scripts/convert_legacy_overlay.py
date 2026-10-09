"""Convert a trusted My_SBR scene_overlay.npz to numeric scene.npz."""
import argparse
from pathlib import Path
import sys
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from video_export.samples import write_scene

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve() or args.output.exists():
        parser.error("Choose a new output file; the converter does not overwrite files")
    with np.load(args.input, allow_pickle=True) as archive:
        polygons = list(archive["building_polys"])
        tx = archive["Tx"] if "Tx" in archive else None
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_scene(args.output, polygons, tx)
    print(args.output)
