"""Display settings and validation."""
import json
import math
from pathlib import Path


DEFAULTS = {
    "input_dir": "data", "output_dir": "output",
    "axes": ["x", "y", "z"],
    "fps_x": 10, "fps_y": 10, "fps_z": 3,
    "frames_x": None, "frames_y": None, "frames_z": None,
    "width": 1280, "height": 960,
    "elevation": 28.0, "azimuth": -60.0, "z_scale": 1.0, "zoom": 1.0,
    "dyn_range": 70.0, "vmin": None, "vmax": None,
    "scene_opacity": 0.35, "slice_opacity": 0.65,
    "marker_radius": 4.5, "ground_z": 0.0,
    "cmap": "turbo", "scalar_label": "Value", "coordinate_unit": "m",
    "coverage_z": None,
}


def load_config(path=None, overrides=None):
    config = dict(DEFAULTS)
    if path is not None:
        supplied = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        if not isinstance(supplied, dict):
            raise ValueError("config: expected a JSON object")
        unknown = set(supplied) - set(DEFAULTS)
        if unknown:
            raise ValueError(f"config: unknown options {sorted(unknown)}")
        config.update(supplied)
    config.update({key: value for key, value in (overrides or {}).items() if value is not None})
    axes = config["axes"]
    if (not isinstance(axes, list) or not axes or any(not isinstance(v, str) or v not in ("x", "y", "z") for v in axes)
            or len(set(axes)) != len(axes)):
        raise ValueError("axes: expected distinct choices from x, y, z")
    for key in ("width", "height", "fps_x", "fps_y", "fps_z"):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f"{key}: must be a positive integer")
    if config["width"] < 320 or config["height"] < 240 or config["width"] % 16 or config["height"] % 16:
        raise ValueError("width/height: minimum 320x240 and multiples of 16")
    for key in ("frames_x", "frames_y", "frames_z"):
        if config[key] is not None and (type(config[key]) is not int or config[key] < 1):
            raise ValueError(f"{key}: must be a positive integer or null for all slices")
    for key in ("elevation", "azimuth", "z_scale", "zoom", "dyn_range", "scene_opacity",
                "slice_opacity", "marker_radius", "ground_z", "vmin", "vmax", "coverage_z"):
        if config[key] is None and key in ("vmin", "vmax", "coverage_z"):
            continue
        if type(config[key]) not in (int, float) or not math.isfinite(config[key]):
            raise ValueError(f"{key}: must be a finite number")
    for key in ("z_scale", "zoom", "dyn_range", "marker_radius"):
        if config[key] <= 0:
            raise ValueError(f"{key}: must be greater than zero")
    for key in ("scene_opacity", "slice_opacity"):
        if not 0 <= config[key] <= 1:
            raise ValueError(f"{key}: must be in [0, 1]")
    for key in ("input_dir", "output_dir", "cmap", "scalar_label", "coordinate_unit"):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f"{key}: expected a nonempty string")
    if config["vmin"] is not None and config["vmax"] is not None and config["vmin"] >= config["vmax"]:
        raise ValueError("vmin must be smaller than vmax")
    return config
