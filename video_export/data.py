"""Read and validate numeric 3D data and optional geometry."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Dataset:
    axes: tuple
    values: np.ndarray
    inside: object
    vertices: np.ndarray
    faces: np.ndarray
    marker: object


def numeric(value, name):
    array = np.asarray(value)
    if array.dtype.kind not in "iuf" or not np.isfinite(array).all():
        raise ValueError(f"{name}: expected finite numeric values")
    return array


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


def load_dataset(cube_path, scene_path=None):
    with np.load(cube_path, allow_pickle=False) as archive:
        axes = tuple(numeric(archive[f"{axis}_centers"], f"{axis}_centers")
                     for axis in "xyz")
        for axis, coordinates in zip("xyz", axes):
            if (coordinates.ndim != 1 or len(coordinates) < 2
                    or np.any(np.diff(coordinates.astype(float)) <= 0)):
                raise ValueError(f"{axis}_centers: need at least two increasing coordinates")
        shape = tuple(len(coordinates) for coordinates in axes)
        values = archive["values"]
        if values.dtype.kind not in "iuf" or values.shape != shape:
            raise ValueError(f"values: expected a numeric array of shape {shape}")
        if np.isinf(values).any() or not np.isfinite(values).any():
            raise ValueError("values: need finite data; use NaN for missing cells")
        inside = archive["inside"] if "inside" in archive else None
        if inside is not None and (inside.dtype.kind != "b" or inside.shape != shape):
            raise ValueError(f"inside: expected a boolean array of shape {shape}")
        if inside is not None and not np.any(np.isfinite(values) & ~inside):
            raise ValueError("values: no finite data outside the inside mask")
    vertices = np.empty((0, 3), dtype=float)
    faces = np.empty(0, dtype=np.int64)
    marker = None
    if scene_path is not None:
        with np.load(Path(scene_path), allow_pickle=False) as scene:
            vertices = numeric(scene["vertices"], "vertices")
            if vertices.ndim != 2 or vertices.shape[1] != 3:
                raise ValueError("vertices: expected shape (N, 3)")
            faces = scene["faces"]
            validate_faces(faces, len(vertices))
            if "marker" in scene:
                marker = numeric(scene["marker"], "marker")
                if marker.shape != (3,):
                    raise ValueError("marker: expected shape (3,)")
    return Dataset(axes, values, inside, vertices, faces, marker)
