"""CLI/config settings and validation."""
import json
import math
from pathlib import Path

DEFAULTS = {
    "axes": ["z", "x", "y"], "quantities": ["coherent", "incoherent"],
    "fps_x": 20, "fps_y": 20, "fps_z": 6,
    "frames_x": 240, "frames_y": 300, "frames_z": None,
    "width": 1920, "height": 1440, "elevation": 28.0, "azimuth": -60.0,
    "z_scale": 1.0, "zoom": 1.0, "dyn_range": 70.0,
    "vmin": None, "vmax": None, "building_opacity": 0.35,
    "slice_opacity": 1.0, "tx_radius": 4.5, "ground_z": 0.0,
    "cmap": "turbo", "display": "native", "preview": True,
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
    for key, allowed in [("axes", {"x", "y", "z"}),
                         ("quantities", {"coherent", "incoherent"})]:
        values = config[key]
        if not isinstance(values, list) or not values or any(v not in allowed for v in values) or len(set(values)) != len(values):
            raise ValueError(f"{key}: expected a nonempty list of distinct choices {sorted(allowed)}")
    for key in ("width", "height", "fps_x", "fps_y", "fps_z"):
        value = config[key]
        if type(value) is not int or value < 1:
            raise ValueError(f"{key}: must be a positive integer")
    if config["width"] < 320 or config["height"] < 240 or config["width"] % 16 or config["height"] % 16:
        raise ValueError("width/height: minimum 320x240 and multiples of 16 for exact MP4 dimensions")
    for key in ("frames_x", "frames_y", "frames_z"):
        value = config[key]
        if value is not None and (type(value) is not int or value < 1):
            raise ValueError(f"{key}: must be a positive integer or null for all slices")
    for key in ("elevation", "azimuth", "z_scale", "zoom", "dyn_range", "building_opacity", "slice_opacity", "tx_radius", "ground_z", "vmin", "vmax"):
        value = config[key]
        if value is None and key in ("vmin", "vmax"):
            continue
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"{key}: must be a finite number")
    for key in ("z_scale", "zoom", "dyn_range", "tx_radius"):
        if config[key] <= 0:
            raise ValueError(f"{key}: must be greater than zero")
    for key in ("building_opacity", "slice_opacity"):
        if not 0 <= config[key] <= 1:
            raise ValueError(f"{key}: must be in [0, 1]")
    if config["display"] not in ("native", "path_gain"):
        raise ValueError("display: choose native or path_gain")
    if type(config["preview"]) is not bool:
        raise ValueError("preview: must be true or false")
    if not isinstance(config["cmap"], str) or not config["cmap"]:
        raise ValueError("cmap: expected a colormap name")
    if config["vmin"] is not None and config["vmax"] is not None and config["vmin"] >= config["vmax"]:
        raise ValueError("vmin must be smaller than vmax")
    return config
