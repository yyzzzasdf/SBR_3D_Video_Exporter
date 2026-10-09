import json
from pathlib import Path
import numpy as np
import pytest
from video_export.config import load_config
from video_export.data import load_dataset
from video_export.samples import generate_synthetic


def load(folder, **overrides):
    paths = dict(cube_path=folder / "power_cube.npz", metadata_path=folder / "metadata.json",
                 scene_path=folder / "scene.npz", inside_path=folder / "inside_mask.npz")
    paths.update(overrides)
    return load_dataset(**paths)


def replace_npz(path, **changes):
    with np.load(path, allow_pickle=False) as archive:
        contents = dict(archive)
    contents.update(changes)
    np.savez_compressed(path, **contents)


def test_valid_bundle_and_single_quantity(tmp_path):
    folder = generate_synthetic(tmp_path)
    dataset = load(folder, quantities=["coherent"])
    assert dataset.powers["coherent"].shape == (8, 10, 6)
    assert list(dataset.powers) == ["coherent"]
    assert dataset.inside.dtype == bool


@pytest.mark.parametrize("problem", ["transpose", "descending", "infinity", "all_nan", "mask_axes", "bad_faces", "object_power"])
def test_reject_invalid_data(tmp_path, problem):
    folder = generate_synthetic(tmp_path)
    with np.load(folder / "power_cube.npz") as archive:
        power = archive["P_coherent_dB"]
        x = archive["x_centers"]
    if problem == "transpose":
        replace_npz(folder / "power_cube.npz", P_coherent_dB=power.transpose(1, 0, 2))
    elif problem == "descending":
        replace_npz(folder / "power_cube.npz", x_centers=x[::-1])
    elif problem == "infinity":
        power[3, 3, 2] = np.inf
        replace_npz(folder / "power_cube.npz", P_coherent_dB=power)
    elif problem == "all_nan":
        replace_npz(folder / "power_cube.npz", P_coherent_dB=np.full(power.shape, np.nan))
    elif problem == "mask_axes":
        replace_npz(folder / "inside_mask.npz", x_centers=x + 1)
    elif problem == "bad_faces":
        replace_npz(folder / "scene.npz", faces=np.array([3, 0, 1, 9999]))
    elif problem == "object_power":
        replace_npz(folder / "power_cube.npz", P_coherent_dB=power.astype(object))
    with pytest.raises(ValueError):
        load(folder)


def test_geometry_is_optional(tmp_path):
    folder = generate_synthetic(tmp_path)
    dataset = load(folder, scene_path=None, inside_path=None)
    assert not dataset.faces.size and dataset.tx is None and dataset.inside is None


@pytest.mark.parametrize("values", [{"fps_x": 0}, {"width": 641}, {"vmin": 0, "vmax": -1},
                                   {"axes": ["x", "x"]}, {"building_opacity": 2}, {"frames_z": 0}])
def test_reject_invalid_parameters(tmp_path, values):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(values))
    with pytest.raises(ValueError):
        load_config(path)
