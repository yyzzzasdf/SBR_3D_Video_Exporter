"""Small reproducible synthetic data and numeric scene serialization."""
from pathlib import Path
import json
import numpy as np


def write_scene(path, polygons, tx):
    vertices, faces, offset = [], [], 0
    for polygon in polygons:
        polygon = np.asarray(polygon, dtype=np.float64)
        vertices.append(polygon)
        faces.extend([len(polygon), *range(offset, offset + len(polygon))])
        offset += len(polygon)
    values = np.vstack(vertices) if vertices else np.empty((0, 3))
    payload = {"vertices": values, "faces": np.asarray(faces, dtype=np.int64)}
    if tx is not None:
        payload["Tx"] = np.asarray(tx, dtype=np.float64)
    np.savez_compressed(path, **payload)


def generate_synthetic(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    x, y, z = np.linspace(-80, 80, 8), np.linspace(-100, 100, 10), np.linspace(5, 65, 6)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    tx = np.array([50., 50., 10.])
    distance = np.sqrt((xx - tx[0])**2 + (yy - tx[1])**2 + (zz - tx[2])**2)
    base = -35.0 - 20.0 * np.log10(distance + 1.0)
    coherent = base + 4.0 * np.sin(xx / 15.0) * np.cos(yy / 19.0)
    coherent[:2, :2, :] = np.nan
    incoherent = base.copy()
    incoherent[:2, :2, :] = np.nan
    np.savez_compressed(output / "power_cube.npz", x_centers=x, y_centers=y, z_centers=z,
                        P_coherent_dB=coherent.astype(np.float32),
                        P_incoherent_dB=incoherent.astype(np.float32))
    vertices = np.array([[-60., -50., 0.], [-10., -50., 0.], [-10., 0., 0.], [-60., 0., 0.],
                         [-60., -50., 40.], [-10., -50., 40.], [-10., 0., 40.], [-60., 0., 40.]])
    loops = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    write_scene(output / "scene.npz", [vertices[ids] for ids in loops], tx)
    inside = (xx > -60) & (xx < -10) & (yy > -50) & (yy < 0) & (zz < 40)
    np.savez_compressed(output / "inside_mask.npz", inside=inside, x_centers=x, y_centers=y, z_centers=z)
    metadata = {"schema_version": 1, "coordinate_unit": "m", "axis_order": ["x", "y", "z"],
                "value_kind": "received_power_dbw", "tx_power_w": 1.0,
                "source": "Analytic synthetic field for renderer testing; not a radio simulation",
                "dataset": "synthetic", "shape": [8, 10, 6]}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return output
