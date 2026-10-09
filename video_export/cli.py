"""Command line entry and complete-before-replace output handling."""
import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from .config import DEFAULTS, load_config
from .data import load_dataset

ROOT = Path(__file__).resolve().parent.parent


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Export a 3D scalar array as slice videos and a coverage map.")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--data", type=Path, help="Input directory; overrides config input_dir")
    parser.add_argument("--out", type=Path, help="Output directory; overrides config output_dir")
    parser.add_argument("--no-scene", action="store_true", help="Render only the scalar data")
    parser.add_argument("--axes", nargs="+", choices=list("xyz"))
    for key in ("fps_x", "fps_y", "fps_z", "width", "height", "frames_x", "frames_y", "frames_z"):
        parser.add_argument("--" + key.replace("_", "-"), type=int)
    for key in ("elevation", "azimuth", "z_scale", "zoom", "dyn_range", "vmin", "vmax",
                "scene_opacity", "slice_opacity", "marker_radius", "ground_z", "coverage_z"):
        parser.add_argument("--" + key.replace("_", "-"), type=float)
    for key in ("cmap", "scalar_label", "coordinate_unit"):
        parser.add_argument("--" + key.replace("_", "-"))
    parser.add_argument("--validate-only", action="store_true", help="Check input without rendering")
    parser.add_argument("--coverage-only", action="store_true", help="Export only coverage.png")
    return parser.parse_args(argv)


def execute(args):
    overrides = {key: getattr(args, key) for key in DEFAULTS if hasattr(args, key)}
    config = load_config(args.config, overrides)
    # Config paths belong to the config file; explicit CLI paths belong to the working directory.
    base = args.config.resolve().parent
    folder = (args.data or base / config["input_dir"]).resolve()
    output = (args.out or base / config["output_dir"]).resolve()
    cube = folder / "power_cube.npz"
    scene = folder / "scene.npz"
    dataset = load_dataset(cube, scene if scene.exists() and not args.no_scene else None)
    if config["coverage_z"] is not None and not dataset.axes[2][0] <= config["coverage_z"] <= dataset.axes[2][-1]:
        raise ValueError("coverage_z must lie within the data's z range")
    print(f"[input] shape={dataset.values.shape}; scene={bool(dataset.faces.size)}")
    if args.validate_only:
        print("[input] validation passed")
        return 0
    targets = [output / "coverage.png"]
    if not args.coverage_only:
        targets.extend(output / f"sweep_{axis}.mp4" for axis in config["axes"])
    protected = {cube.resolve(), scene.resolve(), args.config.resolve()}
    if any(target.resolve() in protected for target in targets):
        raise ValueError("Output would replace an input or config file")
    from .renderer import render_outputs
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".render-", dir=output) as staging:
        results = render_outputs(dataset, config, Path(staging), args.coverage_only)
        for result in results:
            os.replace(Path(staging) / result, output / result)
    print(f"[output] {output}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    try:
        return execute(args)
    except (ValueError, OSError, KeyError, TypeError, ImportError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
