"""Validated, pickle-free input for the standalone renderer."""
from dataclasses import dataclass
from pathlib import Path
import json
import numpy as np


@dataclass
class Dataset:
    axes: tuple
    powers: dict
    vertices: np.ndarray
    faces: np.ndarray
    tx: object
    inside: object
    metadata: dict
    inputs: list


def numeric(value, name):
    a = np.asarray(value)
    if a.dtype.kind not in "iuf" or not np.isfinite(a).all():
        raise ValueError(f"{name}: expected finite real numeric values")
    return a


def validate_faces(faces, vertex_count):
    if faces.ndim != 1 or faces.dtype.kind not in "iu":
        raise ValueError("faces: expected a flat integer array")
    cursor = 0
    while cursor < len(faces):
        size = int(faces[cursor])
        stop = cursor + size + 1
        if size < 3 or stop > len(faces):
            raise ValueError("faces: invalid polygon length or truncated indices")
        ids = faces[cursor + 1:stop]
        if np.any(ids < 0) or np.any(ids >= vertex_count):
            raise ValueError("faces: vertex index out of range")
        cursor = stop


def load_dataset(cube_path, metadata_path, scene_path=None, inside_path=None,
                 quantities=("coherent", "incoherent")):
    cube_path, metadata_path = Path(cube_path), Path(metadata_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    if not isinstance(metadata, dict):
        raise ValueError("metadata.json: expected an object")
    if metadata.get("coordinate_unit") != "m":
        raise ValueError("metadata.json: coordinate_unit must be m")
    if metadata.get("axis_order") != ["x", "y", "z"]:
        raise ValueError("metadata.json: axis_order must be [x, y, z]")
    if metadata.get("value_kind") not in ("received_power_dbw", "path_gain_db"):
        raise ValueError("metadata.json: value_kind must be received_power_dbw or path_gain_db")
    inputs = [cube_path, metadata_path]
    with np.load(cube_path, allow_pickle=False) as archive:
        axes = tuple(numeric(archive[f"{axis}_centers"], f"{axis}_centers")
                     for axis in "xyz")
        for axis, values in zip("xyz", axes):
            if values.ndim != 1 or len(values) < 2 or not np.all(np.diff(values.astype(float)) > 0):
                raise ValueError(f"{axis}_centers: need at least 2 strictly increasing coordinates")
        shape = tuple(len(values) for values in axes)
        powers = {}
        for quantity in quantities:
            key = f"P_{quantity}_dB"
            values = archive[key]
            if values.dtype.kind != "f" or values.shape != shape:
                raise ValueError(f"{key}: expected a floating point array of shape {shape}")
            if np.isinf(values).any() or not np.isfinite(values).any():
                raise ValueError(f"{key}: need finite power values; use NaN for uncovered cells, not infinity")
            powers[quantity] = values
    vertices = np.empty((0, 3), dtype=float)
    faces = np.empty(0, dtype=np.int64)
    tx = None
    if scene_path is not None:
        scene_path = Path(scene_path)
        inputs.append(scene_path)
        with np.load(scene_path, allow_pickle=False) as scene:
            vertices = numeric(scene["vertices"], "vertices")
            if vertices.ndim != 2 or vertices.shape[1] != 3:
                raise ValueError("vertices: expected shape (N, 3)")
            faces = scene["faces"]
            validate_faces(faces, len(vertices))
            if "Tx" in scene:
                tx = numeric(scene["Tx"], "Tx")
                if tx.shape != (3,):
                    raise ValueError("Tx: expected shape (3,)")
    inside = None
    if inside_path is not None:
        inside_path = Path(inside_path)
        inputs.append(inside_path)
        with np.load(inside_path, allow_pickle=False) as mask:
            inside = mask["inside"]
            if inside.dtype.kind != "b" or inside.shape != shape:
                raise ValueError(f"inside: expected a boolean array of shape {shape}")
            coord_keys = [f"{axis}_centers" for axis in "xyz"]
            if any(key in mask for key in coord_keys):
                for key, values in zip(coord_keys, axes):
                    if key not in mask or not np.array_equal(mask[key], values):
                        raise ValueError(f"inside_mask: {key} does not match the power cube")
    return Dataset(axes, powers, vertices, faces, tx, inside, metadata, inputs)
