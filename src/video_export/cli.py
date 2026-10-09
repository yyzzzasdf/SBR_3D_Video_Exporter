"""Portable command line, validation and reproducibility records."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from .config import DEFAULTS, load_config
from .data import load_dataset

ROOT = Path(__file__).resolve().parents[2]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Export x/y/z sweep videos from a 3D power cube.")
    p.add_argument("--data", type=Path, help="Input directory with power_cube.npz and metadata.json")
    p.add_argument("--cube", type=Path, help="Explicit power cube; overrides --data's cube")
    p.add_argument("--scene", type=Path, help="Optional numeric scene.npz")
    p.add_argument("--inside", type=Path, help="Optional inside_mask.npz")
    p.add_argument("--metadata", type=Path, help="Metadata JSON; required alongside the cube")
    p.add_argument("--config", type=Path, default=ROOT / "configs" / "default.json")
    p.add_argument("--out", type=Path, default=ROOT / "outputs" / "synthetic")
    p.add_argument("--axes", nargs="+", choices=list("xyz"))
    p.add_argument("--quantities", nargs="+", choices=["coherent", "incoherent"])
    for key in ("fps_x", "fps_y", "fps_z", "width", "height"):
        p.add_argument("--" + key.replace("_", "-"), type=int)
    for key in ("frames_x", "frames_y", "frames_z"):
        p.add_argument("--" + key.replace("_", "-"), type=int, help="Number of sampled slices; capped at axis length")
    for key in ("elevation", "azimuth", "z_scale", "zoom", "dyn_range", "vmin", "vmax", "building_opacity", "slice_opacity", "tx_radius", "ground_z"):
        p.add_argument("--" + key.replace("_", "-"), type=float)
    p.add_argument("--cmap")
    p.add_argument("--display", choices=["native", "path_gain"])
    p.add_argument("--preview", action=argparse.BooleanOptionalAction, default=None)
    p.add_argument("--preview-only", action="store_true")
    p.add_argument("--validate-only", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="Allow replacing existing generated files")
    return p.parse_args(argv)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execute(args):
    config = load_config(args.config, {key: getattr(args, key) for key in DEFAULTS})
    folder = args.data or (args.cube.parent if args.cube else ROOT / "examples" / "synthetic")
    cube = args.cube or folder / "power_cube.npz"
    metadata = args.metadata or folder / "metadata.json"
    scene = args.scene or (folder / "scene.npz" if (folder / "scene.npz").exists() else None)
    inside = args.inside or (folder / "inside_mask.npz" if (folder / "inside_mask.npz").exists() else None)
    dataset = load_dataset(cube, metadata, scene, inside, config["quantities"])
    from .renderer import display_info, render_outputs
    display_info(dataset.metadata, config)
    print(f"[input] shape={tuple(len(a) for a in dataset.axes)}; quantities={list(dataset.powers)}; unit={dataset.metadata['value_kind']}")
    if args.validate_only:
        print("[input] validation passed")
        return 0
    output = args.out.resolve()
    protected = set(dataset.inputs)
    protected = {path.resolve() for path in protected}
    if output / "run.json" in protected:
        raise ValueError("Output would replace an input")
    if output.exists() and not args.overwrite:
        existing = list(output.glob("sweep3d_*.mp4")) + list(output.glob("preview3d_*.png"))
        if existing or (output / "run.json").exists():
            raise ValueError("Output already contains a run; choose a new --out or use --overwrite")
    output.mkdir(parents=True, exist_ok=True)
    record = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
              "command": sys.argv, "config": config, "metadata": dataset.metadata,
              "inputs": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in dataset.inputs],
              "versions": {name: importlib.metadata.version(name) for name in ("numpy", "pyvista", "vtk", "imageio", "imageio-ffmpeg")},
              "python": sys.version, "outputs": []}
    report = output / "run.json"
    report.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        record["outputs"] = render_outputs(dataset, config, output, args.preview_only)
        for item in record["outputs"]:
            item["bytes"] = (output / item["file"]).stat().st_size
        record["status"] = "complete"
    except Exception as error:
        record["status"] = "failed"
        record["error"] = str(error)
        raise
    finally:
        record["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
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
